# KN_07 — API STANDARDS
## Kain Nusantara Platform — REST API Design Standards

**Versi:** 1.0 | **Berlaku sejak:** 2026-05-23

---

## Response Envelope

```json
// Success — single object
{
  "success": true,
  "data": { "id": "...", "sku": "KN-001" }
}

// Success — list dengan pagination
{
  "success": true,
  "data": [ {...}, {...} ],
  "meta": {
    "total": 10000,
    "page": 1,
    "limit": 20,
    "total_pages": 500,
    "has_next": true,
    "has_prev": false
  }
}

// Error — validation
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Data tidak valid",
    "details": [
      { "field": "quantity", "message": "Nilai harus lebih dari 0" },
      { "field": "uom", "message": "UOM tidak dikenali" }
    ],
    "request_id": "req-550e8400-e29b"
  }
}

// Error — business rule
{
  "success": false,
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Stok tidak mencukupi untuk operasi ini",
    "details": [{ "available": 45, "requested": 60 }],
    "request_id": "req-550e8400-e29b"
  }
}
```

---

## HTTP Status Codes

```
200 OK             → GET berhasil, PUT/PATCH berhasil
201 Created        → POST berhasil membuat resource baru
204 No Content     → DELETE berhasil
400 Bad Request    → Format request salah, tipe data salah
401 Unauthorized   → Belum login atau token expired
403 Forbidden      → Login tapi tidak punya akses
404 Not Found      → Resource tidak ditemukan
409 Conflict       → Duplicate data, concurrent update collision
422 Unprocessable  → Validasi bisnis gagal (stok kurang, status salah)
429 Too Many Req   → Rate limit terlewati
500 Server Error   → Error tidak terduga di server
```

---

## URL Structure

```
# Pattern:
/api/{version}/{domain}/{resource}
/api/{version}/{domain}/{resource}/{id}
/api/{version}/{domain}/{resource}/{id}/{action}

# Versioning: URL-based
/api/v1/inventory/stock
/api/v1/inventory/stock/{item_id}
/api/v1/inventory/stock/{item_id}/adjust

# Domain prefixes:
/api/v1/inventory/    → Inventory domain
/api/v1/warehouse/    → Warehouse operations
/api/v1/sales/        → Sales & POS
/api/v1/procurement/  → Procurement
/api/v1/finance/      → Finance
/api/v1/hr/           → Human Resources
/api/v1/rfid/         → RFID operations
/api/v1/system/       → Users, roles, config
/api/v1/auth/         → Authentication
/api/v1/tasks/        → Personal work system
/api/v1/notifications/→ Notifications

# Action endpoints (non-CRUD):
POST /api/v1/procurement/purchase-orders/{id}/approve
POST /api/v1/procurement/purchase-orders/{id}/void
POST /api/v1/inventory/stock/{id}/adjust
POST /api/v1/sales/orders/{id}/confirm

# Route ordering — specific before generic:
@router.get("/stock/alerts")     # ← Specific FIRST
@router.get("/stock/{item_id}")  # ← Generic AFTER
```

---

## Query Parameters (Filtering & Sorting)

```
GET /api/v1/inventory/stock?
  warehouse_id=wh-001           → Filter by warehouse
  &status=active                → Filter by status enum
  &item_type=fabric             → Filter by type
  &search=katun+merah           → Full-text search
  &lot_number=LOT-2026-05       → Exact match
  &qty_min=100                  → Range filter
  &qty_max=1000
  &created_after=2026-05-01     → Date range
  &created_before=2026-05-31
  &sort_by=updated_at           → Sort field
  &sort_dir=desc                → asc | desc
  &page=1                       → Pagination
  &limit=20                     → Max 100

# Implementasi backend:
async def list_stock(
    warehouse_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("updated_at"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    filter_query = {}
    if warehouse_id: filter_query["warehouse_id"] = warehouse_id
    if status: filter_query["status"] = status
    if search:
        filter_query["$text"] = {"$search": search}
    
    sort_order = -1 if sort_dir == "desc" else 1
    skip = (page - 1) * limit
    
    total = await db.inventory_stock.count_documents(filter_query)
    items = await db.inventory_stock.find(filter_query) \
        .sort(sort_by, sort_order) \
        .skip(skip).limit(limit).to_list(limit)
    
    return paginate_response(items, total, page, limit)
```

---

## Pagination Helper

```python
# core_utils.py
def paginate_response(data: list, total: int, page: int, limit: int) -> dict:
    total_pages = (total + limit - 1) // limit
    return {
        "success": True,
        "data": data,
        "meta": {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }

def success_response(data) -> dict:
    return {"success": True, "data": data}

def error_response(code: str, message: str, details: list = []) -> dict:
    return {
        "success": False,
        "error": {"code": code, "message": message, "details": details}
    }
```

---

## Request ID & Tracing

```python
# Middleware: inject request_id ke setiap request
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Error responses selalu include request_id untuk debugging
raise HTTPException(status_code=422, detail={
    "code": "INSUFFICIENT_STOCK",
    "message": "Stok tidak mencukupi",
    "details": [],
    "request_id": request.state.request_id
})
```

---

## Error Code Convention

```
Format: SCREAMING_SNAKE_CASE, domain prefix

Auth:
  AUTH_INVALID_CREDENTIALS
  AUTH_TOKEN_EXPIRED
  AUTH_INSUFFICIENT_PERMISSION
  AUTH_ACCOUNT_LOCKED

Inventory:
  INVENTORY_ITEM_NOT_FOUND
  INVENTORY_INSUFFICIENT_STOCK
  INVENTORY_DUPLICATE_SKU
  INVENTORY_LOT_MISMATCH

Warehouse:
  WAREHOUSE_LOCATION_FULL
  WAREHOUSE_INVALID_TRANSFER
  WAREHOUSE_LOCATION_NOT_FOUND

Sales:
  SALES_ORDER_ALREADY_CONFIRMED
  SALES_CUSTOMER_CREDIT_EXCEEDED

Procurement:
  PROCUREMENT_PO_ALREADY_RECEIVED
  PROCUREMENT_GR_QTY_EXCEEDS_PO

Validation:
  VALIDATION_ERROR            ← Multiple field errors
  VALIDATION_REQUIRED_FIELD   ← Single field missing
  VALIDATION_INVALID_FORMAT   ← Format salah
  VALIDATION_OUT_OF_RANGE     ← Nilai di luar batas

System:
  SYSTEM_CONCURRENT_UPDATE    ← Race condition
  SYSTEM_RATE_LIMIT_EXCEEDED
  SYSTEM_INTERNAL_ERROR
```

---

## API Versioning Policy

```
v1 → Current stable version
v2 → Saat ada breaking change (bukan additive change)

Breaking changes (PERLU version bump):
  - Hapus endpoint
  - Rename field di response
  - Ubah tipe data field
  - Ubah URL structure

Non-breaking changes (TIDAK perlu version bump):
  - Tambah endpoint baru
  - Tambah optional field di response
  - Tambah optional query parameter
  - Performance improvement

Deprecation policy:
  - Umumkan v1 deprecated minimal 3 bulan sebelum hapus
  - Kirim header: Deprecation: true pada response v1
  - v1 dan v2 bisa jalan bersamaan selama 3 bulan
```
