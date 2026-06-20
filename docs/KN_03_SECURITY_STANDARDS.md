# KN_03 — SECURITY STANDARDS
## Kain Nusantara Platform — Security Implementation Guide

**Versi:** 1.0 | **Berlaku sejak:** 2026-05-23
**Scope:** Internal system — multi-role, multi-warehouse

---

## Threat Model (Internal System)

```
Ancaman yang paling relevan untuk sistem internal:

[1] Privilege Abuse      → Operator akses gudang lain
[2] Inventory Fraud      → Manipulasi stok / movement fiktif
[3] Data Exfiltration    → Export bulk data ke kompetitor
[4] Privilege Escalation → JWT payload modification
[5] Audit Tampering      → Hapus log setelah fraud
[6] RFID Manipulation    → Rogue reader, replay attack, tag cloning
[7] Accidental Damage    → Bulk delete/update salah filter
```

---

## Layer 1 — Authentication

### JWT Implementation

```python
# Token Strategy:

Access Token:
  - Expiry: 15 menit
  - Payload: user_id, role, warehouse_ids, session_id, scope
  - TIDAK boleh ada: password, email sensitif, nama lengkap
  - Algorithm: RS256 (production) / HS256 (development)
  - Delivery: HttpOnly Cookie (BUKAN localStorage)

Refresh Token:
  - Expiry: 8 jam (1 shift kerja)
  - Stored: HttpOnly Cookie
  - Rotasi: Setiap dipakai → invalidate yang lama
  - Disimpan di Redis: bisa di-revoke kapan saja

# Cookie config:
response.set_cookie(
    key="access_token",
    value=access_token,
    httponly=True,      # Tidak bisa diakses JS
    secure=True,        # HTTPS only (production)
    samesite="strict",  # CSRF protection
    max_age=900,        # 15 menit
    path="/api"
)

response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=True,
    samesite="strict",
    max_age=28800,      # 8 jam
    path="/api/v1/auth/refresh"  # Hanya untuk refresh endpoint
)
```

### Password Policy

```python
PASSWORD_POLICY = {
    "min_length": 10,
    "require_uppercase": True,
    "require_number": True,
    "require_special": True,
    "bcrypt_rounds": 12,
    "max_age_days": 90,
    "history_count": 5,      # Tidak boleh reuse 5 password terakhir
}

# Brute force protection:
BRUTE_FORCE = {
    "max_attempts": 5,
    "lockout_minutes": 15,
    "progressive_delay": True,   # Attempt 1: 0s, 2: 1s, 3: 3s, 4: 7s, 5: 15s
    "track_by": ["ip", "email"], # Track keduanya
}
```

### MFA (Multi-Factor Authentication)

```python
# WAJIB untuk:
MFA_REQUIRED_ROLES = ["SUPER_ADMIN", "SYSTEM_ADMIN"]

# Opsional (user bisa aktifkan sendiri) untuk role lain:
MFA_OPTIONAL_ROLES = ["FINANCE_MANAGER", "WAREHOUSE_MANAGER", "EXECUTIVE"]

# Implementasi: TOTP (Google Authenticator compatible)
# Library: pyotp
```

---

## Layer 2 — Authorization (RBAC)

### Permission Model

```python
# 3 Dimensi:
# WHAT (resource) + HOW (action) + WHERE (scope)

RESOURCES = [
    "inventory", "warehouse", "movement", "location",
    "sales_order", "pos", "customer",
    "purchase_order", "supplier", "goods_receipt",
    "finance_ar", "finance_ap", "finance_gl", "finance_cash",
    "hr_employee", "hr_attendance", "hr_payroll", "hr_leave",
    "rfid", "rfid_reader",
    "user", "role", "system_config",
    "report", "export", "audit_log",
    "task", "notification"
]

ACTIONS = ["create", "read", "update", "delete", "approve", "void", "export"]

SCOPES = ["global", "warehouse", "own"]

# Contoh permission matrix:
# WAREHOUSE_MANAGER:
#   warehouse:*     → scope: assigned_warehouses
#   inventory:read  → scope: assigned_warehouses
#   movement:*      → scope: assigned_warehouses
#   report:read     → scope: assigned_warehouses
#   export:*        → scope: assigned_warehouses
```

