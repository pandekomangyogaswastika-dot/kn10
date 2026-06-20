# KN_04 — DATABASE STANDARDS
## Kain Nusantara Platform — MongoDB Design Standards

**Versi:** 1.0 | **Berlaku sejak:** 2026-05-23

---

## SSOT Principle (Single Source of Truth)

```
Setiap business entity HARUS punya TEPAT SATU authoritative collection.

✅ BENAR:
  Satu collection untuk item master: inventory_items
  Satu collection untuk stock levels: inventory_stock
  Satu collection untuk sales orders: sales_orders

❌ SALAH (yang terjadi di DA30):
  acc_items + rahaza_materials + accessories + accessory_items
  (4 collection untuk entitas yang sama)

Sebelum buat collection baru, WAJIB tanya:
  1. Apakah entity ini sudah ada?
  2. Bisa pakai field `type` di collection yang ada?
  3. Hanya buat baru jika domain lifecycle BENAR-BENAR berbeda
```

---

## Collection Naming Convention

```
Format: {domain}_{entity_plural}

Domain prefixes:
  inventory_*     → Item master, stock, movements, reservations
  warehouse_*     → Locations, zones, racks, bins
  sales_*         → Orders, POS, customers, deliveries
  procurement_*   → Purchase orders, GR, suppliers
  finance_*       → AR, AP, GL, journals, cash
  hr_*            → Employees, attendance, payroll, leave
  rfid_*          → Tags, readers, events, zones
  system_*        → Users, roles, permissions, config
  audit_*         → Logs (partitioned by month)
  tasks_*         → Personal work items, assignments
  notifications_* → Notification records

Contoh:
  inventory_items
  inventory_stock
  inventory_movements
  inventory_reservations
  warehouse_locations
  warehouse_zones
  sales_orders
  sales_order_items
  procurement_purchase_orders
  finance_ar_invoices
  hr_employees
  rfid_tags
  rfid_events_raw
  audit_logs_2026_05   ← Monthly partition
```

---

## Document Schema Template

```python
# Setiap document WAJIB punya field-field ini:

BASE_SCHEMA = {
    "id": str(uuid4()),                            # UUID v4, BUKAN ObjectId
    "created_at": datetime.now(timezone.utc).isoformat(),  # UTC, ISO 8601
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "created_by": user["id"],                      # User yang buat
    "created_by_name": user.get("name"),           # Snapshot nama
    "tenant_id": "default",                        # Multi-tenant ready
    # ... business fields
}

# Field tambahan untuk transaksi bisnis:
TRANSACTION_SCHEMA = {
    ...BASE_SCHEMA,
    "warehouse_id": "...",      # WAJIB jika entity terkait gudang
    "status": "draft",          # Status enum
    "updated_by": user["id"],   # Siapa yang terakhir ubah
    "updated_by_name": "...",
    "voided": False,            # Soft delete
    "voided_at": None,
    "voided_by": None,
    "void_reason": None,
}

# ATURAN:
# ✅ SELALU UUID v4 untuk id
# ✅ SELALU timezone.utc untuk timestamp
# ✅ SELALU isoformat() untuk datetime
# ❌ JANGAN gunakan MongoDB ObjectId sebagai business ID
# ❌ JANGAN gunakan naive datetime (tanpa timezone)
```

---

## Index Strategy

```python
# Setiap collection WAJIB punya index berikut:

# 1. Standard indexes (semua collection)
await db.collection.create_index([("created_at", -1)])  # Default sort
await db.collection.create_index([("updated_at", -1)])  # Sync/polling
await db.collection.create_index([("tenant_id", 1)])    # Multi-tenant

# 2. Business entity indexes (collection dengan warehouse scope)
await db.inventory_stock.create_index([
    ("warehouse_id", 1),
    ("status", 1),
    ("created_at", -1)
])  # Compound: filter warehouse + status + sort by date

await db.inventory_stock.create_index([
    ("item_id", 1),
    ("warehouse_id", 1)
], unique=True)  # Unique per item per warehouse

# 3. Reference indexes (foreign keys)
await db.sales_order_items.create_index([("order_id", 1)])  # Lookup by parent
await db.inventory_movements.create_index([("reference_id", 1)])  # Reference

# 4. Search indexes
await db.inventory_items.create_index([
    ("name", "text"),
    ("sku", "text"),
    ("description", "text")
])

# 5. Unique indexes
await db.inventory_items.create_index([("sku", 1)], unique=True)
await db.system_users.create_index([("email", 1)], unique=True)
await db.rfid_tags.create_index([("epc", 1)], unique=True)

# 6. RFID specific
await db.rfid_events_raw.create_index([
    ("reader_id", 1),
    ("sequence_id", 1)
], unique=True)  # Idempotency
await db.rfid_events_raw.create_index(
    [("created_at", 1)],
    expireAfterSeconds=2592000  # TTL: 30 hari untuk raw events
)

# Panduan:
# Cek EXPLAIN sebelum go-live: stage: "COLLSCAN" = tidak ada index
# stage: "IXSCAN" = index digunakan
```

