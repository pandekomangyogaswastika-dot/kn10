# KN_11 — QUALITY LENSES
## Kain Nusantara Platform — Audit Framework & Quality Gates

**Versi:** 1.0 | **Berlaku sejak:** 2026-05-23

---

## 🔍 PURPOSE

Quality Lenses adalah **framework audit** untuk mengevaluasi kualitas code, architecture, dan UX dari berbagai perspektif. Setiap "lens" adalah sudut pandang yang berbeda untuk melihat kualitas sistem.

**Gunakan untuk:**
1. **Code review** — Reviewer gunakan lenses relevan untuk audit PR
2. **Refactoring decisions** — Identifikasi area dengan technical debt tertinggi
3. **New feature planning** — Ensure feature design passes all lenses
4. **Sprint retrospective** — Evaluate sprint deliverables

---

## 🔬 THE 10 QUALITY LENSES

### LENS 1: Code Readability
**Question:** "Apakah developer baru bisa memahami code ini dalam <10 menit?"

#### Checklist:
- [ ] Function names self-explanatory (no `func1`, `doStuff`)
- [ ] Variable names meaningful (no `x`, `temp`, `data`)
- [ ] Comments explain **WHY**, not WHAT
- [ ] Max function length: 50 lines (Python), 30 lines (JS)
- [ ] No deeply nested logic (max 3 levels)
- [ ] Consistent naming convention (snake_case Python, camelCase JS)

#### Red Flags:
```python
# ❌ BAD
def f(x, y):
    r = []
    for i in x:
        if i > y:
            r.append(i)
    return r

# ✅ GOOD
def filter_products_above_price(products: list, min_price: float) -> list:
    """Return products with price greater than min_price."""
    return [product for product in products if product['price'] > min_price]
```

---

### LENS 2: Architecture Coherence
**Question:** "Apakah code organization konsisten dengan principles yang ditetapkan?"

#### Checklist:
- [ ] Follows domain-based structure (not feature-based chaos)
- [ ] Dependencies flow one direction (no circular imports)
- [ ] Separation of concerns (UI ≠ business logic ≠ data access)
- [ ] DRY principle (no copy-paste code blocks)
- [ ] SSOT principle (one source of truth per entity)

#### Red Flags:
- Multiple collections untuk same entity (`products` + `product_master`)
- Business logic di UI component (calculation inside JSX)
- Circular imports (`A imports B imports A`)
- God files (>800 lines Python, >500 lines JSX)

---

### LENS 3: Data Integrity
**Question:** "Apakah data consistency terjamin dalam semua scenarios?"

#### Checklist:
- [ ] Atomic operations untuk critical updates (stock, payment)
- [ ] Transactions where needed (multi-step updates)
- [ ] Validation at entry point (API layer)
- [ ] Foreign key integrity (manual checks untuk MongoDB)
- [ ] No orphaned records (cascade delete logic)
- [ ] Audit trail untuk sensitive operations

#### Red Flags:
```python
# ❌ BAD: Race condition
available = db.get_stock(product_id)
if available >= qty:
    db.decrement_stock(product_id, qty)  # Another request bisa decrement between check & update!

# ✅ GOOD: Atomic operation
result = db.find_one_and_update(
    {"product_id": product_id, "available": {"$gte": qty}},
    {"$inc": {"available": -qty}},
    return_document=True
)
if not result:
    raise InsufficientStockError()
```

---

### LENS 4: Error Handling & Resilience
**Question:** "Apa yang terjadi ketika things go wrong?"

#### Checklist:
- [ ] All API endpoints have try-except
- [ ] Error messages user-friendly (not raw stack trace)
- [ ] Graceful degradation (feature unavailable ≠ app crash)
- [ ] Retry logic untuk transient failures (network timeout)
- [ ] Fallback values untuk non-critical data

#### Red Flags:
- Bare `except:` tanpa specific exception
- Error messages expose internal details (SQL query, file paths)
- No error state UI (just white screen)
- No retry button untuk failed actions

---

### LENS 5: Performance & Scalability
**Question:** "Apakah code ini efficient untuk 10x data/traffic?"

