# KN_10 — TESTING STANDARDS
## Kain Nusantara Platform — Testing Guide & Best Practices

**Versi:** 1.0 | **Berlaku sejak:** 2026-05-23

---

## 🎯 TESTING PHILOSOPHY

### Testing Pyramid
```
        /\
       /  \   E2E Tests (10%)
      /────\   - Critical user flows
     /      \   - Playwright
    /────────\
   / Integration\  Integration Tests (30%)
  /  Tests (30%) \  - API endpoints
 /────────────────\
/ Unit Tests (60%) \  - Pure functions
\──────────────────/  - Business logic
                      - pytest / Jest
```

### Coverage Targets
```
Backend (Python):
  Unit tests: 70% coverage minimum
  Integration tests: All API endpoints
  E2E: Critical flows only

Frontend (React):
  Component tests: 60% coverage minimum
  Integration tests: User interactions
  E2E: 5-10 critical paths
```

---

## 🐍 BACKEND TESTING (Python + pytest)

### Test Structure
```
/app/tests/
  conftest.py           # Fixtures & config
  test_auth.py          # Auth endpoints
  test_products.py      # Product endpoints
  test_sales_orders.py  # Sales order logic
  test_wms.py           # WMS operations
  /fixtures/
    seed_data.py        # Test data factory
```

### 1. Fixtures (conftest.py)

```python
import pytest
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from httpx import AsyncClient
from backend.server import app
from backend.db import db

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def test_db():
    """Isolated test database per test."""
    # Use test database
    test_client = AsyncIOMotorClient("mongodb://localhost:27017")
    test_db_instance = test_client["kn_test_db"]
    
    yield test_db_instance
    
    # Cleanup after test
    await test_client.drop_database("kn_test_db")
    test_client.close()

@pytest.fixture(scope="function")
async def test_client(test_db):
    """FastAPI test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture(scope="function")
async def auth_headers(test_db, test_client):
    """Authenticated admin user headers."""
    # Create test user
    await test_db.users.insert_one({
        "id": "test_admin",
        "email": "admin@test.com",
        "password_hash": hash_password("testpass"),
        "role": "admin",
        "status": "active"
    })
    
    # Login
    response = await test_client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "testpass"
    })
    token = response.json()["token"]
    
    return {"Authorization": f"Bearer {token}"}
```

### 2. Unit Tests (Pure Functions)

```python
# test_utils.py
import pytest
from backend.core_utils import calculate_order_total, allocate_stock

def test_calculate_order_total():
    items = [
        {"price": 100000, "quantity": 2},  # 200,000
        {"price": 50000, "quantity": 3},   # 150,000
    ]
    total = calculate_order_total(items)
    assert total == 350000

def test_calculate_order_total_with_discount():
    items = [{"price": 100000, "quantity": 1}]
    discount = 10000
    total = calculate_order_total(items, discount=discount)
    assert total == 90000

@pytest.mark.parametrize("requested,available,expected", [
    (100, 200, 100),  # Enough stock
    (200, 100, 100),  # Partial allocation
    (100, 0, 0),      # No stock
])
def test_allocate_stock(requested, available, expected):
    allocated = allocate_stock(requested, available)
    assert allocated == expected
```

### 3. Integration Tests (API Endpoints)

