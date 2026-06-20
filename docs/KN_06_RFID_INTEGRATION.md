# KN_06 — RFID INTEGRATION
## Kain Nusantara Platform — Chainway UHF Reader Architecture

**Versi:** 1.0 | **Berlaku sejak:** 2026-05-23

---

## Architecture Overview

```
[Chainway UHF Reader] ──LLRP/TCP──→ [RFID Edge Agent (Python)]
     (Fixed or                           Per warehouse
      Handheld)                          Runs on local server
                                              │
                                         Deduplication
                                         Zone assignment
                                         Buffering
                                         Sequence numbering
                                              │
                                         MQTT over TLS
                                              ▼
                                     [MQTT Broker (EMQX)]
                                     Topic: rfid/events/{wh}/{zone}
                                              │
                                              ▼
                                   [FastAPI MQTT Consumer]
                                   Idempotency check
                                   Business rules
                                   MongoDB write
                                   Redis publish
                                              │
                              ┌───────────────┴───────────────┐
                              ▼                               ▼
                    [rfid_events_raw]             [Redis Pub/Sub]
                    (append-only)                → WebSocket → Frontend
```

---

## Device Strategy

```
FIXED UHF READERS (Primary RFID):
  Dipasang di: Receiving dock, zone gates, shipping dock
  Coverage: Otomatis detect movement antar zone
  Protocol: LLRP (Impinj standard) atau TCP (Chainway native)
  Connection: Wired LAN (bukan WiFi untuk reliability)

HANDHELD CHAINWAY (Operator Tool):
  Use case: Spot check, cycle count, receiving konfirmasi
  Software: Thin Android WebView wrapper + PWA bridge
  RFID: Bridge Chainway UHF SDK → JavaScript Interface
  Barcode: Kamera PWA atau keyboard wedge

RFID TAG STANDARD:
  Protocol: EPC Gen2 (ISO 18000-63)
  Frequency: 920-925 MHz (Indonesia)
  Format EPC: [Header 8bit][Filter 3bit][Partition 3bit]
              [Company Prefix][Item Reference][Serial]
  Encoding: Saat receiving (new tag) atau saat buat item
```

---

## Edge Agent — Core Logic

```python
"""
RFID Edge Agent
===============
Berjalan di local server setiap gudang.
Handle: deduplication, zone assignment, buffering, MQTT publish.
"""

DEDUP_WINDOW_MS = 500     # Tag yang sama dalam 500ms = 1 event
EVENT_BUFFER_SIZE = 1000  # Buffer saat MQTT disconnect
SEQUENCE_COUNTER = 0      # Per reader, monotonically increasing

class RFIDEdgeAgent:
    def __init__(self, warehouse_id: str, reader_id: str):
        self.warehouse_id = warehouse_id
        self.reader_id = reader_id
        self.tag_buffer: Dict[str, TagRead] = {}  # EPC → last seen
        self.sequence = 0
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
    
    async def on_tag_read(self, epc: str, antenna_id: int, rssi: int):
        """Called per raw tag read from reader."""
        now = time.time() * 1000  # milliseconds
        
        # Deduplication: same tag dalam window → update saja
        if epc in self.tag_buffer:
            last = self.tag_buffer[epc]
            if now - last.first_seen_ms < DEDUP_WINDOW_MS:
                last.read_count += 1
                last.last_seen_ms = now
                last.rssi = max(last.rssi, rssi)  # Keep strongest signal
                return  # Jangan emit event baru
        
        # New event setelah dedup window
        self.sequence += 1
        event = RFIDEvent(
            sequence_id=self.sequence,
            reader_id=self.reader_id,
            antenna_id=antenna_id,
            zone_id=self.antenna_to_zone(antenna_id),
            warehouse_id=self.warehouse_id,
            epc=epc,
            rssi=rssi,
            read_count=1,
            first_seen_ms=now,
            last_seen_ms=now,
        )
        self.tag_buffer[epc] = event
        await self.event_queue.put(event)
    
    def antenna_to_zone(self, antenna_id: int) -> str:
        """Map antenna port ke zone ID."""
        # Config per reader, dari DB atau config file
        return ANTENNA_ZONE_MAP.get(f"{self.reader_id}:{antenna_id}", "unknown")
    
    async def mqtt_publisher(self, mqtt_client):
        """Background task: drain queue ke MQTT."""
        while True:
            event = await self.event_queue.get()
            topic = f"rfid/events/{self.warehouse_id}/{event.zone_id}"
            payload = event.model_dump_json()
            try:
                await mqtt_client.publish(topic, payload, qos=1)
            except Exception as e:
                # Re-queue saat MQTT down (bounded buffer)
                if self.event_queue.qsize() < EVENT_BUFFER_SIZE:
                    await self.event_queue.put(event)
```

---

## RFID Event Schema

