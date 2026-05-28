# Cart Management API

A production-grade Cart Management API built with **Python + FastAPI + SQLite + Alembic**, featuring a minimal browser UI.

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ (3.14 supported) |
| Framework | FastAPI |
| Database | SQLite |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Validation | Pydantic v2 |
| UI | Vanilla HTML/CSS/JS |

---

## Setup & Run

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Seed the database

```bash
python seed.py
```

This inserts 20 products and 5 promotions.

### 5. Start the server

```bash
uvicorn main:app --reload
```

**One-liner:**
```bash
alembic upgrade head && python seed.py && uvicorn main:app --reload
```

### 6. Run the test suite (optional)

```bash
python -m pytest tests/ -v
```

105 tests covering promotion strategies, inventory validation, cart service logic, and all API endpoints.

---

## Accessing the App

| URL | Description |
|---|---|
| `http://localhost:8000` | Browser UI |
| `http://localhost:8000/docs` | Swagger UI (interactive API explorer) |
| `http://localhost:8000/redoc` | ReDoc API reference |

---

## API Reference

### Products

| Method | Endpoint | Description |
|---|---|---|
| GET | `/products` | List all products (optional `?category=dairy`) |
| GET | `/products/:id` | Get a single product |

**Examples:**
```bash
# All products
curl http://localhost:8000/products

# Filter by category
curl http://localhost:8000/products?category=dairy

# Single product
curl http://localhost:8000/products/p2
```

---

### Cart

| Method | Endpoint | Description |
|---|---|---|
| GET | `/cart` | Get current cart with promotions applied |
| POST | `/cart/items` | Add item to cart |
| PATCH | `/cart/items/:id` | Update quantity of a cart item |
| DELETE | `/cart/items/:id` | Remove a single item |
| DELETE | `/cart` | Clear the entire cart |
| POST | `/cart/items/:id/promotions` | Apply a specific promotion to a cart item |
| DELETE | `/cart/items/:id/promotions/:promo_id` | Remove a specific promotion from a cart item |

**Examples:**
```bash
# Get cart (promotions evaluated against now)
curl http://localhost:8000/cart

# Get cart with delivery time (promotions validated against delivery date)
curl "http://localhost:8000/cart?delivery_time=2026-06-01T10:00:00Z"

# Add item
curl -X POST http://localhost:8000/cart/items \
  -H "Content-Type: application/json" \
  -d '{"product_id": "p2", "quantity": 2}'

# Update quantity
curl -X PATCH http://localhost:8000/cart/items/1 \
  -H "Content-Type: application/json" \
  -d '{"quantity": 5}'

# Remove item
curl -X DELETE http://localhost:8000/cart/items/1

# Clear cart
curl -X DELETE http://localhost:8000/cart

# Apply a specific promotion to a cart item
curl -X POST http://localhost:8000/cart/items/1/promotions \
  -H "Content-Type: application/json" \
  -d '{"promotion_id": "promo_3"}'

# Remove a specific promotion from a cart item
curl -X DELETE http://localhost:8000/cart/items/1/promotions/promo_3
```

---

### Promotions

| Method | Endpoint | Description |
|---|---|---|
| GET | `/promotions` | List all promotions with active/expired/upcoming status |

```bash
curl http://localhost:8000/promotions
```

---

## Testing Key Scenarios

### 1. Promotion applied to cart item

```bash
# Add Whole Milk (has 20% dairy promo active today)
curl -X POST http://localhost:8000/cart/items \
  -H "Content-Type: application/json" \
  -d '{"product_id": "p2", "quantity": 2}'

# Check cart — should show applied_promotions[] and discounted line_total
curl http://localhost:8000/cart
```

### 2. Delivery-aware pricing (promo expires before delivery)

```bash
# Add Whole Milk first, then check cart with a future delivery date
# promo_1 (20% Off Dairy) expires 2026-05-28 — a June delivery should trigger a warning
curl "http://localhost:8000/cart?delivery_time=2026-06-01T10:00:00Z"
```

Expected: `warnings` array contains a message like:
> `promo_1 '20% Off Dairy' expires 2026-05-28, before delivery on 2026-06-01 — discount not applied`

### 3. Inventory validation (hard block)

```bash
# Salmon Fillet has inventory=18, request 99
curl -X POST http://localhost:8000/cart/items \
  -H "Content-Type: application/json" \
  -d '{"product_id": "p6", "quantity": 99}'
```

Expected: `400` with message:
> `Insufficient inventory for 'Salmon Fillet'. Requested: 99, Available: 18`

### 4. Invalid product

```bash
curl -X POST http://localhost:8000/cart/items \
  -H "Content-Type: application/json" \
  -d '{"product_id": "p99", "quantity": 1}'
```

Expected: `404` — `Product 'p99' not found`

### 5. Zero/negative quantity (validation error)

```bash
curl -X POST http://localhost:8000/cart/items \
  -H "Content-Type: application/json" \
  -d '{"product_id": "p2", "quantity": 0}'
```

