# Django Microservices: Book Shop + Warehouse

Two separate Django services communicating via REST API.

```
┌─────────────────────────────────────────────────────────────────┐
│                          NGINX :80                              │
│   /           →  ProjectA: Book Shop   (book_shop_web:8000)    │
│   /warehouse/ →  ProjectB: Warehouse   (warehouse_web:8001)    │
└──────────┬──────────────────────────┬───────────────────────────┘
           │                          │
   ┌───────▼────────┐        ┌────────▼────────┐
   │  ProjectA      │        │  ProjectB       │
   │  Book Shop     │◄──────►│  Warehouse      │
   │  :8000         │  HTTP  │  :8001          │
   │                │  API   │                 │
   │ PostgreSQL DB1 │        │ PostgreSQL DB2  │
   │ Celery Worker  │        │ Celery Worker   │
   │ Celery Beat    │        │ Celery Beat     │
   └───────┬────────┘        └────────┬────────┘
           │                          │
           └──────────┬───────────────┘
                ┌─────▼─────┐
                │  Redis    │
                │  DB0 / DB1│
                └───────────┘
```

## Inter-Service Communication

| Direction | Trigger | Endpoint |
|-----------|---------|----------|
| ProjectA → ProjectB | Order created | `POST /api/stock/by-book/{id}/reserve/` |
| ProjectA → ProjectB | Order cancelled | `POST /api/stock/by-book/{id}/release/` |
| ProjectA → ProjectB | Book catalog sync (nightly) | `POST /api/stock/sync/` |
| ProjectB → ProjectA | Low/out-of-stock alert | `POST /api/webhooks/stock-alert/` |

Auth: `X-Warehouse-Secret` shared-secret header for service-to-service calls.
Error handling: graceful degradation — checkout proceeds even if Warehouse is unreachable.

---

## ProjectA — Book Shop

| Feature | Details |
|---------|---------|
| Stack | Django 5, DRF, PostgreSQL, Redis, Celery, Gunicorn |
| Auth | JWT (`/api/auth/token/`) |
| API | `/api/` — Books, Categories, Orders, Cart ViewSets |
| Webhooks | `POST /api/webhooks/stock-alert/` |
| Tasks | Order email, daily sales report, catalog sync |
| i18n | uk (default), en |
| Tests | 218 tests, 91%+ coverage |
| Docs | `/api/docs/` (Swagger) |

## ProjectB — Warehouse Management

| Feature | Details |
|---------|---------|
| Stack | Django 5, DRF, PostgreSQL, Redis, Celery, Gunicorn |
| Auth | JWT (`/api/auth/token/`) |
| Models | `StockItem`, `StockMovement`, `WarehouseAlert`, `WeeklyStockReport` |
| API | `/api/stock/`, `/api/movements/`, `/api/alerts/`, `/api/analytics/` |
| Custom actions | `reserve/`, `release/`, `adjust/`, `sync/` |
| Tasks | Low-stock check, weekly report, catalog sync from ProjectA |
| UI | Bootstrap 5 dashboard (stock list, detail, alerts, analytics) |
| i18n | uk (default), en |
| Tests | 78 tests, 92%+ coverage |
| Docs | `/api/docs/` (Swagger) |

---

## Quick Start

### 1. Clone and configure

```bash
git clone <repo>
cd Django

# Copy env templates
cp .env.example .env
cp book_shop/.env.example book_shop/.env
cp warehouse/.env.example warehouse/.env

# Edit both .env files with your secrets
```

### 2. Run everything with Docker Compose

```bash
# Build and start all services
docker-compose up --build

# Access services
# Book Shop:   http://localhost/
# Warehouse:   http://localhost/warehouse/
# Book Shop API docs: http://localhost/api/docs/
# Warehouse API docs: http://localhost/warehouse/api/docs/
```

### 3. Run services individually (development)

**ProjectA:**
```bash
cd book_shop
python -m venv venv && source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements-dev.txt
cp .env.example .env  # edit as needed
python manage.py migrate
python manage.py runserver
# In another terminal:
celery -A book_shop worker -l info
```

**ProjectB:**
```bash
cd warehouse
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 8001
# In another terminal:
celery -A warehouse worker -l info
```

---

## Running Tests

```bash
# ProjectA (from book_shop/)
python -m pytest tests/ --cov=books --cov=orders --cov=accounts -v

# ProjectB (from warehouse/)
python -m pytest tests/ --cov=inventory --cov=analytics --cov=accounts -v
```

---

## API Documentation

Both services expose interactive Swagger UI:

- **ProjectA**: `http://localhost/api/docs/`
- **ProjectB**: `http://localhost/warehouse/api/docs/`

---

## Key Environment Variables

### ProjectA (`book_shop/.env`)

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DB_NAME/USER/PASSWORD/HOST` | PostgreSQL |
| `REDIS_URL` | Redis URL (db 0) |
| `WAREHOUSE_API_URL` | URL of ProjectB (e.g. `http://warehouse_web:8001`) |
| `WAREHOUSE_WEBHOOK_SECRET` | Shared secret for inter-service calls |
| `STRIPE_*` | Stripe payment keys |

### ProjectB (`warehouse/.env`)

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DB_NAME/USER/PASSWORD/HOST` | PostgreSQL |
| `REDIS_URL` | Redis URL (db 1) |
| `BOOK_SHOP_API_URL` | URL of ProjectA |
| `WEBHOOK_SECRET` | Shared secret for inter-service calls |

---

## CI/CD

- **ProjectA**: `.github/workflows/django.yml` — lint → test → Docker push
- **ProjectB**: `warehouse/.github/workflows/warehouse.yml` — lint → test → Docker push

Required GitHub secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `CODECOV_TOKEN`

---

## Project Structure

```
Django/
├── docker-compose.yml          # Orchestrates all services
├── nginx/nginx.conf            # Shared NGINX config
├── .env.example                # Root env template
│
├── book_shop/                  # ProjectA
│   ├── accounts/               # CustomUser (bio, phone)
│   ├── books/                  # Book, Category models + CBVs
│   ├── orders/                 # Order, Cart (session), Stripe
│   ├── api/                    # DRF ViewSets + webhooks
│   ├── services/
│   │   └── warehouse_client.py # HTTP client for ProjectB
│   ├── book_shop/settings/     # base / dev / prod / test
│   └── tests/                  # 218 tests
│
└── warehouse/                  # ProjectB
    ├── accounts/               # CustomUser (role, department)
    ├── inventory/              # StockItem, StockMovement, Alert
    ├── analytics/              # WeeklyStockReport + dashboard
    ├── services/
    │   └── book_shop_client.py # HTTP client for ProjectA
    ├── warehouse/settings/     # base / dev / prod / test
    └── tests/                  # 78 tests
```
