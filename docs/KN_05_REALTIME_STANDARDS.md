# KN_05 — REAL-TIME STANDARDS
## Kain Nusantara Platform — WebSocket, SSE & Redis Pub/Sub

**Versi:** 1.0 | **Berlaku sejak:** 2026-05-23

---

## Kapan Pakai Apa — Decision Tree

```
                    ┌─ Dua arah? ──────────────────── YES → WebSocket
                    │
Butuh real-time? ───┤                ┌─ High frequency? ── YES → WebSocket
                    │                │   (>5 events/detik)
                    └─ Satu arah? ───┤
                                     └─ Low frequency? ──── YES → SSE
                                         (<5 events/detik)

Use cases:
  WebSocket → RFID live feed, collaborative operations,
               scanner interface, live location tracking
  SSE       → Dashboard KPI updates, notifications,
               order status updates, stock alerts
  Regular REST → Reports, historical data, exports
                 (tidak butuh real-time)
```

---

## Architecture Overview

```
RFID Reader ─────────────┐
                          ▼
Business Event ──→ [FastAPI] ──→ [Redis Pub/Sub] ──┬──→ [WebSocket Manager]
User Action ─────────────┘                         │         │
                                                    │         └──→ Browser clients
                                                    └──→ [SSE Manager]
                                                              │
                                                              └──→ Browser clients

Channels (Redis topics):
  kn:warehouse:{warehouse_id}:movements     ← Stock movements
  kn:warehouse:{warehouse_id}:rfid          ← RFID events
  kn:warehouse:{warehouse_id}:alerts        ← Warehouse alerts
  kn:user:{user_id}:notifications           ← Personal notifications
  kn:user:{user_id}:tasks                   ← Task updates
  kn:global:system                          ← System-wide broadcasts
```

---

## Backend — WebSocket Pattern

```python
# WebSocket connection manager
from fastapi import WebSocket
from typing import Dict, Set
import asyncio, json

class ConnectionManager:
    def __init__(self):
        # { warehouse_id: Set[WebSocket] }
        self.warehouse_connections: Dict[str, Set[WebSocket]] = {}
        # { user_id: Set[WebSocket] }
        self.user_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user: dict):
        await websocket.accept()
        user_id = user["id"]
        warehouse_ids = user.get("warehouse_ids", [])
        
        # Register ke warehouse channels
        for wh_id in warehouse_ids:
            if wh_id not in self.warehouse_connections:
                self.warehouse_connections[wh_id] = set()
            self.warehouse_connections[wh_id].add(websocket)
        
        # Register ke user channel
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, user: dict):
        # Cleanup semua registrations
        user_id = user["id"]
        for wh_id in user.get("warehouse_ids", []):
            self.warehouse_connections.get(wh_id, set()).discard(websocket)
        self.user_connections.get(user_id, set()).discard(websocket)

    async def broadcast_to_warehouse(self, warehouse_id: str, message: dict):
        connections = self.warehouse_connections.get(warehouse_id, set()).copy()
        dead = set()
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.warehouse_connections[warehouse_id].discard(ws)

    async def send_to_user(self, user_id: str, message: dict):
        connections = self.user_connections.get(user_id, set()).copy()
        for ws in connections:
            try:
                await ws.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

# WebSocket endpoint
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        user = verify_jwt(token)
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return
    
    await manager.connect(websocket, user)
    try:
        while True:
            # Keep-alive ping
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        await manager.disconnect(websocket, user)

# Redis subscriber (background task)
async def redis_subscriber():
    async with redis_client.pubsub() as pubsub:
        await pubsub.psubscribe("kn:*")
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                channel = message["channel"].decode()
                data = json.loads(message["data"])
                
                # Route berdasarkan channel
                if ":movements" in channel or ":rfid" in channel:
                    wh_id = channel.split(":")[2]
                    await manager.broadcast_to_warehouse(wh_id, data)
                elif ":notifications" in channel or ":tasks" in channel:
                    user_id = channel.split(":")[2]
                    await manager.send_to_user(user_id, data)
```

---

## Backend — SSE Pattern

