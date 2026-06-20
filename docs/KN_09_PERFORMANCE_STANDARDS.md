# KN_09 — PERFORMANCE STANDARDS
## Kain Nusantara Platform — Performance Optimization Rules

**Versi:** 1.0 | **Berlaku sejak:** 2026-05-23

---

## 🎯 PERFORMANCE TARGETS

### Page Load Time (P95)
| Page Type | Target | Measurement |
|---|---|---|
| Dashboard (cold start) | <2s | First Contentful Paint |
| List views (orders, inventory) | <1.5s | Time to Interactive |
| Detail panels (order detail) | <800ms | Content visible |
| Form submissions | <1s | Response feedback |

### Bundle Size
```
Frontend:
  Initial bundle: <500KB (gzipped)
  Total app: <2MB (gzipped)
  Lazy-loaded chunks: <150KB each

Backend:
  API response size: <1MB per request
  Paginate if > 100 records
```

### Database Query Time
```
Single document fetch: <50ms
List queries (paginated): <200ms
Aggregation pipelines: <500ms
Complex reports: <2s
```

---

## 🔧 BACKEND OPTIMIZATION

### 1. Database Query Optimization

#### ✅ ALWAYS Use Indexes
```python
# ✅ GOOD: Query uses index
result = await db.products.find(
    {"sku": "BTK-001", "status": "active"},  # Both indexed
    {"_id": 0, "id": 1, "name": 1, "price": 1}  # Projection
).to_list(100)

# ❌ BAD: Full collection scan
result = await db.products.find(
    {"$where": "this.price > 100000"}  # No index usage!
).to_list(None)  # No limit!
```

#### ✅ ALWAYS Use Projection
```python
# ✅ GOOD: Only fetch needed fields
products = await db.products.find(
    {"category": "Batik"},
    {"_id": 0, "id": 1, "sku": 1, "name": 1, "price": 1}
).to_list(100)

# ❌ BAD: Fetch all fields (including large image_data)
products = await db.products.find({"category": "Batik"}).to_list(100)
```

#### ✅ ALWAYS Paginate
```python
# ✅ GOOD: Pagination
page = int(request.query_params.get("page", 1))
limit = int(request.query_params.get("limit", 20))
skip = (page - 1) * limit

results = await db.collection.find(filter).skip(skip).limit(limit).to_list(limit)
total = await db.collection.count_documents(filter)

return {
    "data": results,
    "pagination": {
        "page": page,
        "limit": limit,
        "total": total,
        "pages": math.ceil(total / limit)
    }
}

# ❌ BAD: Return all documents
results = await db.collection.find(filter).to_list(None)
return {"data": results}  # Could be 10,000+ records!
```

### 2. Prevent N+1 Queries

#### ❌ BAD: N+1 Query
```python
orders = await db.sales_orders.find({}).to_list(100)
for order in orders:
    customer = await db.customers.find_one({"id": order["customer_id"]})
    order["customer_name"] = customer["name"]  # 100 extra queries!
```

#### ✅ GOOD: Batch Fetch or Denormalize
```python
# Option 1: Aggregation with $lookup
pipeline = [
    {"$match": {}},
    {"$lookup": {
        "from": "customers",
        "localField": "customer_id",
        "foreignField": "id",
        "as": "customer"
    }},
    {"$unwind": "$customer"},
    {"$limit": 100}
]
orders = await db.sales_orders.aggregate(pipeline).to_list(100)

# Option 2: Denormalize (store customer_name in order)
# At order creation, save customer name snapshot
order_doc = {
    "customer_id": customer_id,
    "customer_name": customer["name"],  # Denormalized
    ...
}
```

### 3. Caching Strategy (Future: Redis)

```python
# Pattern untuk high-read, low-write data
import redis

cache = redis.Redis()

async def get_product(product_id: str):
    # Try cache first
    cached = cache.get(f"product:{product_id}")
    if cached:
        return json.loads(cached)
    
    # Cache miss: fetch from DB
    product = await db.products.find_one({"id": product_id})
    if product:
        cache.setex(f"product:{product_id}", 3600, json.dumps(product))
    return product
```