```python
# test_products.py
import pytest

@pytest.mark.asyncio
async def test_create_product(test_client, auth_headers, test_db):
    payload = {
        "sku": "TEST-001",
        "name": "Test Product",
        "category": "Batik",
        "price": 100000,
        "base_unit": "meter"
    }
    
    response = await test_client.post(
        "/api/products",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["sku"] == "TEST-001"
    
    # Verify in DB
    product = await test_db.products.find_one({"sku": "TEST-001"})
    assert product is not None
    assert product["name"] == "Test Product"

@pytest.mark.asyncio
async def test_create_product_duplicate_sku(test_client, auth_headers, test_db):
    # Create first product
    await test_db.products.insert_one({"id": "p1", "sku": "DUP-001", "name": "Existing"})
    
    # Try to create duplicate
    payload = {"sku": "DUP-001", "name": "Duplicate", "price": 50000}
    response = await test_client.post(
        "/api/products",
        json=payload,
        headers=auth_headers
    )
    
    assert response.status_code == 422  # Validation error
    assert "SKU sudah ada" in response.json()["detail"]

@pytest.mark.asyncio
async def test_list_products_with_pagination(test_client, auth_headers, test_db):
    # Seed 50 products
    products = [{"id": f"p{i}", "sku": f"SKU-{i:03d}", "name": f"Product {i}"} 
                for i in range(50)]
    await test_db.products.insert_many(products)
    
    # Request page 2, limit 20
    response = await test_client.get(
        "/api/products?page=2&limit=20",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 20
    assert data["pagination"]["page"] == 2
    assert data["pagination"]["total"] == 50
    assert data["pagination"]["pages"] == 3
```

### 4. Business Logic Tests

```python
# test_sales_orders.py
import pytest
from datetime import datetime, timezone, timedelta

@pytest.mark.asyncio
async def test_order_reservation_expiry(test_db):
    """Test that reservation expires after 3 days."""
    # Create order with expired reservation
    expired_time = datetime.now(timezone.utc) - timedelta(days=4)
    await test_db.sales_orders.insert_one({
        "id": "order1",
        "status": "reserved",
        "reservation_expires_at": expired_time.isoformat(),
        "items": [{"product_id": "p1", "quantity": 100}]
    })
    
    # Run expiry check (simulate cron job)
    from backend.services.reservation_service import check_expired_reservations
    expired_count = await check_expired_reservations(test_db)
    
    assert expired_count == 1
    
    # Verify order status updated
    order = await test_db.sales_orders.find_one({"id": "order1"})
    assert order["status"] == "cancelled"
    assert "reservation expired" in order.get("cancel_reason", "")

@pytest.mark.asyncio
async def test_stock_reservation_atomic(test_db):
    """Test that stock reservation prevents race conditions."""
    # Setup: 100 units available
    await test_db.inventory_balances.insert_one({
        "product_id": "p1",
        "warehouse_id": "wh1",
        "available_qty": 100,
        "reserved_qty": 0
    })
    
    # Simulate concurrent reservations
    from backend.services.inventory_service import reserve_stock
    
    # Try to reserve 60 + 60 = 120 (should partially fail)
    result1 = await reserve_stock(test_db, "p1", "wh1", 60)
    result2 = await reserve_stock(test_db, "p1", "wh1", 60)
    
    # One should succeed, one should partially allocate
    assert result1["reserved"] == 60
    assert result2["reserved"] == 40  # Only 40 left
    
    # Verify final state
    balance = await test_db.inventory_balances.find_one({"product_id": "p1"})
    assert balance["available_qty"] == 0
    assert balance["reserved_qty"] == 100
```

---

## ⚛️ FRONTEND TESTING (React + Jest + Playwright)

### Test Structure
```
/app/frontend/src/
  __tests__/
    components/
      Button.test.jsx
      DataTable.test.jsx
    features/
      sales/
        SalesPortal.test.jsx
      wms/
        InventoryStockView.test.jsx
  e2e/
    critical-flows.spec.js  # Playwright E2E
```

### 1. Component Unit Tests (Jest + React Testing Library)

```jsx
// __tests__/components/Button.test.jsx
import { render, screen, fireEvent } from '@testing-library/react';
import { Button } from '@/components/ui/button';

test('renders button with text', () => {
  render(<Button>Click me</Button>);
  expect(screen.getByText('Click me')).toBeInTheDocument();
});

test('calls onClick handler when clicked', () => {
  const handleClick = jest.fn();
  render(<Button onClick={handleClick}>Click me</Button>);
  
  fireEvent.click(screen.getByText('Click me'));
  expect(handleClick).toHaveBeenCalledTimes(1);
});

test('is disabled when disabled prop is true', () => {
  render(<Button disabled>Disabled</Button>);
  expect(screen.getByText('Disabled')).toBeDisabled();
});
```