### Row-Level Security (Warehouse Isolation)

```python
# WAJIB: Warehouse filter SELALU dari token, bukan dari request

# ❌ BERBAHAYA:
@router.get("/stock")
async def get_stock(warehouse_id: str, user=Depends(require_auth)):
    return await db.inventory_stock.find({"warehouse_id": warehouse_id})

# ✅ AMAN:
@router.get("/stock")
async def get_stock(user=Depends(require_auth)):
    # Scope dari token
    if "global" in user.get("scope", []):
        filter_query = {}  # Admin lihat semua
    else:
        filter_query = {"warehouse_id": {"$in": user["warehouse_ids"]}}
    
    return await db.inventory_stock.find(filter_query).to_list(None)
```

### Permission Cache (Redis)

```python
async def check_permission(db, redis, user_id: str, role: str, 
                           resource: str, action: str) -> bool:
    cache_key = f"permissions:{user_id}:{role}"
    cached = await redis.get(cache_key)
    
    if cached:
        permissions = json.loads(cached)
    else:
        permissions = await db.role_permissions.find(
            {"role": role}
        ).to_list(None)
        # Cache 5 menit
        await redis.setex(cache_key, 300, json.dumps(permissions))
    
    # Check
    return any(
        p["resource"] in [resource, "*"] and
        p["action"] in [action, "*"]
        for p in permissions
    )

# Invalidate saat role user berubah:
async def invalidate_permission_cache(redis, user_id: str):
    await redis.delete(f"permissions:{user_id}:*")
```

---

## Layer 3 — API Security

### Input Validation

```python
# Semua request body WAJIB Pydantic model dengan strict=True

class CreateMovementRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    
    item_id: str = Field(..., min_length=1, max_length=50,
                         pattern=r'^[a-zA-Z0-9_-]+$')  # No injection chars
    quantity: float = Field(..., gt=0, le=999999)
    uom: Literal["roll", "meter", "kg", "pcs", "yard"]
    notes: str = Field(default="", max_length=500)

# NoSQL Injection prevention:
def sanitize_query_param(value: str) -> str:
    """Block MongoDB operator injection."""
    if value and (value.startswith("$") or "{" in value):
        raise HTTPException(400, "Parameter tidak valid")
    return value.strip() if value else value
```

### Rate Limiting

```python
# Redis sliding window rate limiter
RATE_LIMITS = {
    "auth_login":        {"limit": 5,      "window": 60},    # 5/menit per IP
    "auth_refresh":      {"limit": 10,     "window": 60},    # 10/menit per user
    "write_operations":  {"limit": 60,     "window": 60},    # 60/menit per user
    "read_operations":   {"limit": 300,    "window": 60},    # 300/menit per user
    "export":            {"limit": 5,      "window": 3600},  # 5/jam per user
    "rfid_events":       {"limit": 10000,  "window": 60},    # 10k/menit per reader
}
```

### Security Headers

```python
# Middleware — semua response
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store, no-cache",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()"
}

# CORS — ketat untuk internal
CORS_CONFIG = {
    "allow_origins": [os.getenv("FRONTEND_URL", "http://localhost:3000")],
    "allow_credentials": True,  # Perlu untuk cookie
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE"],
    "allow_headers": ["Content-Type", "X-Request-ID"],
}
# JANGAN: allow_origins=["*"]
```

---

## Layer 4 — Data Security & Audit Trail

### PII Classification