#### Checklist:
- [ ] Database queries use indexes
- [ ] No N+1 query patterns
- [ ] Pagination implemented (no unlimited fetch)
- [ ] Expensive operations memoized/cached
- [ ] Large lists use virtualization
- [ ] Images lazy-loaded

#### Red Flags:
```python
# ❌ BAD: N+1
orders = db.orders.find().to_list(None)  # 1000+ orders
for order in orders:
    customer = db.customers.find_one({"id": order["customer_id"]})  # 1000 queries!

# ✅ GOOD: Single aggregation
orders = db.orders.aggregate([
    {"$lookup": {"from": "customers", "localField": "customer_id", "foreignField": "id", "as": "customer"}}
]).to_list(1000)
```

---

### LENS 6: Security & Privacy
**Question:** "Apakah code ini aman dari common vulnerabilities?"

#### Checklist:
- [ ] No hardcoded secrets (API keys, passwords)
- [ ] SQL/NoSQL injection prevention (parameterized queries)
- [ ] XSS prevention (sanitize user input)
- [ ] CSRF protection (for state-changing requests)
- [ ] Authentication for all protected endpoints
- [ ] Authorization checks (role-based permissions)
- [ ] Sensitive data encrypted at rest

#### Red Flags:
```python
# ❌ BAD: SQL injection
query = f"SELECT * FROM users WHERE email = '{user_email}'"  # Exploitable!

# ✅ GOOD: Parameterized
query = "SELECT * FROM users WHERE email = %s"
db.execute(query, (user_email,))

# ❌ BAD: Hardcoded secret
OPENAI_API_KEY = "sk-abc123xyz"  # Committed to Git!

# ✅ GOOD: Environment variable
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
```

---

### LENS 7: Testability
**Question:** "Apakah code ini mudah di-test?"

#### Checklist:
- [ ] Functions are pure (same input → same output)
- [ ] Dependencies injectable (not hardcoded globals)
- [ ] Side effects isolated (I/O, API calls)
- [ ] No hidden state (explicit parameters)
- [ ] All interactive elements have `data-testid`

#### Red Flags:
```python
# ❌ BAD: Untestable (global state, side effect)
def process_order():
    order_id = get_current_order()  # Global state
    order = db.orders.find_one({"id": order_id})  # Direct DB call
    send_email(order["customer_email"])  # Side effect
    return order

# ✅ GOOD: Testable
def process_order(order_id: str, db_client, email_service):
    order = db_client.orders.find_one({"id": order_id})
    email_service.send(order["customer_email"])
    return order
```

---

### LENS 8: User Experience (UX)
**Question:** "Apakah user bisa accomplish task dengan mudah & cepat?"

#### Checklist:
- [ ] Loading states visible (skeleton/spinner)
- [ ] Empty states helpful (icon + description + action)
- [ ] Error states actionable (retry button, clear message)
- [ ] Success feedback immediate (toast/confirmation)
- [ ] No surprise behaviors (confirm destructive actions)
- [ ] Keyboard navigable (tab order logical)
- [ ] Mobile-friendly (touch targets ≥44px)

#### Red Flags:
- Delete button tanpa confirmation dialog
- Form submission tanpa loading indicator
- Error message: "Error 500" (tidak helpful)
- List kosong tanpa explanation atau action

---

### LENS 9: Maintainability
**Question:** "Berapa effort untuk modify/extend code ini 6 bulan dari sekarang?"

#### Checklist:
- [ ] Code well-documented (README, docstrings)
- [ ] Dependencies up-to-date (no deprecated packages)
- [ ] No "magic numbers" (constants named)
- [ ] Config externalized (not hardcoded)
- [ ] Version controlled (Git history clean)
- [ ] CI/CD pipeline exists

#### Red Flags:
```python
# ❌ BAD: Magic numbers
if order.total > 5000000:  # What is 5000000?
    apply_discount(order, 0.1)  # What is 0.1?

# ✅ GOOD: Named constants
FREE_SHIPPING_THRESHOLD = 5_000_000  # Rp 5 juta
BULK_DISCOUNT_RATE = 0.1  # 10%

if order.total > FREE_SHIPPING_THRESHOLD:
    apply_discount(order, BULK_DISCOUNT_RATE)
```

---

### LENS 10: Business Value Alignment
**Question:** "Apakah feature ini solve real user problem?"