---

## ⚛️ FRONTEND OPTIMIZATION

### 1. Code Splitting & Lazy Loading

```jsx
// ✅ GOOD: Lazy load heavy components
import { lazy, Suspense } from 'react';
import { Skeleton } from '@/components/ui/skeleton';

const ReportsDashboard = lazy(() => import('./features/reports/ReportsDashboard'));

function App() {
  return (
    <Suspense fallback={<Skeleton className="h-96" />}>
      <ReportsDashboard />
    </Suspense>
  );
}

// ❌ BAD: Import everything upfront
import ReportsDashboard from './features/reports/ReportsDashboard';
import AnalyticsCharts from './features/analytics/AnalyticsCharts';
import AdminPanel from './features/admin/AdminPanel';
// ... (500KB bundle on initial load)
```

### 2. Image Optimization

```jsx
// ✅ GOOD: Lazy load images, use correct format
<img 
  src={product.image} 
  alt={product.name}
  loading="lazy"  // Native lazy load
  width={300}
  height={200}
  className="object-cover"
/>

// Future: Use WebP with fallback
<picture>
  <source srcSet={product.image_webp} type="image/webp" />
  <img src={product.image_jpg} alt={product.name} loading="lazy" />
</picture>

// ❌ BAD: Load all images eagerly
{products.map(p => (
  <img src={p.image} alt={p.name} />  // No lazy load, no sizing
))}
```

### 3. List Virtualization (Large Datasets)

```jsx
// ✅ GOOD: Virtual scroll for >100 items
import { useVirtualizer } from '@tanstack/react-virtual';

function InventoryList({ items }) {
  const parentRef = useRef();
  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 60,  // Row height
  });

  return (
    <div ref={parentRef} className="h-96 overflow-auto">
      <div style={{ height: virtualizer.getTotalSize() }}>
        {virtualizer.getVirtualItems().map((virtualRow) => (
          <div key={virtualRow.index} className="h-[60px]">
            {items[virtualRow.index].name}
          </div>
        ))}
      </div>
    </div>
  );
}

// ❌ BAD: Render all 1000+ items
function InventoryList({ items }) {
  return items.map(item => <InventoryRow key={item.id} item={item} />);
}
```

### 4. Debounce Search Input

```jsx
// ✅ GOOD: Debounce 300ms
import { useDebouncedValue } from '@/hooks/useDebounce';

function SearchBar() {
  const [search, setSearch] = useState('');
  const debouncedSearch = useDebouncedValue(search, 300);

  useEffect(() => {
    if (debouncedSearch) {
      fetchResults(debouncedSearch);  // Only after 300ms idle
    }
  }, [debouncedSearch]);

  return <Input value={search} onChange={(e) => setSearch(e.target.value)} />;
}

// ❌ BAD: API call on every keystroke
function SearchBar() {
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchResults(search);  // API spam!
  }, [search]);

  return <Input value={search} onChange={(e) => setSearch(e.target.value)} />;
}
```

### 5. Memoization (React.memo, useMemo, useCallback)

```jsx
// ✅ GOOD: Memoize expensive components
const ExpensiveChart = React.memo(function ExpensiveChart({ data }) {
  // Only re-renders if data changes
  return <ChartComponent data={data} />;
});

// ✅ GOOD: useMemo untuk expensive calculations
function Dashboard({ orders }) {
  const stats = useMemo(() => {
    return orders.reduce((acc, order) => {
      acc.total += order.total;
      acc.count += 1;
      return acc;
    }, { total: 0, count: 0 });
  }, [orders]);  // Only recalculate when orders change

  return <div>Total: {stats.total}</div>;
}

// ❌ BAD: Recalculate on every render
function Dashboard({ orders }) {
  const stats = orders.reduce(...)  // Runs every render!
  return <div>Total: {stats.total}</div>;
}
```

---

## 🌐 NETWORK OPTIMIZATION

