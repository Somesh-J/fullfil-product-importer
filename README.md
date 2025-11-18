# FullFil-Product Importer - Full-Stack CSV Import System

> **Backend Engineer Assessment Project**  
> A production-ready web application for importing and managing large CSV product catalogs with real-time progress tracking, webhooks, and async processing.

---

## 📋 Project Overview

This application solves the challenge of importing **large CSV files (500,000+ rows)** without HTTP timeout issues by leveraging asynchronous task processing with Celery and Redis. It provides:

- **CSV Upload & Import**: Upload product catalogs via drag-and-drop interface
- **Real-time Progress**: Live Server-Sent Events (SSE) streaming of import progress
- **Product Management**: Full CRUD operations with pagination, filtering, and search
- **Bulk Operations**: Delete all products asynchronously without timeout
- **Webhook System**: Configurable webhooks for product lifecycle events
- **Production-Ready**: Docker deployment with PostgreSQL, Redis, and Celery workers

---

## ✨ Features

- ✅ **Async CSV Processing**: Handle files with 500k+ rows without blocking HTTP requests
- ✅ **Real-time Updates**: SSE-powered progress bar showing live import status
- ✅ **Smart Upserts**: Case-insensitive SKU deduplication with batch inserts
- ✅ **Advanced Filtering**: Search products by name/description, filter by SKU and active status
- ✅ **Webhook Events**: Trigger HTTP callbacks on product.created, product.updated, import.completed
- ✅ **Bulk Delete**: Truncate entire product catalog without timeout
- ✅ **Responsive UI**: Single-page vanilla JavaScript interface with drag-and-drop
- ✅ **Docker Ready**: Complete docker-compose setup for local development
- ✅ **Database Migrations**: Alembic-managed schema versioning
- ✅ **API Documentation**: Auto-generated Swagger/ReDoc at `/docs` and `/redoc`

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI 0.104.1 (Python 3.11) |
| **Database** | PostgreSQL 15 with asyncpg driver |
| **ORM** | SQLAlchemy 2.0 (async mode) |
| **Migrations** | Alembic 1.12.1 |
| **Task Queue** | Celery 5.3.4 |
| **Message Broker** | Redis 7 (Celery + SSE pub/sub) |
| **Frontend** | Vanilla JavaScript, HTML5, CSS3 |
| **Deployment** | Docker + Docker Compose, Railway.app |
| **Validation** | Pydantic 2.5.0 |

---

## 🚀 Local Setup (Docker Compose)

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Git

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd fullfil

# Create environment file
cp .env.example .env

# Build and start all services
docker-compose up --build
```

The application will be available at:
- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Running Database Migrations

```bash
# Inside Docker container
docker-compose exec web alembic upgrade head

# Or locally (if running outside Docker)
alembic upgrade head
```

### Stopping Services

```bash
# Stop containers
docker-compose down

# Stop and remove volumes (⚠️ deletes database)
docker-compose down -v
```

---

## 📡 API Quick Reference

### Complete API Summary

| Category | Method | Endpoint | Description | Key Features |
|----------|--------|----------|-------------|--------------|
| **Upload** | POST | `/api/upload` | Upload CSV file | Returns job_id, 202 Accepted |
| **Progress** | GET | `/api/progress/{job_id}` | SSE progress stream | Real-time updates via Redis |
| **Jobs** | GET | `/api/jobs/{job_id}` | Get job status | Polling alternative to SSE |
| **Jobs** | POST | `/api/jobs/{job_id}/cancel` | Cancel import | Stops processing gracefully |
| **Products** | GET | `/api/products` | List products | Pagination, filtering, search |
| **Products** | POST | `/api/products` | Create product | Validates SKU uniqueness |
| **Products** | GET | `/api/products/{id}` | Get product | Single product details |
| **Products** | PUT | `/api/products/{id}` | Update product | Case-insensitive SKU check |
| **Products** | DELETE | `/api/products/{id}` | Delete product | Soft delete option |
| **Products** | DELETE | `/api/products/bulk` | Delete all products | Async, returns job_id |
| **Webhooks** | GET | `/api/webhooks` | List webhooks | All webhook configurations |
| **Webhooks** | POST | `/api/webhooks` | Create webhook | Event types, URL validation |
| **Webhooks** | GET | `/api/webhooks/{id}` | Get webhook | Single webhook details |
| **Webhooks** | PUT | `/api/webhooks/{id}` | Update webhook | Modify URL, events, status |
| **Webhooks** | DELETE | `/api/webhooks/{id}` | Delete webhook | Cascades to logs |
| **Webhooks** | POST | `/api/webhooks/{id}/test` | Test webhook | Sends sample payload |
| **Webhooks** | GET | `/api/webhooks/{id}/logs` | View logs | Delivery history, stats |

**Full API Documentation:**
- 📖 Interactive Swagger UI: `http://localhost:8000/docs`
- 📘 ReDoc Documentation: `http://localhost:8000/redoc`
- 📄 Detailed Reference: See [`Docs/API_REFERENCE.md`](Docs/API_REFERENCE.md)

---

## 🏗️ Architecture

The system follows a **distributed task queue architecture**:

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Browser   │─────▶│  FastAPI Web │─────▶│  PostgreSQL │
│  (UI/SSE)   │◀─────│   (Port 8000)│      │   Database  │
└─────────────┘      └──────────────┘      └─────────────┘
                            │                       ▲
                            ▼                       │
                     ┌─────────────┐               │
                     │    Redis    │               │
                     │  (Pub/Sub)  │               │
                     └─────────────┘               │
                            │                       │
                            ▼                       │
                     ┌─────────────┐               │
                     │   Celery    │───────────────┘
                     │   Worker    │
                     └─────────────┘