Expected: `422` Unprocessable Entity

### 6. Multiple promotions — all stack automatically

By default all active eligible promotions are applied and stack. Each appears in `applied_promotions[]` with its individual discount. You can manually remove a specific promo or re-apply it:

```bash
# After adding an item, remove one promotion (switches item to manual mode)
curl -X DELETE http://localhost:8000/cart/items/1/promotions/promo_1

# Re-apply it
curl -X POST http://localhost:8000/cart/items/1/promotions \
  -H "Content-Type: application/json" \
  -d '{"promotion_id": "promo_1"}'

# GET /cart shows applied_promotions (applied) and eligible_promotions (available but not applied)
curl http://localhost:8000/cart
```

### 7. Expired promotion (no discount)

```bash
# Frozen Pizza (p7) — promo_2 ($2 Off Frozen) expired 2026-05-24
curl -X POST http://localhost:8000/cart/items \
  -H "Content-Type: application/json" \
  -d '{"product_id": "p7", "quantity": 1}'

curl http://localhost:8000/cart
# applied_promotions should be []
```

### 8. Inventory drop after item in cart (soft warning)

```bash
# Add item, then manually reduce inventory in SQLite, then re-fetch cart
sqlite3 cart.db "UPDATE products SET inventory = 1 WHERE id = 'p2';"

# Add 3 Whole Milk
curl -X POST http://localhost:8000/cart/items \
  -H "Content-Type: application/json" \
  -d '{"product_id": "p2", "quantity": 1}'

sqlite3 cart.db "UPDATE products SET inventory = 0 WHERE id = 'p2';"

curl http://localhost:8000/cart
# inventory_warnings should contain a message — item stays in cart
```

---

## Seed Data

### Products (20 items)

| ID | Name | Price | Inventory | Category |
|---|---|---|---|---|
| p1 | Organic Banana | $0.79 | 120 | produce |
| p2 | Whole Milk | $4.99 | 50 | dairy |
| p3 | Brown Eggs | $6.49 | 35 | dairy |
| p4 | Greek Yogurt | $5.99 | 25 | dairy |
| p5 | Chicken Breast | $12.99 | 40 | meat |
| p6 | Salmon Fillet | $18.99 | 18 | seafood |
| p7 | Frozen Pizza | $8.99 | 60 | frozen |
| p8 | Orange Juice | $5.49 | 22 | beverages |
| p9 | Sparkling Water | $7.99 | 80 | beverages |
| p10 | Coffee Beans | $15.99 | 28 | pantry |
| p11 | Pasta | $2.99 | 90 | pantry |
| p12 | Tomato Sauce | $3.49 | 75 | pantry |
| p13 | Avocado | $1.99 | 55 | produce |
| p14 | Blueberries | $4.49 | 30 | produce |
| p15 | Ice Cream | $6.99 | 20 | frozen |
| p16 | Ground Beef | $10.99 | 26 | meat |
| p17 | Cheddar Cheese | $7.49 | 32 | dairy |
| p18 | Protein Bar | $2.49 | 100 | snacks |
| p19 | Potato Chips | $4.99 | 70 | snacks |
| p20 | Almond Butter | $11.99 | 24 | pantry |

### Promotions (5 items)

| ID | Description | Type | Value | Start | End | Status (May 28) |
|---|---|---|---|---|---|---|
| promo_1 | 20% Off Dairy | PERCENTAGE | 20% | May 20 | May 28 | Expires today |
| promo_2 | $2 Off Frozen | FIXED | $2 | May 18 | May 24 | Expired |
| promo_3 | 10% Off Pantry | PERCENTAGE | 10% | May 21 | Jun 01 | Active |
| promo_4 | Buy More Save More | PERCENTAGE | 15% | May 15 | May 30 | Active |
| promo_5 | Weekend Produce Sale | PERCENTAGE | 25% | May 23 | May 26 | Expired |

Applies to: promo_1→p2,p3 | promo_2→p7,p15 | promo_3→p10,p11 | promo_4→p5,p16 | promo_5→p1,p14

---

## Assumptions & Tradeoffs

| Decision | Choice | Rationale |
|---|---|---|
| Cart identity | Single global cart (id=1) | No auth in scope; production would use per-user via JWT |
| Price at add time | Stored as `unit_price_at_add` | Cart stays stable if product price changes; promotions recalculate live |
| Inventory reservation | Advisory only — no lock | Avoids distributed lock complexity; noted as production gap |
| Multiple promotions | All eligible promos stack | Each active applicable promo contributes its discount |
| Promotion control | Manual apply/remove per item | User can opt out of specific promos; default is auto-apply all |
| Delivery time | Not stored — passed per request | Stateless; it's a query concern, not cart state |
| Fixed discount floor | Capped at item total | Prevents negative line prices |
| Inventory conflict | Soft warning, item remains | User decides whether to adjust quantity or check out anyway |
| Upsert on add | Adding existing product increments quantity | More intuitive than duplicate line items |
# ecom-cart
