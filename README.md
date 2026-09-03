# Restaurant Management System (Django + DRF)

A backend for restaurant operations: menu, orders, tables, reservations, and
inventory, with automatic stock deduction and basic reporting.

## Stack
- Django 6.1 (see `requirements.txt` for exact pins)
- Django REST Framework
- SQLite by default (Postgres-ready via `psycopg2-binary`, see below)

## Project layout
```
restaurant_system/   project settings & root urls
menu/                Category, MenuItem, MenuItemIngredient (recipe -> inventory link)
inventory/           InventoryItem, StockMovement (audit log)
tables/              DiningTable, Reservation
orders/              Order, OrderItem, order-processing logic (services.py)
reports/             daily sales / stock alert endpoints (no models of its own)
```

## Setup
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py createsuperuser     # for /admin/
python manage.py seed_demo_data      # optional: sample categories/items/tables
python manage.py runserver
```
Admin panel: http://127.0.0.1:8000/admin/

### Using Postgres instead of SQLite
Set these environment variables before running (the app falls back to SQLite
if `USE_POSTGRES` isn't set):
```
USE_POSTGRES=1
POSTGRES_DB=restaurant_system
POSTGRES_USER=postgres
POSTGRES_PASSWORD=...
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

## How the business logic works
- **Menu items** can list *recipe lines* (`MenuItemIngredient`) tying them to
  `InventoryItem`s with a quantity needed per serving.
- **Placing an order** (`orders/services.py: place_order`) checks the table is
  `AVAILABLE` for dine-in, checks every item has enough stock for every
  ingredient, then creates the order, deducts inventory (with a
  `StockMovement` audit row per ingredient), and marks the table `OCCUPIED`.
  All of this happens inside one DB transaction, so a failure anywhere rolls
  back cleanly and nothing is half-applied.
- **Completing/cancelling an order** frees the table again; cancelling
  restocks the inventory that was deducted.
- **Reservations** validate that the party fits the table and that the new
  time window doesn't overlap an existing reservation on the same table.

## API reference
All endpoints are under `/api/`. DRF's browsable API works too — open any
endpoint in a browser.

### Menu — `/api/menu/`
- `GET|POST /categories/`, `GET|PATCH|DELETE /categories/<id>/`
- `GET|POST /items/` (filters: `?available=true`, `?category=<id>`)
- `GET|PATCH|DELETE /items/<id>/`
- `GET|POST /recipe-lines/` — links a menu item to an inventory item + qty needed

### Inventory — `/api/inventory/`
- `GET|POST /items/`, `GET|PATCH|DELETE /items/<id>/`
- `GET /items/low-stock/` — items at/under their reorder level
- `POST /items/<id>/adjust-stock/` — body: `{"quantity": 5, "movement_type": "IN|OUT|ADJ", "reason": "..."}`
- `GET /movements/` — read-only audit log

### Tables & reservations — `/api/`
- `GET|POST /tables/`, `GET|PATCH|DELETE /tables/<id>/`
- `GET /tables/available/?party_size=4`
- `GET|POST /reservations/` — validates capacity + no double-booking
- `POST /reservations/<id>/seat/` `/complete/` `/cancel/`

### Orders — `/api/orders/`
- `GET /orders/` (filters: `?status=`, `?order_type=`)
- `POST /orders/` — body:
  ```json
  {
    "table": 1,
    "order_type": "DINE_IN",
    "customer_name": "Alice",
    "items": [{"menu_item": 3, "quantity": 2, "special_instructions": "no onions"}]
  }
  ```
- `POST /orders/<id>/add-item/` — same shape as one entry in `items`
- `POST /orders/<id>/set-status/` — body `{"status": "PREPARING|READY|SERVED|COMPLETED|CANCELLED"}`
- `POST /orders/<id>/complete/`, `POST /orders/<id>/cancel/` — shortcuts that also free/restock

### Reports — `/api/reports/`
- `GET /daily-sales/?date=YYYY-MM-DD` — order count, revenue, top-selling items
- `GET /sales-range/?start=YYYY-MM-DD&end=YYYY-MM-DD` — revenue per day
- `GET /stock-alerts/` — inventory items at/under reorder level

## Running the tests
34 automated tests cover model logic, the order-placement service layer, and
the API endpoints (order lifecycle, stock deduction/restocking, table
availability, reservation overlap/capacity checks, and reports):
```bash
python manage.py test
```