```
Level 3 — Highly Sensitive (strict access, mask in logs):
  Karyawan: gaji, rekening bank, nomor KTP, alamat lengkap
  User: password hash

Level 2 — Sensitive (access controlled, partial mask):
  Customer: nomor HP, email, alamat
  Supplier: contact, pricing
  Finance: jumlah invoice, pembayaran

Level 1 — Internal (access controlled):
  Inventory data, stock quantities, business metrics

Level 0 — Reference (widely accessible):
  Nama item, SKU, nama gudang, UoM
```

### Audit Trail — Tamper-Evident

```python
import hashlib

# Collection: audit_logs (append-only, tidak pernah update/delete)
# Index by month untuk archiving: audit_logs_2026_05

async def write_audit_log(
    db, actor: dict, action: str,
    resource_type: str, resource_id: str,
    before: dict = None, after: dict = None,
    warehouse_id: str = None
):
    timestamp = now_iso()
    doc = {
        "id": str(uuid4()),
        "timestamp": timestamp,
        "actor_id": actor["id"],
        "actor_name": actor.get("name", ""),  # Snapshot, bukan FK
        "actor_role": actor.get("role", ""),
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "warehouse_id": warehouse_id,
        "before": before,
        "after": after,
        "source": "web",
        # Checksum untuk deteksi tampering
        "checksum": hashlib.sha256(
            f"{timestamp}{actor['id']}{action}{resource_id}".encode()
        ).hexdigest()
    }
    await db.audit_logs.insert_one(doc)

# Wajib audit:
AUDITABLE_ACTIONS = [
    "STOCK_ADJUSTMENT", "CYCLE_COUNT_CLOSE",
    "USER_ROLE_CHANGE", "USER_LOGIN_FAIL", "USER_LOGIN_SUCCESS",
    "BULK_EXPORT", "DOCUMENT_VOID", "PRICE_CHANGE",
    "RFID_TAG_REASSIGN", "WAREHOUSE_ACCESS_GRANT",
    "PAYMENT_APPROVED", "INVOICE_VOIDED",
    "GOODS_RECEIPT_CREATED", "GOODS_RECEIPT_ADJUSTED"
]
```

### Audit Log Retention

```
Hot  (MongoDB primary):    0-24 bulan (queryable, indexed)
Warm (MongoDB minimal idx): 24-60 bulan (queryable, minimal index)
Cold (Archive/S3):          60+ bulan (tidak queryable langsung)

Implementasi: Monthly collection rotation
  audit_logs_2026_05, audit_logs_2026_06, ...
  TTL: tidak ada (audit tidak pernah expire otomatis)
  Manual archive: cron job setiap bulan
```

---

## Layer 5 — RFID Security

```
Threat 1: Rogue Reader
  → Mutual TLS per reader (certificate-based auth)
  → MQTT broker: whitelist client_id per warehouse
  → reader_id harus terdaftar di DB
  → Event dari unknown reader_id → reject + alert

Threat 2: Replay Attack
  → Sequence number per reader (monotonically increasing)
  → Timestamp window: event >30 detik → reject
  → Idempotency: sequence_id unique per reader

Threat 3: Tag Cloning
  → Tag registration: setiap EPC terdaftar saat receiving
  → Duplicate detection: same EPC di 2 zone berbeda simultan → fraud alert
  → Lock bit EPC Gen2 setelah encoding

Threat 4: MQTT Broker
  → TLS 1.3 only (tidak ada plain text)
  → Topic ACL: RFID service hanya bisa publish ke rfid/events/#
  → Rate limit per client_id
```

---

## Environment & Secrets

```
✅ SELALU:
  - Secrets di .env file (tidak di-commit ke git)
  - .env.example di-commit (template tanpa values)
  - Akses via os.environ.get() atau process.env
  - Production secrets via vault / environment injection

🚫 JANGAN:
  - Hardcode API key, JWT secret, password di code
  - Commit .env file
  - Log secrets ke console atau file
  - Kirim secrets dalam response body
  - Gunakan secrets di URL parameter

Environment separation:
  DEV:        .env.development (simple secrets OK)
  STAGING:    .env.staging (mirror prod structure)
  PRODUCTION: Environment injection (vault)
```