```

**Flow**:
1. User uploads CSV via FastAPI `/api/upload` endpoint
2. FastAPI saves file to disk and enqueues Celery task
3. Celery worker processes CSV in batches (1000 rows), publishes progress to Redis
4. Browser opens SSE connection to `/api/progress/{job_id}`, receives real-time updates
5. Products are upserted into PostgreSQL with case-insensitive SKU deduplication

See `ARCHITECTURE.md` for detailed design documentation.

---

## 📡 API Endpoints

### CSV Upload & Progress

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Upload CSV file and trigger import |
| `GET` | `/api/progress/{job_id}` | SSE stream of real-time import progress |
| `GET` | `/api/jobs/{job_id}` | Get import job status (polling alternative) |

### Products

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/products` | List products (pagination, filters: `q`, `sku`, `active`) |
| `POST` | `/api/products` | Create new product |
| `GET` | `/api/products/{id}` | Get single product by ID |
| `PUT` | `/api/products/{id}` | Update product |
| `DELETE` | `/api/products/{id}` | Delete product |
| `POST` | `/api/products/bulk-delete` | Delete all products (async) |

### Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/webhooks` | List all webhooks |
| `POST` | `/api/webhooks` | Create webhook |
| `GET` | `/api/webhooks/{id}` | Get webhook details |
| `PUT` | `/api/webhooks/{id}` | Update webhook |
| `DELETE` | `/api/webhooks/{id}` | Delete webhook |
| `POST` | `/api/webhooks/{id}/test` | Send test event to webhook |
| `GET` | `/api/webhooks/{id}/logs` | View delivery history |

---

## 📂 Project Structure

```
fullfil/
├── alembic/
│   ├── versions/
│   │   └── 20251118_0100_initial_create_tables.py
│   └── env.py
├── app/
│   ├── routers/
│   │   ├── upload.py      # CSV upload + SSE endpoints
│   │   ├── products.py    # Product CRUD
│   │   └── webhooks.py    # Webhook management
│   ├── celery_app.py      # Celery configuration
│   ├── db.py              # Database sessions
│   ├── main.py            # FastAPI app
│   ├── models.py          # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   ├── tasks.py           # Celery tasks
│   └── utils.py           # Utility functions
├── static/
│   └── index.html         # Single-page UI
├── uploads/               # CSV file storage
├── .env.example           # Environment template
├── alembic.ini            # Alembic config
├── docker-compose.yml     # Local dev stack
├── Dockerfile             # Container image
├── requirements.txt       # Python dependencies
├── ARCHITECTURE.md        # Design documentation
└── README.md
```

---

## 🔧 Development

### Adding New Migrations

```bash
# Auto-generate migration from model changes
docker-compose exec web alembic revision --autogenerate -m "description"

# Apply migration
docker-compose exec web alembic upgrade head
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f worker
```

### Accessing Services

```bash
# PostgreSQL
docker-compose exec db psql -U fullfil -d fullfil

# Redis CLI
docker-compose exec redis redis-cli

# Web service shell
docker-compose exec web bash
```

---

## 📚 Documentation

This project includes comprehensive documentation:

| Document | Description | Link |
|----------|-------------|------|
| **README.md** | Quick start guide, setup instructions | You are here |
| **Architecture** | System design, data models, tech stack | [`Docs/ARCHITECTURE.md`](Docs/ARCHITECTURE.md) |
| **API Reference** | Complete API documentation with examples | [`Docs/API_REFERENCE.md`](Docs/API_REFERENCE.md) |
| **Project Completion** | Task checklist, requirements verification | [`Docs/PROJECT_COMPLETION.md`](Docs/PROJECT_COMPLETION.md) |
| **AI Prompts** | Complete log of all AI interactions | [`Docs/AI_PROMPTS.md`](Docs/AI_PROMPTS.md) |
| **Interactive API Docs** | Swagger UI for testing | `http://localhost:8000/docs` |
| **ReDoc API Docs** | Alternative API documentation | `http://localhost:8000/redoc` |

---

## ✅ Project Status

**Status:** ✅ **Production Ready**

### Features Implemented

- ✅ CSV Upload (drag-and-drop, up to 500MB)
- ✅ Real-time Progress Tracking (SSE with Redis pub/sub)
- ✅ Async Import Processing (Celery workers, no timeout)
- ✅ Product CRUD (create, read, update, delete)
- ✅ Advanced Filtering (SKU prefix, name/description search, active status)
- ✅ Pagination (configurable page size, 1-100)
- ✅ Bulk Operations (delete all, delete selected)
- ✅ Cancel Import (stop running jobs)
- ✅ Webhook Management (CRUD, testing, delivery logs)
- ✅ Case-insensitive SKU uniqueness
- ✅ Professional UI (modern, responsive design)
- ✅ Error Handling (user-friendly messages)
- ✅ Docker Support (local development)
- ✅ Deployment Ready (Railway.app configuration)

### Performance

- ⚡ Import speed: ~4,000 rows/second
- ⚡ 500,000 rows in ~2 minutes
- ⚡ Memory efficient: Streaming processing
- ⚡ No HTTP timeout issues (async processing)