#### Checklist:
- [ ] Feature maps to PRD requirement
- [ ] Solves measurable pain point
- [ ] User feedback positive (if MVP tested)
- [ ] Metrics defined (how to measure success)
- [ ] Cost-benefit favorable (ROI positive)

#### Red Flags:
- Feature added "because it's cool"
- No user requested this feature
- Adds complexity without clear value
- Duplicates existing feature

---

## 🎯 QUALITY SCORE CALCULATION

### Scoring System
For each lens:
- **Pass** = All checklist items ✅
- **Partial** = 50-80% checklist items ✅
- **Fail** = <50% checklist items ✅

### Overall Quality Grade
```
A+ (Excellent): 10/10 lenses Pass
A  (Great): 8-9/10 lenses Pass, rest Partial
B  (Good): 6-7/10 lenses Pass, no Fail
C  (Acceptable): 5/10 lenses Pass, max 2 Fail
D  (Needs Work): 3-4/10 lenses Pass, multiple Fail
F  (Unacceptable): <3 lenses Pass
```

### Threshold untuk Merge
**Minimum grade B** untuk merge ke `main`.

---

## 🛠️ USAGE PATTERNS

### 1. Code Review (PR)
```markdown
## Quality Lens Review

### LENS 1: Code Readability - ✅ PASS
- Function names clear
- Good comments

### LENS 2: Architecture - ⚠️ PARTIAL
- DRY principle violated (line 45-60 duplicate logic)
- Suggest: Extract to helper function

### LENS 5: Performance - ❌ FAIL
- N+1 query detected (line 123)
- No pagination (line 145)
- **BLOCKER:** Must fix before merge

**Overall Grade: C (Acceptable with fixes)**
**Action Required:** Fix Performance issues (LENS 5)
```

### 2. Sprint Retrospective
```markdown
## Sprint 12 Quality Assessment

**Features Delivered:** 5
**Average Quality Grade:** B+

**Strengths:**
- All features have excellent UX (LENS 8: 5/5 Pass)
- Performance optimized (LENS 5: 5/5 Pass)

**Improvement Areas:**
- Testability low (LENS 7: 2/5 Pass, 3/5 Partial)
  → Action: Add pytest workshop next sprint
- Documentation lacking (LENS 9: 3/5 Pass)
  → Action: Enforce docstring requirement
```

### 3. Refactoring Priority
```python
# Run quality audit on all modules
modules = [
    {"name": "sales_orders.py", "grade": "A"},
    {"name": "inventory.py", "grade": "B"},
    {"name": "wms.py", "grade": "D"},  # ⚠️ Priority refactor!
    {"name": "reporting.py", "grade": "C"},
]

# Prioritize modules with grade D or F
refactor_queue = [m for m in modules if m["grade"] in ["D", "F"]]
```

---

## 📝 AUDIT TEMPLATE

```markdown
# Quality Lens Audit: [Feature/Module Name]

**Date:** YYYY-MM-DD  
**Auditor:** [Name]  
**Scope:** [What is being audited]

---

## LENS 1: Code Readability
- [ ] Function names self-explanatory
- [ ] Variable names meaningful
- [ ] Comments explain WHY
- [ ] Max function length adhered
- [ ] No deeply nested logic
- [ ] Consistent naming

**Grade:** [Pass / Partial / Fail]  
**Notes:** [Specific observations]

---

## LENS 2: Architecture Coherence
[... repeat for each lens ...]

---

## OVERALL ASSESSMENT

**Quality Grade:** [A+ to F]  
**Pass Count:** X/10  
**Partial Count:** Y/10  
**Fail Count:** Z/10

### Strengths
1. [Strength 1]
2. [Strength 2]

### Improvement Areas
1. [Area 1] (Lens X: Fail)
2. [Area 2] (Lens Y: Partial)

### Action Items
- [ ] [Action 1] (Priority: High/Medium/Low)
- [ ] [Action 2]

**Recommendation:** [Merge / Merge with conditions / Block until fixes / Major refactor needed]
```

---

**Last Updated:** 23 Mei 2026  
**Maintained by:** Development + QA Team  
**Review Cycle:** Per sprint retrospective
