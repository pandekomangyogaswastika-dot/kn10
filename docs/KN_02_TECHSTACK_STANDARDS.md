# KN_02 — TECH STACK STANDARDS
## Kain Nusantara Platform — Coding Patterns & Standards

**Versi:** 1.0 | **Berlaku sejak:** 2026-05-23

---

## Stack Overview

```
BACKEND
  Framework:      FastAPI (Python 3.11+)
  DB Driver:      Motor (async MongoDB)
  Cache/PubSub:   Redis (aioredis)
  Validation:     Pydantic v2
  Scheduler:      APScheduler
  MQTT Client:    aiomqtt
  Auth:           python-jose (JWT)
  Password:       passlib (bcrypt)

FRONTEND
  Framework:      React 19
  Styling:        TailwindCSS + Shadcn/UI
  Server State:   TanStack Query (React Query v5)
  Client State:   Zustand
  Charts:         Apache ECharts (echarts-for-react)
  Real-time:      WebSocket (native) + SSE
  Router:         React Router v6
  Forms:          React Hook Form + Zod
  Icons:          Lucide React
  Virtual Scroll: TanStack Virtual

DATABASE & MESSAGING
  Primary DB:     MongoDB
  Cache + RT:     Redis
  RFID Broker:    EMQX / Mosquitto (MQTT)

RFID LAYER
  Edge Agent:     Python (per warehouse)
  Protocol:       LLRP / TCP (Chainway UHF)
  Transport:      MQTT over TLS
```

---

## BACKEND — FastAPI Patterns

### 1. Router Organization (Domain-Based)

```python
# ✅ BENAR: Domain-based, satu file per aggregate
/app/backend/routers/
  warehouse_locations.py    # Location hierarchy CRUD
  warehouse_movements.py    # Stock movements
  inventory_items.py        # Item master
  inventory_stock.py        # Stock levels
  sales_orders.py           # Sales orders
  sales_pos.py              # POS transactions
  finance_ar.py             # Accounts Receivable
  finance_ap.py             # Accounts Payable

# ❌ SALAH: Feature-based tanpa domain
  create_order.py
  list_orders.py
  approve_orders.py
```

### 2. Router File Structure

```python
"""
Inventory Stock Router
======================
Endpoints untuk manajemen stok per gudang.

Endpoints:
- GET    /api/v1/inventory/stock              List stok dengan filter
- GET    /api/v1/inventory/stock/{item_id}    Detail stok per item
- POST   /api/v1/inventory/stock/adjust       Adjustment manual
- GET    /api/v1/inventory/stock/alerts       Safety stock alerts

Collections: inventory_stock, inventory_items
Dependencies: auth, db, warehouse_scope
Last updated: YYYY-MM-DD
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from ..dependencies import get_db, require_auth, require_permission
from ..schemas.inventory import StockAdjustRequest, StockAdjustResponse
from ..core_utils import now_iso, paginate_response

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])

# ─── Stock Endpoints ──────────────────────────────────────────────

@router.get("/stock")
async def list_stock(
    warehouse_id: Optional[str] = Query(None),
    item_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("updated_at"),
    sort_dir: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    user=Depends(require_auth)
):
    # Warehouse scope dari token, bukan dari request
    allowed_warehouses = user.get("warehouse_ids", [])
    ...
```

### 3. Dependency Injection Pattern

```python
# dependencies.py — Centralized

async def get_db():
    """MongoDB database instance."""
    return db

async def require_auth(request: Request) -> dict:
    """Extract & validate JWT dari HttpOnly cookie."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(401, "Tidak terautentikasi")
    try:
        payload = verify_jwt(token)
        return payload
    except Exception:
        raise HTTPException(401, "Token tidak valid atau kadaluarsa")

def require_permission(resource: str, action: str):
    """Factory untuk permission check."""
    async def checker(user=Depends(require_auth), db=Depends(get_db)):
        has_perm = await check_permission(db, user["role"], resource, action)
        if not has_perm:
            raise HTTPException(403, f"Akses ditolak: {resource}:{action}")
        return user
    return checker

def require_warehouse_scope():
    """Inject warehouse filter dari token."""
    async def checker(user=Depends(require_auth)):
        if "global" in user.get("scope", []):
            return None  # No filter, lihat semua
        return {"warehouse_id": {"$in": user["warehouse_ids"]}}
    return checker
```

### 4. Pydantic Model Hierarchy