### 1. API Response Compression (Backend)

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)  # Compress responses >1KB
```

### 2. HTTP Caching Headers

```python
from fastapi import Response

@app.get("/api/products")
async def list_products(response: Response):
    products = await db.products.find({}).to_list(100)
    
    # Cache for 5 minutes (300 seconds)
    response.headers["Cache-Control"] = "public, max-age=300"
    
    return {"data": products}
```

### 3. Prefetching (React Query)

```jsx
// ✅ GOOD: Prefetch related data
import { useQuery, useQueryClient } from '@tanstack/react-query';

function OrderList() {
  const queryClient = useQueryClient();
  const { data: orders } = useQuery(['orders'], fetchOrders);

  const handleOrderHover = (orderId) => {
    // Prefetch order details on hover
    queryClient.prefetchQuery(
      ['order', orderId],
      () => fetchOrderDetail(orderId)
    );
  };

  return orders.map(order => (
    <OrderCard 
      key={order.id} 
      order={order}
      onMouseEnter={() => handleOrderHover(order.id)}
    />
  ));
}
```

---

## 📊 MONITORING & PROFILING

### Backend Monitoring

```python
import time
from fastapi import Request

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    
    # Log slow queries (>1s)
    if duration > 1.0:
        print(f"SLOW REQUEST: {request.url} took {duration:.2f}s")
    
    response.headers["X-Process-Time"] = str(duration)
    return response
```

### Frontend Profiling

```jsx
// Use React DevTools Profiler
import { Profiler } from 'react';

function App() {
  return (
    <Profiler id="App" onRender={(id, phase, actualDuration) => {
      if (actualDuration > 16) {  // > 16ms = dropped frame
        console.warn(`Slow render: ${id} took ${actualDuration}ms`);
      }
    }}>
      <MainApp />
    </Profiler>
  );
}
```

---

## 🚫 PERFORMANCE ANTI-PATTERNS

### ❌ 1. Fetch Inside Loop
```python
# ❌ BAD
for order_id in order_ids:
    order = await db.orders.find_one({"id": order_id})  # N queries!

# ✅ GOOD
orders = await db.orders.find({"id": {"$in": order_ids}}).to_list(len(order_ids))
```

### ❌ 2. Large Aggregation Without Limit
```python
# ❌ BAD
pipeline = [
    {"$match": {}},
    {"$group": {...}},
    {"$sort": {...}}
]  # Could process millions of documents!

# ✅ GOOD
pipeline = [
    {"$match": {}},
    {"$group": {...}},
    {"$sort": {...}},
    {"$limit": 1000}  # Cap result size
]
```

### ❌ 3. Inline Styles (React)
```jsx
// ❌ BAD: New object every render
<div style={{ padding: '16px', background: '#fff' }}>...</div>

// ✅ GOOD: CSS class
<div className="p-4 bg-white">...</div>
```

### ❌ 4. Unnecessary Re-renders
```jsx
// ❌ BAD: New function every render
function Parent() {
  return <Child onClick={() => console.log('click')} />;  // New function!
}

// ✅ GOOD: useCallback
function Parent() {
  const handleClick = useCallback(() => console.log('click'), []);
  return <Child onClick={handleClick} />;
}
```

---

## ✅ PERFORMANCE CHECKLIST

Before deploying to production:

### Backend
- [ ] All queries use indexes (verify with EXPLAIN)
- [ ] All list endpoints paginated (max 100 per page)
- [ ] Projection used (only fetch needed fields)
- [ ] No N+1 queries
- [ ] GZip compression enabled
- [ ] Slow query logging enabled (>1s)

### Frontend
- [ ] Bundle size <500KB initial (gzipped)
- [ ] Code splitting implemented (lazy load routes)
- [ ] Images lazy-loaded
- [ ] Search inputs debounced (300ms)
- [ ] Lists >100 items use virtual scroll
- [ ] Expensive computations memoized
- [ ] React DevTools Profiler shows no >16ms renders

---

**Last Updated:** 23 Mei 2026  
**Maintained by:** Development Team  
**Review Cycle:** Quarterly