```python
# rfid_events_raw — append-only, TTL 30 hari
RFID_RAW_EVENT = {
    "id": "uuid",
    "sequence_id": 12345,          # Per reader, untuk idempotency
    "reader_id": "reader-cikarang-gate-01",
    "antenna_id": 2,
    "zone_id": "zone-receiving",
    "warehouse_id": "wh-cikarang",
    "epc": "E2001234567890ABCDEF",  # RFID tag ID
    "rssi": -65,                   # Signal strength (dBm)
    "read_count": 3,               # Reads dalam dedup window
    "first_seen_at": "2026-05-23T10:30:00.000Z",
    "last_seen_at": "2026-05-23T10:30:00.450Z",
    "processed": False,            # Sudah jadi business event?
    "business_event_id": None,     # Link ke movement jika processed
    "created_at": "2026-05-23T10:30:01.000Z"
}

# rfid_tags — tag registry
RFID_TAG = {
    "id": "uuid",
    "epc": "E2001234567890ABCDEF",
    "item_id": "item-uuid",
    "roll_id": "roll-uuid",        # Untuk roll-level tracking
    "warehouse_id": "wh-cikarang",
    "current_zone_id": "zone-storage",
    "current_location_id": "bin-A-1-3",
    "tag_status": "active",        # active | deactivated | lost
    "encoded_at": "2026-05-23T...",
    "encoded_by": "user-uuid",
    "last_seen_at": "2026-05-23T...",
    "last_seen_zone": "zone-storage",
    "lock_bit": True,              # EPC Gen2 lock status
    "created_at": "..."
}
```

---

## Backend MQTT Consumer

```python
import aiomqtt, json

async def mqtt_consumer(app_state):
    """Background task: consume RFID events dari MQTT broker."""
    async with aiomqtt.Client(
        hostname=MQTT_HOST,
        port=MQTT_PORT,
        username=MQTT_USER,
        password=MQTT_PASS,
        tls_context=create_tls_context(),  # TLS 1.3
    ) as client:
        await client.subscribe("rfid/events/#", qos=1)
        async for message in client.messages:
            try:
                event = RFIDRawEvent(**json.loads(message.payload))
                await process_rfid_event(app_state.db, app_state.redis, event)
            except Exception as e:
                logger.error(f"RFID processing error: {e}")

async def process_rfid_event(db, redis, event: RFIDRawEvent):
    # 1. Idempotency check
    existing = await db.rfid_events_raw.find_one({
        "reader_id": event.reader_id,
        "sequence_id": event.sequence_id
    })
    if existing:
        return  # Already processed
    
    # 2. Validate reader
    reader = await db.rfid_readers.find_one({"reader_id": event.reader_id})
    if not reader or not reader.get("active"):
        logger.warning(f"Unknown/inactive reader: {event.reader_id}")
        return
    
    # 3. Lookup tag
    tag = await db.rfid_tags.find_one({"epc": event.epc})
    
    # 4. Detect zone transition
    if tag and tag["current_zone_id"] != event.zone_id:
        # Zone transition → create movement
        movement = await create_rfid_movement(
            db, event, tag,
            from_zone=tag["current_zone_id"],
            to_zone=event.zone_id
        )
        
        # Publish ke real-time
        await publish_event(redis,
            f"kn:warehouse:{event.warehouse_id}:rfid",
            "ZONE_TRANSITION",
            {"epc": event.epc, "from": tag["current_zone_id"],
             "to": event.zone_id, "movement_id": movement["id"]}
        )
    
    # 5. Duplicate tag detection (fraud check)
    if tag:
        other_recent = await db.rfid_events_raw.find_one({
            "epc": event.epc,
            "warehouse_id": {"$ne": event.warehouse_id},
            "created_at": {"$gte": (datetime.now(timezone.utc) -
                                    timedelta(minutes=5)).isoformat()}
        })
        if other_recent:
            await create_fraud_alert(db, redis, event, tag)
    
    # 6. Save raw event
    await db.rfid_events_raw.insert_one(event.model_dump())
    
    # 7. Update tag last seen
    await db.rfid_tags.update_one(
        {"epc": event.epc},
        {"$set": {
            "current_zone_id": event.zone_id,
            "last_seen_at": event.last_seen_at,
            "last_seen_zone": event.zone_id
        }}
    )
```

---

## RFID Security

```
Reader Authentication:
  → Mutual TLS: setiap reader punya certificate unik
  → MQTT client_id = reader_id (whitelist di broker)
  → reader_id harus terdaftar di rfid_readers collection
  → Unknown reader → reject + security alert

Replay Attack Prevention:
  → sequence_id monotonically increasing per reader
  → Timestamp validation: event >30 detik = reject
  → Idempotency: sequence_id + reader_id unique index

Tag Integrity:
  → EPC terdaftar di rfid_tags saat receiving
  → Same EPC di 2 warehouse berbeda = fraud alert
  → Lock bit setelah tag encoding

MQTT Security:
  → TLS 1.3 mandatory
  → Topic ACL: RFID service hanya publish rfid/events/#
  → Rate limit: 10.000 events/menit per reader_id
```