### 2. Feature Integration Tests

```jsx
// __tests__/features/sales/SalesPortal.test.jsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SalesPortal } from '@/features/sales/SalesPortal';
import * as api from '@/services/apiClient';

jest.mock('@/services/apiClient');

test('adds product to cart', async () => {
  // Mock API
  api.get.mockResolvedValueOnce({
    data: [
      { id: 'p1', sku: 'BTK-001', name: 'Batik Mega', price: 185000 }
    ]
  });
  
  render(<SalesPortal />);
  
  // Wait for products to load
  await waitFor(() => {
    expect(screen.getByText('Batik Mega')).toBeInTheDocument();
  });
  
  // Add to cart
  const addButton = screen.getByTestId('add-to-cart-p1');
  await userEvent.click(addButton);
  
  // Verify cart updated
  expect(screen.getByText('1 item in cart')).toBeInTheDocument();
  expect(screen.getByText('Rp 185.000')).toBeInTheDocument();
});

test('shows empty state when no products', async () => {
  api.get.mockResolvedValueOnce({ data: [] });
  
  render(<SalesPortal />);
  
  await waitFor(() => {
    expect(screen.getByText('Belum ada produk')).toBeInTheDocument();
  });
});
```

### 3. E2E Tests (Playwright)

```javascript
// e2e/critical-flows.spec.js
import { test, expect } from '@playwright/test';

test.describe('Sales Order Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('https://kn8-erp-fix.preview.emergentagent.com');
    await page.fill('[data-testid="login-email"]', 'sales@kainnusantara.id');
    await page.fill('[data-testid="login-password"]', 'demo12345');
    await page.click('[data-testid="login-submit"]');
    
    // Wait for redirect to POS
    await page.waitForSelector('[data-testid="pos-catalog"]');
  });
  
  test('create order end-to-end', async ({ page }) => {
    // Step 1: Add product to cart
    await page.click('[data-testid="product-card-prod_batik_mega"]');
    await page.fill('[data-testid="quantity-input"]', '5');
    await page.click('[data-testid="add-to-cart-button"]');
    
    // Step 2: Select customer
    await page.click('[data-testid="customer-select"]');
    await page.click('[data-testid="customer-option-cust_toko_kain"]');
    
    // Step 3: Submit order
    await page.click('[data-testid="submit-order-button"]');
    
    // Step 4: Verify success
    await expect(page.locator('[data-testid="success-toast"]'))
      .toContainText('Order berhasil dibuat');
    
    // Step 5: Navigate to orders
    await page.click('[data-testid="nav-orders"]');
    
    // Step 6: Verify order appears
    await expect(page.locator('[data-testid^="order-card-"]').first())
      .toBeVisible();
  });
  
  test('approve order (manager)', async ({ page }) => {
    // ... (similar pattern)
  });
});
```

---

## ✅ TESTING CHECKLIST

### Before Merge to Main
- [ ] All new functions have unit tests
- [ ] All new API endpoints have integration tests
- [ ] All interactive components have data-testid
- [ ] Critical user flows have E2E tests
- [ ] All tests pass locally (`pytest` + `yarn test`)
- [ ] Coverage meets minimum threshold

### Test Quality
- [ ] Tests are independent (no shared state)
- [ ] Tests have descriptive names
- [ ] Tests assert specific outcomes (not just "no error")
- [ ] Mocks are isolated per test
- [ ] Cleanup happens after each test

---

**Last Updated:** 23 Mei 2026  
**Maintained by:** Development + QA Team  
**Review Cycle:** Per sprint