```python
# schemas/inventory.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime

# Base schema (shared fields)
class StockBase(BaseModel):
    item_id: str = Field(..., min_length=1)
    warehouse_id: str = Field(..., min_length=1)
    location_id: Optional[str] = None
    quantity: float = Field(..., ge=0)
    uom: Literal["roll", "meter", "kg", "pcs", "yard"]

# Request schema (input dari user)
class StockAdjustRequest(StockBase):
    model_config = ConfigDict(strict=True)
    reason: str = Field(..., min_length=5, max_length=500)
    reference_doc: Optional[str] = None
    # TIDAK ADA: id, created_at, created_by (dari server)

# Response schema (output ke client)
class StockAdjustResponse(StockBase):
    id: str
    adjustment_qty: float
    before_qty: float
    after_qty: float
    reason: str
    created_by: str
    created_at: str
    warehouse_name: str  # Denormalized untuk display

# DB schema (internal, tidak di-expose ke client)
class StockAdjustDB(StockBase):
    id: str
    adjustment_qty: float
    before_qty: float
    after_qty: float
    reason: str
    reference_doc: Optional[str]
    created_by: str
    created_by_name: str
    created_at: str
    updated_at: str
    tenant_id: str = "default"
```

### 5. Standard Exception Handling

```python
# Hierarchy exception yang konsisten
from fastapi import HTTPException

# Business rule violations → 422
class BusinessRuleError(HTTPException):
    def __init__(self, code: str, message: str, details: list = []):
        super().__init__(status_code=422, detail={
            "code": code,
            "message": message,
            "details": details
        })

# Contoh penggunaan:
if stock.quantity < requested_qty:
    raise BusinessRuleError(
        code="INSUFFICIENT_STOCK",
        message=f"Stok tidak mencukupi. Tersedia: {stock.quantity} {stock.uom}",
        details=[{"field": "quantity", "available": stock.quantity}]
    )

# Not found → 404
if not item:
    raise HTTPException(404, "Item tidak ditemukan")

# Concurrent update → 409
if not result:  # find_one_and_update returned None
    raise HTTPException(409, "Data telah berubah, coba lagi")
```

### 6. Atomic Stock Operations (Race Condition Prevention)

```python
# ✅ WAJIB untuk semua operasi yang ubah quantity
async def deduct_stock(db, item_id: str, warehouse_id: str, qty: float):
    result = await db.inventory_stock.find_one_and_update(
        {
            "item_id": item_id,
            "warehouse_id": warehouse_id,
            "quantity": {"$gte": qty}  # Cek cukup dalam satu operasi
        },
        {
            "$inc": {"quantity": -qty},
            "$set": {"updated_at": now_iso()}
        },
        return_document=True
    )
    if not result:
        raise BusinessRuleError("INSUFFICIENT_STOCK", "Stok tidak mencukupi")
    return result
```

---

## FRONTEND — React Patterns

### 1. Component Architecture (Atomic Design Lite)

```
/app/frontend/src/
  components/ui/          ← Shadcn components (jangan modifikasi)
  components/shared/      ← Shared app components
    DataTable.jsx         ← Table dengan virtual scroll
    PageHeader.jsx        ← Consistent page header
    EmptyState.jsx        ← Empty state component
    ConfirmDialog.jsx     ← Reusable confirm dialog
    StatusBadge.jsx       ← Status indicator
    ChartContainer.jsx    ← ECharts wrapper
  features/
    warehouse/            ← Domain-based feature folders
      components/         ← Feature-specific components
      hooks/              ← Feature-specific hooks
      pages/              ← Page-level components
    inventory/
    sales/
    finance/
    hr/
    executive/
  hooks/                  ← Global custom hooks
  services/               ← API client
  utils/                  ← Pure utility functions
  stores/                 ← Zustand stores
```

### 2. TanStack Query Pattern (Server State)

```jsx
// hooks/useInventoryStock.js
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/apiClient';

// Query keys — centralized dan structured
export const stockKeys = {
  all: ['inventory', 'stock'],
  list: (filters) => [...stockKeys.all, 'list', filters],
  detail: (id) => [...stockKeys.all, 'detail', id],
  alerts: () => [...stockKeys.all, 'alerts'],
};

export function useStockList(filters) {
  return useQuery({
    queryKey: stockKeys.list(filters),
    queryFn: () => api.get('/inventory/stock', { params: filters }),
    staleTime: 30_000,       // 30 detik sebelum refetch
    gcTime: 5 * 60_000,      // 5 menit cache
    select: (data) => data.data,
  });
}

export function useStockAdjust() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload) => api.post('/inventory/stock/adjust', payload),
    onSuccess: () => {
      // Invalidate semua stock queries
      queryClient.invalidateQueries({ queryKey: stockKeys.all });
    },
    onError: (error) => {
      // Error handling centralized
      console.error('Stock adjust failed:', error.response?.data?.error);
    }
  });
}
```