---

## Anti-Patterns (JANGAN LAKUKAN)

```python
# ❌ 1. Unbounded array dalam satu document
{
  "order_id": "xxx",
  "movements": [...]  # Bisa ribuan → 16MB limit terlewati
}
# ✅ Separate collection dengan foreign key

# ❌ 2. Load semua data tanpa limit
all_data = await db.inventory_movements.find({}).to_list(None)  # BERBAHAYA!
# ✅ Selalu paginate
data = await db.inventory_movements.find(filter).skip(skip).limit(limit).to_list(limit)

# ❌ 3. N+1 query
for order in orders:
    customer = await db.customers.find_one({"id": order["customer_id"]})
# ✅ Batch fetch atau $lookup aggregation

# ❌ 4. Tidak ada projection (ambil semua field)
docs = await db.inventory_items.find({}).to_list(None)
# ✅ Hanya ambil field yang perlu
docs = await db.inventory_items.find({}, {"id": 1, "sku": 1, "name": 1, "_id": 0})

# ❌ 5. Direct user input ke query
result = await db.users.find_one({"email": raw_input})
# ✅ Validate dulu
email = str(raw_input).strip().lower()
if not email or "@" not in email:
    raise HTTPException(400, "Email tidak valid")
result = await db.users.find_one({"email": email})
```

---

## Soft Delete Policy

```python
# KN menggunakan soft delete untuk semua business entities
# Hard delete HANYA untuk: raw RFID events (TTL), system config drafts

# Soft delete pattern:
async def soft_delete(db, collection: str, doc_id: str, user: dict):
    result = await db[collection].update_one(
        {"id": doc_id, "voided": False},
        {"$set": {
            "voided": True,
            "voided_at": now_iso(),
            "voided_by": user["id"],
            "voided_by_name": user.get("name"),
            "updated_at": now_iso()
        }}
    )
    return result.modified_count > 0

# Semua list endpoints WAJIB exclude voided:
filter["voided"] = {"$ne": True}  # Exclude soft-deleted
```

---

## Migration Protocol

```python
"""
Setiap schema migration WAJIB ikuti protokol ini:

1. Tulis migration script di /app/backend/migrations/
2. Jalankan dry-run mode dulu (count + sample, tidak ada writes)
3. Validasi: jumlah source == target
4. Backup collection sebelum migrate
5. Jalankan dengan --execute flag
6. Validasi ulang setelah migrate
7. Simpan collection lama 1 minggu (monitoring)
8. Baru delete setelah konfirmasi tidak ada write ke collection lama

Format nama file: YYYYMMDD_description.py
Contoh: 20260523_migrate_inventory_items_add_lot_tracking.py
"""

# Template migration script:
import asyncio, argparse
from datetime import datetime, timezone

async def migrate(dry_run=True):
    db = get_db()
    source_count = await db.old_collection.count_documents({})
    print(f"[DRY={dry_run}] Source: {source_count} records")
    
    migrated = 0
    async for doc in db.old_collection.find({}):
        new_doc = transform(doc)
        if not dry_run:
            await db.new_collection.update_one(
                {"id": new_doc["id"]}, {"$set": new_doc}, upsert=True
            )
        migrated += 1
    
    print(f"[DRY={dry_run}] Migrated: {migrated}")
    if not dry_run:
        target = await db.new_collection.count_documents({})
        assert target >= source_count, "DATA LOSS DETECTED!"
        print(f"Target: {target} records — OK")
```

---

## Materialized Summary Strategy

```python
# Untuk reporting pada data besar (jutaan record):
# Hitung summary setiap malam, dashboard baca dari summary

# Collection: daily_inventory_summary
# Update: cron job pukul 00:05 WIB setiap hari

{
    "id": "summary-2026-05-23-wh-cikarang",
    "date": "2026-05-23",
    "warehouse_id": "wh-cikarang",
    "item_id": "item-001",
    "sku": "KN-KATUN-MERAH-001",
    "opening_qty": 500.0,
    "total_in": 100.0,
    "total_out": 75.0,
    "closing_qty": 525.0,
    "uom": "meter",
    "calculated_at": "2026-05-24T00:05:00Z"
}

# Query laporan pakai summary, bukan raw movements
# Max date range untuk query raw movements: 7 hari
# Lebih dari 7 hari: gunakan daily_summary
# Lebih dari 90 hari: gunakan monthly_summary
```
