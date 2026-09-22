# 🛍️ BuyYantra — Backend (ShopHub API)

**A production-grade, hybrid-auth e-commerce backend built with Django & Django REST Framework.**

Django REST API that powers the **BuyYantra** e-commerce platform — product catalogue, cart, checkout and order management — with a JWT-secured API for a React/mobile frontend, and a cookie-authenticated Django site for sellers to manage their own products.

<p align="left">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white">
  <img alt="Django" src="https://img.shields.io/badge/Django-6.0-092E20?logo=django&logoColor=white">
  <img alt="DRF" src="https://img.shields.io/badge/DRF-3.18-A30000">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white">
  <img alt="Redis" src="https://img.shields.io/badge/Redis-Celery-DC382D?logo=redis&logoColor=white">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-green">
</p>

<p align="left">
  🔗 <strong>Live API:</strong> <a href="https://api.systemizer.site/">api.systemizer.site</a>
  &nbsp;·&nbsp;
  🖥️ <strong>Live App:</strong> <a href="https://buyyantra.systemizer.site/">buyyantra.systemizer.site</a>
  &nbsp;·&nbsp;
  🎨 <strong>Frontend repo:</strong> <a href="https://github.com/Amanyadav72/BuyYantra_FrontStore">BuyYantra_FrontStore</a>