### 3. Zustand Store Pattern (Client State)

```jsx
// stores/warehouseStore.js
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useWarehouseStore = create(persist(
  (set, get) => ({
    // State
    activeWarehouseId: null,
    activeWarehouseName: '',
    assignedWarehouses: [],

    // Actions
    setActiveWarehouse: (warehouse) => set({
      activeWarehouseId: warehouse.id,
      activeWarehouseName: warehouse.name,
    }),
    setAssignedWarehouses: (warehouses) => set({ assignedWarehouses: warehouses }),
    clearWarehouse: () => set({ activeWarehouseId: null, activeWarehouseName: '' }),
  }),
  {
    name: 'kn-warehouse',  // localStorage key
    partialize: (state) => ({ activeWarehouseId: state.activeWarehouseId }),
  }
));

// stores/authStore.js
export const useAuthStore = create((set) => ({
  user: null,
  isAuthenticated: false,
  setUser: (user) => set({ user, isAuthenticated: true }),
  clearAuth: () => set({ user: null, isAuthenticated: false }),
}));
```

### 4. Page Component Pattern

```jsx
// features/inventory/pages/StockPage.jsx
import { useState } from 'react';
import { useStockList, useStockAdjust } from '../hooks/useInventoryStock';
import { DataTable } from '@/components/shared/DataTable';
import { PageHeader } from '@/components/shared/PageHeader';
import { EmptyState } from '@/components/shared/EmptyState';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Alert, AlertDescription } from '@/components/ui/alert';

export function StockPage() {
  const [filters, setFilters] = useState({});
  const { data, isLoading, error, refetch } = useStockList(filters);

  // ✅ Loading state — skeleton, bukan spinner
  if (isLoading) return <StockPageSkeleton />;

  // ✅ Error state — dengan retry
  if (error) return (
    <Alert variant="destructive">
      <AlertDescription>
        Gagal memuat data stok. <Button onClick={refetch}>Coba Lagi</Button>
      </AlertDescription>
    </Alert>
  );

  // ✅ Empty state — kontekstual dengan action
  if (!data?.length) return (
    <EmptyState
      icon={Package}
      title="Belum ada data stok"
      description="Mulai dengan melakukan penerimaan barang pertama"
      action={<Button>+ Penerimaan Baru</Button>}
    />
  );

  return (
    <div className="h-full flex flex-col" data-testid="stock-page">
      <PageHeader
        title="Stok & Inventori"
        description="Monitor stok real-time per lokasi"
      />
      <DataTable data={data} columns={stockColumns} />
    </div>
  );
}
```

### 5. API Client Pattern

```javascript
// services/apiClient.js
import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';

export const api = axios.create({
  baseURL: `${process.env.REACT_APP_BACKEND_URL}/api/v1`,
  withCredentials: true,  // Kirim HttpOnly cookie
  timeout: 30_000,
});

// Request interceptor — inject request ID
api.interceptors.request.use((config) => {
  config.headers['X-Request-ID'] = crypto.randomUUID();
  return config;
});

// Response interceptor — handle 401
api.interceptors.response.use(
  (response) => response.data,  // Unwrap envelope
  async (error) => {
    if (error.response?.status === 401) {
      // Try silent refresh
      try {
        await axios.post('/api/v1/auth/refresh', {}, { withCredentials: true });
        return api.request(error.config);  // Retry
      } catch {
        useAuthStore.getState().clearAuth();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
```

---

## FILE SIZE LIMITS — NON-NEGOTIABLE

```
React Component (.jsx):   MAX 500 baris
Python Router (.py):      MAX 800 baris
Utility/Helper (.js):     MAX 300 baris
CSS File:                 MAX 400 baris
Test File:                MAX 800 baris

Jika mendekati limit → SPLIT sebelum melewati batas
Jangan tunggu sampai 2000 baris baru dipecah
```

---

## NAMING CONVENTIONS

```
Python:
  snake_case          → variabel, fungsi, parameter
  PascalCase          → class, Pydantic model
  SCREAMING_SNAKE     → konstanta
  snake_case.py       → file names

JavaScript/React:
  camelCase           → variabel, fungsi, hook names (useSomething)
  PascalCase          → React components, class
  SCREAMING_SNAKE     → konstanta
  PascalCase.jsx      → component files
  camelCase.js        → utility files

MongoDB Collections:
  snake_case plural   → warehouse_locations, inventory_items
  Domain prefix:      → inventory_*, warehouse_*, sales_*, finance_*, hr_*

CSS:
  Gunakan Tailwind classes, hindari custom CSS
  Jika perlu custom → BEM dalam App.css
```
