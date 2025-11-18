# Product Importer - Architecture Document

**Project:** Acme Inc. Product Importer  
**Date:** November 18, 2025  
**Tech Stack:** FastAPI + Celery + Redis + PostgreSQL + SQLAlchemy

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Data Model](#data-model)
4. [Component Design](#component-design)
5. [API Endpoints](#api-endpoints)
6. [Asynchronous Processing](#asynchronous-processing)
7. [Real-Time Progress Updates](#real-time-progress-updates)
8. [Deployment Architecture](#deployment-architecture)
9. [Security Considerations](#security-considerations)
10. [Performance Optimization](#performance-optimization)

---

## 1. Executive Summary

### 1.1 Project Goals
Build a scalable web application capable of:
- Importing **500,000+ products** from CSV without timeout
- Providing **real-time progress** feedback to users
- Managing products via a **simple web UI**
- Configuring and testing **webhooks**
- Handling **long-running operations** asynchronously

### 1.2 Key Requirements
- ✅ Upload large CSV files (products.csv)
- ✅ Real-time progress tracking (SSE-based)
- ✅ Product CRUD with pagination & filtering
- ✅ Bulk delete with confirmation
- ✅ Webhook management & testing
- ✅ Case-insensitive SKU uniqueness
- ✅ Public deployment (no timeout issues)

### 1.3 CSV Schema
**File:** `products.csv`

| Column | Type | Description |
|--------|------|-------------|
| name | string | Product name |
| sku | string | Stock Keeping Unit (unique, case-insensitive) |
| description | text | Product description |

**Additional Database Fields:**
- `price` (decimal) - Product price (can be in CSV or added later)
- `active` (boolean) - Not in CSV, defaults to `true`
- `id` (integer) - Auto-generated primary key
- `created_at` (timestamp) - Auto-generated
- `updated_at` (timestamp) - Auto-updated

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT BROWSER                          │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐   │
│  │   HTML UI   │  │  JavaScript  │  │  SSE Event Stream   │   │
│  └─────────────┘  └──────────────┘  └─────────────────────┘   │
└────────┬──────────────────┬────────────────────┬───────────────┘
         │                  │                    │
         │ HTTP/REST        │ HTTP/REST          │ SSE Connection
         ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI APPLICATION                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │   REST API   │  │  Static Files│  │  SSE Endpoint    │     │
│  │   Endpoints  │  │   (UI)       │  │  /api/progress   │     │
│  └──────┬───────┘  └──────────────┘  └────────┬─────────┘     │
│         │                                      │                │
│         │ Enqueue Task                         │ Subscribe      │
│         ▼                                      ▼                │
│  ┌─────────────────────┐              ┌──────────────────┐     │
│  │   Celery Client     │              │   Redis Pub/Sub  │     │
│  └──────┬──────────────┘              └──────────────────┘     │
└─────────┼──────────────────────────────────────────────────────┘
          │
          │ Task Queue
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                       REDIS BROKER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │ Task Queue   │  │ Result Store │  │  Pub/Sub Channel │     │
│  └──────────────┘  └──────────────┘  └──────────────────┘     │
└────────┬────────────────────────────────────────────────────────┘
         │
         │ Consume Tasks
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CELERY WORKER(S)                           │
│  ┌──────────────────────────────────────────────────────┐      │
│  │  CSV Processing Task:                                │      │
│  │  1. Stream CSV file                                  │      │
│  │  2. Parse & validate rows                            │      │
│  │  3. Batch insert (1000 records/batch)                │      │
│  │  4. Publish progress to Redis                        │      │
│  │  5. Trigger webhooks on events                       │      │
│  └────────────────┬─────────────────────────────────────┘      │
│                   │                                             │
│  ┌────────────────▼─────────────────────────────────────┐      │
│  │  Webhook Task:                                       │      │
│  │  1. Retrieve webhook configurations                  │      │
│  │  2. Send HTTP POST with event payload                │      │
│  │  3. Log response status & time                       │      │
│  └──────────────────────────────────────────────────────┘      │
└────────┬────────────────────────────────────────────────────────┘
         │
         │ Database Operations
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    POSTGRESQL DATABASE                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐     │
│  │   Products   │  │   Webhooks   │  │  Webhook Logs    │     │
│  │   Table      │  │   Table      │  │  Table           │     │
│  └──────────────┘  └──────────────┘  └──────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Web Framework** | FastAPI | Async REST API, auto-documentation, high performance |
| **Task Queue** | Celery | Asynchronous background job processing |
| **Message Broker** | Redis | Task queue, result backend, pub/sub for SSE |
| **Database** | PostgreSQL | Relational data storage, ACID compliance |
| **ORM** | SQLAlchemy (Async) | Async database abstraction, migrations, relationships |
| **Migrations** | Alembic | Database schema version control |
| **Frontend** | HTML/CSS/JS | Minimal UI with modern features (no React) |
| **Real-time** | Server-Sent Events (SSE) | Live progress updates via Redis pub/sub |
| **Containerization** | Docker + Docker Compose | Local development environment |
| **Deployment** | Render.com | Managed web + worker + PostgreSQL + Redis |

---

## 3. Data Model

### 3.1 Database Schema

#### **Products Table**
```sql
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    sku VARCHAR(255) NOT NULL,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Case-insensitive unique constraint on SKU
CREATE UNIQUE INDEX idx_products_sku_lower ON products (LOWER(sku));

-- Indexes for filtering
CREATE INDEX idx_products_active ON products (active);
CREATE INDEX idx_products_name ON products (name);
CREATE INDEX idx_products_created_at ON products (created_at DESC);
```

#### **Webhooks Table**
```sql
CREATE TABLE webhooks (
    id SERIAL PRIMARY KEY,
    url VARCHAR(1000) NOT NULL,
    event_type VARCHAR(100) NOT NULL,  -- product.created, product.updated, product.deleted
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_webhooks_event_type ON webhooks (event_type);
CREATE INDEX idx_webhooks_enabled ON webhooks (enabled);
```

#### **Webhook Logs Table**
```sql
CREATE TABLE webhook_logs (
    id SERIAL PRIMARY KEY,
    webhook_id INTEGER REFERENCES webhooks(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB,
    response_status INTEGER,
    response_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_webhook_logs_webhook_id ON webhook_logs (webhook_id);
CREATE INDEX idx_webhook_logs_created_at ON webhook_logs (created_at DESC);
```

### 3.2 SQLAlchemy Models

```python
# models.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(255), nullable=False)
    name = Column(String(500), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2))
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_products_sku_lower', func.lower(sku), unique=True),
    )

class Webhook(Base):
    __tablename__ = "webhooks"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(1000), nullable=False)
    event_type = Column(String(100), nullable=False, index=True)  # product.created, product.updated, product.deleted
    enabled = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    logs = relationship("WebhookLog", back_populates="webhook", cascade="all, delete-orphan", lazy="selectin")

class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("webhooks.id", ondelete="CASCADE"))
    event_type = Column(String(100), nullable=False)
    payload = Column(JSONB)
    response_status = Column(Integer)
    response_time_ms = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    webhook = relationship("Webhook", back_populates="logs")
```

---

## 4. Component Design

### 4.1 Project Structure

```
fullfil/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── db.py                   # Database connection & async session
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic schemas (request/response)
│   ├── celery_app.py           # Celery configuration
│   ├── tasks.py                # Celery tasks (CSV import, webhooks, bulk delete)
│   ├── utils.py                # Utility functions (CSV processor, Redis pub/sub)
│   │
│   └── routers/
│       ├── __init__.py
│       ├── products.py         # Product CRUD endpoints
│       ├── upload.py           # CSV upload + SSE progress endpoint
│       └── webhooks.py         # Webhook CRUD + test endpoints
│
├── static/
│   └── index.html              # Complete UI (HTML + CSS + JS inline)
│
├── alembic/                    # Alembic migrations
│   ├── env.py
│   └── versions/
│
├── tests/
│   ├── test_products.py
│   ├── test_webhooks.py
│   └── test_csv_import.py
│
├── products.csv                # Sample CSV file (500k rows)
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── docker-compose.yml          # Local development setup
├── render.yaml                 # Render deployment config
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore file
├── README.md                   # Project documentation
└── ARCHITECTURE.md             # This document
```

### 4.2 Key Components

#### **FastAPI Application (`app/main.py`)**
- Serves REST API endpoints
- Hosts static files for UI (`/static/index.html`)
- Handles SSE connections for real-time progress
- CORS configuration
- Exception handling
- Async SQLAlchemy session dependency

#### **Database Module (`app/db.py`)**
- Async SQLAlchemy engine & session factory
- PostgreSQL connection with asyncpg driver
- Database session dependency for FastAPI
- Base declarative class for models

#### **Celery Worker (`app/celery_app.py` + `app/tasks.py`)**
- Celery configuration with Redis broker
- CSV import task with batch processing
- Bulk delete task
- Webhook notification tasks
- Redis pub/sub for progress updates

#### **Utility Functions (`app/utils.py`)**
- CSV streaming & parsing (memory-efficient)
- Batch upsert with case-insensitive SKU handling
- Redis pub/sub progress publisher
- Webhook HTTP client with timeout & logging

#### **Routers (`app/routers/`)**
- `products.py` - CRUD with pagination & filtering
- `upload.py` - CSV upload + SSE progress stream
- `webhooks.py` - CRUD + test endpoint

---

## 5. API Endpoints

### 5.1 Product Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/api/products` | List products (paginated) | `?page=1&limit=50&search=&active=true` | `{ items: [], total: 500000, page: 1, pages: 10000 }` |
| GET | `/api/products/{id}` | Get single product | - | `Product` object |
| POST | `/api/products` | Create product | `{ sku, name, description, price, active }` | `Product` object |
| PUT | `/api/products/{id}` | Update product | `{ sku, name, description, price, active }` | `Product` object |
| DELETE | `/api/products/{id}` | Delete product | - | `{ message: "Deleted" }` |
| DELETE | `/api/products/bulk` | Delete all products (async) | - | `{ task_id: "uuid", message: "Bulk delete started" }` |

### 5.2 Upload Endpoint

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| POST | `/api/upload` | Upload CSV file | `multipart/form-data: file` | `{ task_id: "uuid", message: "Processing started" }` |

### 5.3 Progress Endpoint

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/api/progress/{task_id}` | SSE stream for task progress | - | Event stream |

**SSE Event Format:**
```javascript
data: {"status": "started", "message": "Parsing CSV file..."}

data: {"status": "processing", "current": 25000, "total": 500000, "percent": 5, "message": "Imported 25,000 products"}

data: {"status": "complete", "imported": 500000, "errors": 0, "message": "Import complete!"}

data: {"status": "error", "message": "Invalid CSV format at row 1234"}
```

### 5.4 Webhook Endpoints

| Method | Endpoint | Description | Request | Response |
|--------|----------|-------------|---------|----------|
| GET | `/api/webhooks` | List all webhooks | - | `[Webhook]` |
| GET | `/api/webhooks/{id}` | Get webhook | - | `Webhook` object |
| POST | `/api/webhooks` | Create webhook | `{ url, event_type, enabled }` | `Webhook` object |
| PUT | `/api/webhooks/{id}` | Update webhook | `{ url, event_type, enabled }` | `Webhook` object |
| DELETE | `/api/webhooks/{id}` | Delete webhook | - | `{ message: "Deleted" }` |
| POST | `/api/webhooks/{id}/test` | Test webhook | `{ payload }` | `{ status: 200, time_ms: 150 }` |
| GET | `/api/webhooks/{id}/logs` | Get webhook logs | `?limit=50` | `[WebhookLog]` |

---

## 6. Asynchronous Processing

### 6.1 Celery Task Flow

```python
# app/tasks.py

from app.celery_app import celery_app
from app.utils import publish_progress, process_csv_batch, send_webhook
from sqlalchemy import create_engine, text
import csv
import os

@celery_app.task(bind=True)
def import_csv_task(self, file_path: str, task_id: str):
    """
    Import CSV file asynchronously with progress updates via Redis pub/sub
    """
    try:
        # Step 1: Publish initial status
        publish_progress(task_id, {
            "status": "started",
            "message": "Parsing CSV file..."
        })
        
        # Step 2: Count total rows (for progress calculation)
        with open(file_path, 'r', encoding='utf-8') as f:
            total_rows = sum(1 for _ in f) - 1  # Exclude header
        
        publish_progress(task_id, {
            "status": "processing",
            "total": total_rows,
            "current": 0,
            "percent": 0,
            "message": f"Found {total_rows:,} products to import"
        })
        
        # Step 3: Stream CSV and batch process
        imported = 0
        batch = []
        batch_size = 1000
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                batch.append(row)
                
                if len(batch) >= batch_size:
                    # Process batch (upsert with case-insensitive SKU)
                    process_csv_batch(batch)
                    imported += len(batch)
                    batch = []
                    
                    # Publish progress
                    percent = int((imported / total_rows) * 100)
                    publish_progress(task_id, {
                        "status": "processing",
                        "current": imported,
                        "total": total_rows,
                        "percent": percent,
                        "message": f"Imported {imported:,} of {total_rows:,} products"
                    })
            
            # Process remaining rows
            if batch:
                process_csv_batch(batch)
                imported += len(batch)
        
        # Step 4: Complete
        publish_progress(task_id, {
            "status": "complete",
            "imported": imported,
            "total": total_rows,
            "percent": 100,
            "message": f"Import complete! {imported:,} products imported."
        })
        
        # Cleanup uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        publish_progress(task_id, {
            "status": "error",
            "message": str(e)
        })
        raise


@celery_app.task
def bulk_delete_task(task_id: str):
    """
    Delete all products asynchronously
    """
    try:
        publish_progress(task_id, {
            "status": "started",
            "message": "Starting bulk delete..."
        })
        
        from app.db import sync_engine
        from app.models import Product
        
        with sync_engine.connect() as conn:
            result = conn.execute(text("DELETE FROM products"))
            conn.commit()
            deleted_count = result.rowcount
        
        publish_progress(task_id, {
            "status": "complete",
            "deleted": deleted_count,
            "message": f"Deleted {deleted_count:,} products"
        })
        
    except Exception as e:
        publish_progress(task_id, {
            "status": "error",
            "message": str(e)
        })
        raise


@celery_app.task
def send_webhook_task(webhook_id: int, event_type: str, payload: dict):
    """
    Send webhook notification asynchronously
    """
    send_webhook(webhook_id, event_type, payload)
```

### 6.2 Batch Insert Strategy

```python
# app/utils.py

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import func
from app.models import Product
from app.db import sync_engine
import redis
import json
import os

# Redis client for pub/sub
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

def process_csv_batch(batch: list):
    """
    Insert or update products in batch using PostgreSQL UPSERT (sync for Celery)
    """
    from sqlalchemy.orm import Session
    
    with Session(sync_engine) as session:
        for row in batch:
            # Case-insensitive SKU upsert
            stmt = insert(Product).values(
                sku=row['sku'],
                name=row['name'],
                description=row.get('description', ''),
                price=row.get('price'),
                active=True
            ).on_conflict_do_update(
                index_elements=[func.lower(Product.sku)],
                set_={
                    'name': row['name'],
                    'description': row.get('description', ''),
                    'price': row.get('price'),
                    'updated_at': func.now()
                }
            )
            
            session.execute(stmt)
        
        session.commit()

def publish_progress(task_id: str, data: dict):
    """
    Publish progress update to Redis channel for SSE streaming
    """
    channel = f"task_progress:{task_id}"
    redis_client.publish(channel, json.dumps(data))
```

### 6.3 Progress Publishing



---

## 7. Real-Time Progress Updates

### 7.1 SSE Implementation

**Backend (FastAPI):**
```python
# app/routers/upload.py

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import redis
import os

router = APIRouter()
redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

@router.get("/progress/{task_id}")
async def stream_progress(task_id: str):
    """
    Server-Sent Events endpoint for real-time progress via Redis pub/sub
    """
    async def event_generator():
        pubsub = redis_client.pubsub()
        channel = f"task_progress:{task_id}"
        pubsub.subscribe(channel)
        
        try:
            for message in pubsub.listen():
                if message['type'] == 'message':
                    data = message['data'].decode('utf-8')
                    yield f"data: {data}\n\n"
                    
                    # Stop streaming on complete/error
                    import json
                    msg = json.loads(data)
                    if msg.get('status') in ['complete', 'error']:
                        break
        finally:
            pubsub.unsubscribe()
            pubsub.close()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**Frontend (JavaScript):**
```javascript
// static/app.js

function uploadCSV(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
    .then(res => res.json())
    .then(data => {
        // Start listening to progress
        const eventSource = new EventSource(`/api/progress/${data.task_id}`);
        
        eventSource.onmessage = (event) => {
            const progress = JSON.parse(event.data);
            updateProgressBar(progress.percent);
            updateStatusMessage(progress.message);
            
            if (progress.status === 'complete' || progress.status === 'error') {
                eventSource.close();
                showCompletionDialog(progress);
            }
        };
    });
}
```

---

## 8. Deployment Architecture

### 8.1 Deployment Platform: **Render** (Recommended)

**Services Required:**
1. **Web Service** - FastAPI application
2. **Background Worker** - Celery worker
3. **Redis** - Message broker + pub/sub
4. **PostgreSQL** - Database

### 8.2 Render Configuration (`render.yaml`)

```yaml
services:
  # FastAPI Web Service
  - type: web
    name: product-importer-web
    env: python
    runtime: python-3.11
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: product-importer-db
          property: connectionString
      - key: REDIS_URL
        fromDatabase:
          name: product-importer-redis
          property: connectionString
      - key: CELERY_BROKER_URL
        fromDatabase:
          name: product-importer-redis
          property: connectionString
    
  # Celery Worker
  - type: worker
    name: product-importer-worker
    env: python
    runtime: python-3.11
    buildCommand: pip install -r requirements.txt
    startCommand: celery -A app.celery_app worker --loglevel=info
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: product-importer-db
          property: connectionString
      - key: REDIS_URL
        fromDatabase:
          name: product-importer-redis
          property: connectionString
      - key: CELERY_BROKER_URL
        fromDatabase:
          name: product-importer-redis
          property: connectionString

databases:
  - name: product-importer-db
    databaseName: products
    user: products_user
    plan: free

  - name: product-importer-redis
    plan: free
```

### 8.3 Environment Variables

```bash
# .env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname
REDIS_URL=redis://host:6379/0
CELERY_BROKER_URL=redis://host:6379/0
CELERY_RESULT_BACKEND=redis://host:6379/0
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

### 8.4 Timeout Handling

**Problem:** Heroku/Render have 30-second HTTP timeout limits.

**Solution:**
1. Upload endpoint immediately returns `202 Accepted` with `task_id`
2. CSV processing happens in background worker (no time limit)
3. Client polls/streams progress via SSE (separate connection)
4. Worker can run for hours if needed

---

## 9. Security Considerations

### 9.1 Input Validation
- **CSV Upload:** Validate file type, size limit (max 100MB)
- **SKU Format:** Alphanumeric + hyphens only
- **SQL Injection:** Use SQLAlchemy ORM (parameterized queries)
- **XSS Prevention:** Sanitize user inputs in frontend

### 9.2 CORS Configuration
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-app.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 9.3 Rate Limiting
- Webhook calls: Max 1000/hour per webhook
- API endpoints: 100 requests/minute per IP

### 9.4 Authentication (Future Enhancement)
- Current: No auth (as per assignment)
- Future: JWT tokens, API keys for webhooks

---

## 10. Performance Optimization

### 10.1 Database Optimizations
- **Indexes:** SKU (case-insensitive), active, name, created_at
- **Batch Inserts:** 1000 records per transaction
- **Connection Pooling:** SQLAlchemy pool (size=10, max_overflow=20)
- **UPSERT:** PostgreSQL `ON CONFLICT` for efficient updates

### 10.2 CSV Processing
- **Streaming:** Process line-by-line (no full file load)
- **Batch Size:** 1000 rows per DB transaction
- **Memory:** Max ~50MB memory footprint for 500k records

### 10.3 Caching Strategy
- **Redis Cache:** Webhook configurations (TTL: 5 minutes)
- **Database Cache:** Product count (updated on import)

### 10.4 Scalability
- **Horizontal Scaling:** Add more Celery workers
- **Database:** PostgreSQL read replicas (future)
- **CDN:** Static assets via CDN (future)

---

## 11. Monitoring & Logging

### 11.1 Application Logs
- **Level:** INFO (production), DEBUG (development)
- **Format:** JSON structured logs
- **Storage:** Render logs / CloudWatch

### 11.2 Metrics to Track
- CSV import time (avg, p95, p99)
- Webhook delivery success rate
- Database connection pool usage
- Celery queue length

### 11.3 Error Tracking
- Failed CSV imports → Log to database
- Webhook failures → Store in `webhook_logs`
- Application errors → Sentry (optional)

---

## 12. Testing Strategy

### 12.1 Unit Tests
- CSV processor validation logic
- SKU case-insensitive uniqueness
- Webhook payload formatting

### 12.2 Integration Tests
- End-to-end CSV import flow
- API endpoint responses
- Database transactions

### 12.3 Load Testing
- Simulate 500k record import
- Concurrent API requests
- Webhook delivery under load

---

## 13. Future Enhancements

### 13.1 Phase 2 Features
- [ ] User authentication & authorization
- [ ] CSV export functionality
- [ ] Advanced filtering (price range, tags)
- [ ] Product categories & relationships
- [ ] Image upload support
- [ ] Audit trail for all changes

### 13.2 Technical Improvements
- [ ] GraphQL API option
- [ ] WebSocket fallback for SSE
- [ ] Database sharding for 10M+ products
- [ ] Elasticsearch for full-text search
- [ ] Rate limiting per user
- [ ] API versioning (v1, v2)

---

## 14. Conclusion

This architecture provides a **production-ready, scalable solution** for importing and managing large product datasets. Key strengths:

✅ **Handles 500k+ records** without timeout  
✅ **Real-time progress** via SSE  
✅ **Async processing** with Celery  
✅ **Clean separation** of concerns  
✅ **Easy deployment** on modern platforms  
✅ **Optimized performance** with batching & indexing  

The system is designed to be:
- **Maintainable:** Clear code structure, documented
- **Scalable:** Horizontal worker scaling
- **Reliable:** Error handling, logging, retries
- **User-friendly:** Simple UI, clear progress feedback

---

**End of Architecture Document**