</p>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Related Repositories](#related-repositories)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

BuyYantra's backend is a **single-database, multi-tenant marketplace API**: any registered user can become a seller and list their own products, while every user can shop across the entire catalogue, maintain a cart, and check out into an order — all product data is scoped per-owner at the model level (`unique_product_per_owner`), so sellers only ever manage their own inventory.

It deliberately runs **two parallel auth systems**:

| Surface | Auth method | Who uses it |
|---|---|---|
| `/api/v1/*` (JSON API) | JWT (access + rotating refresh tokens via `djangorestframework-simplejwt`) | React / mobile frontend (`BuyYantra_FrontStore`) |
| `/`, `/my-products/`, `/admin/` (server-rendered) | Django session cookies | Sellers managing listings through server-rendered templates, and staff via Django Admin |

## Features

- 🔐 **Hybrid authentication** — stateless JWT for the API, session cookies for the seller/admin surface, backed by a shared Django user model.
- 🔑 **Full account lifecycle** — register, login, logout, refresh, change password, and email-based password reset (both as JSON endpoints and server-rendered views).
- 📍 **Address book** — multiple shipping addresses per user with a single enforced default (`one_default_address_per_user` DB constraint).
- 📦 **Product catalogue** — owner-scoped CRUD, draft/published status, category tagging, filtering by price range, stock range and category (`django-filter`), and search/pagination out of the box.
- 🛒 **Cart** — one cart per user, quantity-managed line items, unique product-per-cart constraint.
- 💳 **Checkout & orders** — atomic checkout (`select_for_update` to prevent overselling), stock decrement, order-number generation, itemised order history, and async order-confirmation emails via Celery.
- ⚙️ **Async task processing** — Redis-backed Celery workers for transactional emails and background jobs, with `task_acks_late` + `reject_on_worker_lost` for at-least-once delivery.
- ⚡ **Redis caching layer** for hot product/catalogue reads.
- ☁️ **Cloudflare R2** (S3-compatible) object storage for product images and avatars via `django-storages`.
- 📖 **Self-documenting API** — OpenAPI schema + interactive Swagger UI via `drf-spectacular`.
- 🚦 **Rate limiting** — DRF throttling (`500/day` anonymous, `2000/day` authenticated).
- 🧰 **Standardised error responses** via a custom DRF exception handler.
- 🌐 **CORS-ready** for a decoupled frontend, with credentialed cross-origin requests enabled.
- 🛡️ **Hardened for production** — HSTS, SSL redirect, secure cookies, and `debug_toolbar` auto-disabled outside `DEBUG`.

## Tech Stack

| Layer | Technology |
|---|---|
| Language / Framework | Python 3.12+, Django 6.0, Django REST Framework 3.18 |
| Auth | `djangorestframework-simplejwt` (JWT) + Django sessions |
| Database | PostgreSQL ([Neon](https://neon.tech), serverless) via `psycopg` 3 |
| Cache / Broker | Redis |
| Async tasks | Celery 5 |
| Object storage | Cloudflare R2 (S3-compatible) via `django-storages` + `boto3` |
| API docs | `drf-spectacular` (OpenAPI 3 + Swagger UI) |
| Filtering | `django-filter` |
| CORS | `django-cors-headers` |
| Web server | Gunicorn behind Nginx |
| Hosting | Oracle Cloud Infrastructure (OCI) VM, Ubuntu, HTTPS |

## Architecture

``` text
                    ┌──────────────────────────┐
                    │     React Frontend       │
                    │   BuyYantra Storefront   │
                    └────────────┬─────────────┘
                                 │ HTTPS / REST API
                                 │ JWT
                                 ▼
                    ┌──────────────────────────┐
                    │       Nginx              │
                    │ Reverse Proxy + HTTPS    │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Gunicorn                 │
                    │ Django Application       │
                    └──────┬─────┬─────┬──────┘
                           │     │     │
              ┌────────────┘     │     └───────────────┐
              ▼                  ▼                     ▼
       ┌─────────────┐    ┌─────────────┐      ┌─────────────┐
       │ Neon        │    │ Redis       │      │ Cloudflare  │
       │ PostgreSQL  │    │ Cache       │      │ R2 Media    │
       └─────────────┘    └──────┬──────┘      └─────────────┘
                                  │
                                  ▼
                           ┌─────────────┐
                           │ Celery      │
                           │ Workers     │
                           └─────────────┘
```

## Project Structure

```
BuyYantra_BackStore/
├── accounts/                # Custom auth: register/login/logout, JWT, addresses, profile
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   ├── models.py             # CustomerProfile, Address
│   ├── serializers.py
│   ├── signals.py
│   ├── tasks.py               # Celery tasks (e.g. password-reset emails)
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── cart/                    # Cart & CartItem models, services, API views
│   ├── apps.py
│   ├── migrations/
│   ├── models.py              # Cart, CartItem
│   ├── serializers.py
│   ├── services.py
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── orders/                  # Order/OrderItem models, checkout service, Celery tasks
│   ├── apps.py
│   ├── migrations/
│   ├── models.py              # Order, OrderItem
│   ├── serializers.py
│   ├── services.py             # Atomic checkout() logic
│   ├── signals.py
│   ├── tasks.py                # send_order_confirmation_email, etc.
│   ├── tests.py
│   ├── urls.py
│   └── views.py
├── products/                 # Product catalogue, categories, seller-facing CRUD templates
│   ├── api/                   # DRF ViewSet, serializers, permissions for the product API
│   ├── admin.py
│   ├── apps.py
│   ├── cache.py                # Redis caching helpers for catalogue reads
│   ├── exceptions.py           # Custom DRF exception handler
│   ├── filters.py               # django-filter: price/stock range, category
│   ├── forms.py
│   ├── management/             # Custom management commands
│   ├── migrations/
│   ├── models.py                # Category, Product, SellerProfile
│   ├── pagination.py
│   ├── signals.py
│   ├── static/                  # Static assets for the seller-facing templates
│   ├── templates/               # Server-rendered HTML (catalogue, seller CRUD, auth)
│   ├── tests.py
│   ├── urls.py                  # Server-rendered views (/, /my-products/, auth, etc.)
│   └── views.py
├── shophub/                  # Django project: settings, root urls, celery app, wsgi/asgi
│   ├── asgi.py
│   ├── celery.py
│   ├── middleware.py           # RequestTimingMiddleware
│   ├── settings.py
│   ├── urls.py                  # Root URLConf — mounts every app + API docs
│   └── wsgi.py
├── .env.example               # Documented environment variable template
├── .gitignore
├── manage.py
└── requirements.txt
```

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL (or a [Neon](https://neon.tech) connection string)
- Redis (for caching and as the Celery broker/result backend)

### 1. Clone & set up a virtual environment

```bash
git clone https://github.com/Amanyadav72/BuyYantra_BackStore.git
cd BuyYantra_BackStore

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Fill in `.env` with your own values — see [Environment Variables](#environment-variables) below. For local development you can set `DJANGO_DEBUG=true`, which relaxes several production-only checks.

### 3. Apply migrations & create a superuser

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run the app

```bash
# Django dev server
python manage.py runserver

# In separate terminals — Celery worker (needs Redis running)
celery -A shophub worker -l info

# Optional — Celery beat, if/when scheduled tasks are added
celery -A shophub beat -l info
```

The API is now available at `http://127.0.0.1:8000/api/v1/`, the seller-facing site at `http://127.0.0.1:8000/`, and interactive API docs at `http://127.0.0.1:8000/api/docs/`.

> The production equivalents are live at **[api.systemizer.site](https://api.systemizer.site/)** (backend) and **[buyyantra.systemizer.site](https://buyyantra.systemizer.site/)** (frontend).

## Environment Variables

All variables are documented in [`.env.example`](.env.example). None are hard-coded — `DJANGO_SECRET_KEY` and the database/Redis credentials are **required** whenever `DJANGO_DEBUG=false`.

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django cryptographic signing key |
| `DJANGO_DEBUG` | `true`/`false` — toggles debug mode, debug toolbar, and production security headers |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames allowed to serve the app |
| `CORS_ALLOWED_ORIGINS` | Comma-separated origins allowed to call the API with credentials |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL connection |
| `DB_CONN_MAX_AGE`, `DB_CONNECT_TIMEOUT` | Connection pooling/timeout tuning |
| `REDIS_URL` | Redis instance used for Django's cache backend |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Redis DBs used by Celery |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP credentials (Gmail) for transactional email |
| `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ACCOUNT_ID`, `R2_ENDPOINT_URL` | Cloudflare R2 credentials for media storage |

> **Never commit your real `.env` file.** It's already covered by `.gitignore` — only `.env.example` should be tracked.

## API Reference

Full interactive documentation (Swagger UI) is served at **`/api/docs/`**, with the raw OpenAPI schema at **`/api/schema/`**. All JSON endpoints are namespaced under `/api/v1/`.

<details>
<summary><strong>Auth &amp; Accounts</strong> — <code>/api/v1/auth/*</code>, <code>/api/v1/profile/</code>, <code>/api/v1/addresses/*</code></summary>

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register/` | Create a new account |
| POST | `/auth/login/` | Obtain JWT access + refresh tokens |
| POST | `/auth/logout/` | Blacklist the refresh token |
| POST | `/token/refresh/` | Exchange a refresh token for a new access token |
| GET | `/auth/me/` | Current authenticated user |
| POST | `/auth/password/change/` | Change password (authenticated) |
| POST | `/auth/password/reset/` | Request a password-reset email |
| POST | `/auth/password/reset/confirm/` | Confirm a password reset |
| GET/PUT | `/profile/` | Retrieve/update the customer profile |
| GET/POST/PUT/DELETE | `/addresses/` | Full CRUD on the address book |

</details>

<details>
<summary><strong>Products</strong> — <code>/api/v1/products/*</code></summary>

| Method | Endpoint | Description |
|---|---|---|
| GET | `/products/` | List published products — supports `?categories=`, `?min_price=`, `?max_price=`, `?min_stock=`, `?max_stock=` |
| GET | `/products/{id}/` | Retrieve a single product |
| POST | `/products/` | Create a product (owner = requesting user) |
| PUT/PATCH | `/products/{id}/` | Update your own product |
| DELETE | `/products/{id}/` | Delete your own product |

</details>

<details>
<summary><strong>Cart</strong> — <code>/api/v1/cart/*</code></summary>

| Method | Endpoint | Description |
|---|---|---|
| GET | `/cart/` | View your current cart |
| GET/POST | `/cart/items/` | List / add cart items |
| PUT/DELETE | `/cart/items/{id}/` | Update quantity / remove a cart item |

</details>

<details>
<summary><strong>Orders</strong> — <code>/api/v1/orders/*</code></summary>

| Method | Endpoint | Description |
|---|---|---|
| POST | `/orders/checkout/` | Convert the current cart into an order (atomic, stock-checked) |
| GET | `/orders/` | List the authenticated user's orders |
| GET | `/orders/{number}/` | Retrieve a single order by its order number |

</details>

<details>
<summary><strong>Seller-facing site (session auth, server-rendered)</strong> — <code>/</code></summary>

Includes the public catalogue, `/my-products/` CRUD for sellers, `/register/`, `/login/`, `/logout/`, `/change-password/`, `/profile/` and the full Django password-reset flow — all outside the `/api/v1/` namespace.

</details>

## Deployment

The reference deployment runs on an **Oracle Cloud Infrastructure (OCI)** Ubuntu VM:

- **Nginx** as the reverse proxy and TLS terminator (HTTPS)
- **Gunicorn** as the WSGI application server
- **PostgreSQL** hosted on [Neon](https://neon.tech) (serverless Postgres)
- **Media storage** on **Cloudflare R2** (S3-compatible, zero egress fees)
- **Redis** for caching and as the Celery broker, with a Celery worker process running alongside Gunicorn
- `DJANGO_DEBUG=false` in production, with `SECURE_SSL_REDIRECT`, HSTS, and secure cookies all enforced automatically

## Related Repositories

| | |
|---|---|
| 🎨 **Frontend repo** | [`Amanyadav72/BuyYantra_FrontStore`](https://github.com/Amanyadav72/BuyYantra_FrontStore) — the client application that consumes this API |
| 🖥️ **Frontend (live)** | [buyyantra.systemizer.site](https://buyyantra.systemizer.site/) |
| 🔗 **Backend API (live)** | [api.systemizer.site](https://api.systemizer.site/) |
| 📖 **API docs (Swagger)** | [api.systemizer.site/api/docs/](https://api.systemizer.site/api/docs/) |

## Roadmap

- [ ] Payment gateway integration
- [ ] Order tracking / shipment status webhooks
- [ ] Product reviews & ratings
- [ ] Wishlist
- [ ] Automated CI (tests + lint) via GitHub Actions

## Contributing

Contributions, issues and feature requests are welcome.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m "Add your feature"`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

<p align="center">Built with Django & DRF by <a href="https://github.com/Amanyadav72">Amanyadav72</a></p>