```python
from fastapi.responses import StreamingResponse
import asyncio, json

@router.get("/sse/dashboard")
async def dashboard_sse(user=Depends(require_auth)):
    async def event_generator():
        async with redis_client.pubsub() as pubsub:
            channels = [
                f"kn:warehouse:{wh_id}:alerts"
                for wh_id in user.get("warehouse_ids", [])
            ]
            await pubsub.subscribe(*channels)
            
            # Kirim initial data
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            
            # Stream updates
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"data: {message['data'].decode()}\n\n"
                    
                # Heartbeat setiap 30 detik
                await asyncio.sleep(0)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Nginx buffering off
        }
    )
```

---

## Frontend — WebSocket Hook

```javascript
// hooks/useWebSocket.js
import { useEffect, useRef, useCallback } from 'react';
import { useAuthStore } from '@/stores/authStore';
import { useWarehouseStore } from '@/stores/warehouseStore';

export function useKNWebSocket(onMessage) {
  const ws = useRef(null);
  const reconnectTimer = useRef(null);
  const { user } = useAuthStore();
  
  const connect = useCallback(() => {
    if (!user?.ws_token) return;
    
    const wsUrl = `${process.env.REACT_APP_WS_URL}/ws?token=${user.ws_token}`;
    ws.current = new WebSocket(wsUrl);
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };
    
    ws.current.onclose = () => {
      // Auto-reconnect dengan exponential backoff
      const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
      reconnectTimer.current = setTimeout(connect, delay);
    };
    
    ws.current.onerror = () => {
      ws.current?.close();
    };
  }, [user, onMessage]);
  
  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimer.current);
      ws.current?.close();
    };
  }, [connect]);
}

// hooks/useSSE.js
export function useSSE(endpoint, onEvent) {
  useEffect(() => {
    const sse = new EventSource(
      `${process.env.REACT_APP_BACKEND_URL}${endpoint}`,
      { withCredentials: true }
    );
    
    sse.onmessage = (e) => onEvent(JSON.parse(e.data));
    sse.onerror = () => {
      sse.close();
      // Reconnect setelah 5 detik
      setTimeout(() => useSSE(endpoint, onEvent), 5000);
    };
    
    return () => sse.close();
  }, [endpoint]);
}
```

---

## Real-Time UX Patterns

```javascript
// Pattern 1: Dashboard KPI — smooth number update
function KPICard({ value, label }) {
  const [displayed, setDisplayed] = useState(value);
  
  useEffect(() => {
    // Animasi count-up/down saat value berubah
    animateNumber(displayed, value, setDisplayed);
  }, [value]);
  
  return (
    <div data-testid="kpi-card">
      <span className="text-3xl font-bold tabular-nums">{displayed}</span>
      <span className="text-sm text-muted-foreground">{label}</span>
    </div>
  );
}

// Pattern 2: Tabel — highlight row yang baru update
function useHighlightOnUpdate(data, key = 'id') {
  const [highlighted, setHighlighted] = useState(new Set());
  const prevData = usePrevious(data);
  
  useEffect(() => {
    if (!prevData) return;
    const changed = data
      .filter(item => {
        const prev = prevData.find(p => p[key] === item[key]);
        return !prev || prev.updated_at !== item.updated_at;
      })
      .map(item => item[key]);
    
    setHighlighted(new Set(changed));
    setTimeout(() => setHighlighted(new Set()), 2000); // Clear setelah 2 detik
  }, [data]);
  
  return highlighted;
}

// Pattern 3: Jangan interrupt saat user sedang isi form
// Gunakan background sync, update setelah form submit
```

---

## Redis Pub/Sub — Publishing Pattern

```python
# Setiap kali ada business event, publish ke Redis
async def publish_event(redis, channel: str, event_type: str, data: dict):
    message = {
        "type": event_type,
        "data": data,
        "timestamp": now_iso()
    }
    await redis.publish(channel, json.dumps(message))

# Contoh: setelah stock movement
async def after_movement_created(movement: dict, redis):
    await publish_event(
        redis,
        channel=f"kn:warehouse:{movement['warehouse_id']}:movements",
        event_type="MOVEMENT_CREATED",
        data={
            "movement_id": movement["id"],
            "item_id": movement["item_id"],
            "qty_change": movement["quantity"],
            "new_stock": movement["after_qty"]
        }
    )
```
