# API Reference - Product Importer

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000` (local) | `https://your-app.onrender.com` (production)  
**Documentation:** `/docs` (Swagger UI) | `/redoc` (ReDoc)

---

## 📋 Table of Contents

1. [Authentication](#authentication)
2. [Products API](#products-api)
3. [Upload & Import API](#upload--import-api)
4. [Webhooks API](#webhooks-api)
5. [Error Responses](#error-responses)
6. [Rate Limits](#rate-limits)

---

## 1. Authentication

**Current Version:** No authentication required (as per assignment specifications)

**Future Enhancement:** JWT Bearer tokens will be implemented for production use.

---

## 2. Products API

### 2.1 List Products (Paginated)

**Endpoint:** `GET /api/products`

**Description:** Retrieve a paginated list of products with optional filtering.

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `page` | integer | No | 1 | Page number (1-indexed) |
| `page_size` | integer | No | 20 | Items per page (max: 100) |
| `search` | string | No | - | Search in name or description |
| `sku` | string | No | - | Filter by SKU (prefix match, case-insensitive) |
| `active` | boolean | No | - | Filter by active status |

**Example Request:**
```bash
GET /api/products?page=1&page_size=50&search=laptop&active=true
```

**Success Response (200 OK):**
```json
{
  "items": [
    {
      "id": 1,
      "sku": "LAPTOP-001",
      "name": "Dell Latitude 5420",
      "description": "14-inch business laptop",
      "price": 899.99,
      "active": true,
      "created_at": "2025-11-18T10:30:00Z",
      "updated_at": "2025-11-18T10:30:00Z"
    }
  ],
  "total": 1500,
  "page": 1,
  "page_size": 50,
  "pages": 30
}
```

---

### 2.2 Get Single Product

**Endpoint:** `GET /api/products/{id}`

**Description:** Retrieve a single product by ID.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Product ID |

**Example Request:**
```bash
GET /api/products/123
```

**Success Response (200 OK):**
```json
{
  "id": 123,
  "sku": "LAPTOP-001",
  "name": "Dell Latitude 5420",
  "description": "14-inch business laptop",
  "price": 899.99,
  "active": true,
  "created_at": "2025-11-18T10:30:00Z",
  "updated_at": "2025-11-18T10:30:00Z"
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Product not found"
}
```

---

### 2.3 Create Product

**Endpoint:** `POST /api/products`

**Description:** Create a new product.

**Request Body:**
```json
{
  "sku": "LAPTOP-001",
  "name": "Dell Latitude 5420",
  "description": "14-inch business laptop",
  "price": 899.99,
  "active": true
}
```

**Field Validations:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `sku` | string | Yes | 1-255 chars, unique (case-insensitive) |
| `name` | string | Yes | 1-1024 chars |
| `description` | string | No | Max 10,000 chars |
| `price` | decimal | No | >= 0, max 2 decimal places |
| `active` | boolean | No | Default: true |

**Success Response (201 Created):**
```json
{
  "id": 124,
  "sku": "LAPTOP-001",
  "name": "Dell Latitude 5420",
  "description": "14-inch business laptop",
  "price": 899.99,
  "active": true,
  "created_at": "2025-11-18T11:00:00Z",
  "updated_at": "2025-11-18T11:00:00Z"
}
```

**Error Response (400 Bad Request):**
```json
{
  "detail": "Product with SKU 'LAPTOP-001' already exists"
}
```

---

### 2.4 Update Product

**Endpoint:** `PUT /api/products/{id}`

**Description:** Update an existing product.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Product ID |

**Request Body:**
```json
{
  "sku": "LAPTOP-001-V2",
  "name": "Dell Latitude 5420 (Updated)",
  "description": "14-inch business laptop - Refreshed model",
  "price": 799.99,
  "active": true
}
```

**Success Response (200 OK):**
```json
{
  "id": 123,
  "sku": "LAPTOP-001-V2",
  "name": "Dell Latitude 5420 (Updated)",
  "description": "14-inch business laptop - Refreshed model",
  "price": 799.99,
  "active": true,
  "created_at": "2025-11-18T10:30:00Z",
  "updated_at": "2025-11-18T11:15:00Z"
}
```

---

### 2.5 Delete Product

**Endpoint:** `DELETE /api/products/{id}`

**Description:** Delete a single product.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Product ID |

**Success Response (200 OK):**
```json
{
  "message": "Product deleted successfully"
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Product not found"
}
```

---

### 2.6 Bulk Delete All Products

**Endpoint:** `DELETE /api/products/bulk`

**Description:** Delete all products asynchronously (returns immediately, processes in background).

**Request Body:**
```json
{
  "confirm": true
}
```

**Success Response (202 Accepted):**
```json
{
  "job_id": "27b7d206-d19f-441a-afb4-da36c080db73",
  "message": "Bulk delete started. Use the job_id to track progress."
}
```

**Notes:**
- This is an asynchronous operation
- Use the `job_id` to track progress via SSE endpoint
- Requires `confirm: true` to prevent accidental deletion

---

## 3. Upload & Import API

### 3.1 Upload CSV File

**Endpoint:** `POST /api/upload`

**Description:** Upload a CSV file and trigger asynchronous import process.

**Request:** `multipart/form-data`

**Form Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | file | Yes | CSV file (max 500MB) |

**CSV Format:**
```csv
sku,name,description,price
LAPTOP-001,Dell Latitude 5420,14-inch business laptop,899.99
MOUSE-001,Logitech MX Master 3,Wireless mouse,99.99
```

**Required Columns:**
- `sku` (string, unique)
- `name` (string)

**Optional Columns:**
- `description` (string)
- `price` (decimal)

**Example Request (curl):**
```bash
curl -X POST http://localhost:8000/api/upload \
  -F "file=@products.csv"
```

**Success Response (202 Accepted):**
```json
{
  "id": "3f6ed567-7f87-41de-8346-9de468e6f382",
  "filename": "products.csv",
  "status": "queued",
  "message": "CSV upload successful. Import job queued."
}
```

**Error Responses:**

**400 Bad Request - Invalid file type:**
```json
{
  "detail": "Only CSV files are allowed"
}
```

**413 Payload Too Large - File too large:**
```json
{
  "detail": "File size exceeds maximum allowed (500MB)"
}
```

---

### 3.2 Stream Import Progress (SSE)

**Endpoint:** `GET /api/progress/{job_id}`

**Description:** Real-time Server-Sent Events stream for import progress.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | uuid | Yes | Import job ID from upload response |

**Example Request (JavaScript):**
```javascript
const eventSource = new EventSource('/api/progress/3f6ed567-7f87-41de-8346-9de468e6f382');

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data);
};
```

**Event Stream Format:**

**Connected Event:**
```json
{
  "status": "connected",
  "job_id": "3f6ed567-7f87-41de-8346-9de468e6f382"
}
```

**Processing Events:**
```json
{
  "status": "processing",
  "processed": 50000,
  "inserted": 49251,
  "updated": 749,
  "percent": 10,
  "message": "Processed 50,000 rows"
}
```

**Completion Event:**
```json
{
  "status": "complete",
  "processed": 500000,
  "inserted": 377339,
  "updated": 122661,
  "percent": 100,
  "message": "Import complete! Processed 500,000 products (377,339 new, 122,661 updated)"
}
```

**Error Event:**
```json
{
  "status": "error",
  "error": "Invalid CSV format at row 12345",
  "message": "Import failed: Invalid CSV format at row 12345"
}
```

**Cancelled Event:**
```json
{
  "status": "cancelled",
  "message": "Import cancelled after processing 75,000 rows"
}
```

---

### 3.3 Get Job Status

**Endpoint:** `GET /api/jobs/{job_id}`

**Description:** Get current status of an import job (polling alternative to SSE).

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | uuid | Yes | Import job ID |

**Success Response (200 OK):**
```json
{
  "id": "3f6ed567-7f87-41de-8346-9de468e6f382",
  "filename": "products.csv",
  "status": "processing",
  "total_rows": 500000,
  "processed_rows": 150000,
  "error": null,
  "created_at": "2025-11-18T12:30:00Z",
  "updated_at": "2025-11-18T12:35:00Z"
}
```

**Status Values:**
- `queued` - Job queued, not started yet
- `running` - Currently processing
- `completed` - Successfully completed
- `failed` - Error occurred
- `cancelled` - Cancelled by user

---

### 3.4 Cancel Import Job

**Endpoint:** `POST /api/jobs/{job_id}/cancel`

**Description:** Request cancellation of a running import job.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `job_id` | uuid | Yes | Import job ID |

**Success Response (200 OK):**
```json
{
  "message": "Job 3f6ed567-7f87-41de-8346-9de468e6f382 has been cancelled"
}
```

**Error Response (400 Bad Request):**
```json
{
  "detail": "Cannot cancel job with status: completed"
}
```

**Notes:**
- Cancellation is not immediate (checked every ~100 rows)
- Already processed data will remain in database
- Job status will update to `cancelled`

---

## 4. Webhooks API

### 4.1 List Webhooks

**Endpoint:** `GET /api/webhooks`

**Description:** Retrieve all configured webhooks.

**Success Response (200 OK):**
```json
[
  {
    "id": 1,
    "url": "https://example.com/webhook",
    "event_type": "product.created",
    "enabled": true,
    "created_at": "2025-11-18T10:00:00Z",
    "updated_at": "2025-11-18T10:00:00Z"
  },
  {
    "id": 2,
    "url": "https://example.com/import-complete",
    "event_type": "import.completed",
    "enabled": true,
    "created_at": "2025-11-18T10:05:00Z",
    "updated_at": "2025-11-18T10:05:00Z"
  }
]
```

---

### 4.2 Create Webhook

**Endpoint:** `POST /api/webhooks`

**Description:** Create a new webhook configuration.

**Request Body:**
```json
{
  "url": "https://example.com/webhook",
  "event_type": "product.created",
  "enabled": true
}
```

**Field Validations:**

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `url` | string | Yes | Valid HTTP/HTTPS URL, max 1000 chars |
| `event_type` | string | Yes | One of: `product.created`, `product.updated`, `product.deleted`, `import.completed` |
| `enabled` | boolean | No | Default: true |

**Success Response (201 Created):**
```json
{
  "id": 3,
  "url": "https://example.com/webhook",
  "event_type": "product.created",
  "enabled": true,
  "created_at": "2025-11-18T11:00:00Z",
  "updated_at": "2025-11-18T11:00:00Z"
}
```

---

### 4.3 Update Webhook

**Endpoint:** `PUT /api/webhooks/{id}`

**Description:** Update an existing webhook configuration.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Webhook ID |

**Request Body:**
```json
{
  "url": "https://example.com/webhook-v2",
  "event_type": "product.updated",
  "enabled": false
}
```

**Success Response (200 OK):**
```json
{
  "id": 3,
  "url": "https://example.com/webhook-v2",
  "event_type": "product.updated",
  "enabled": false,
  "created_at": "2025-11-18T11:00:00Z",
  "updated_at": "2025-11-18T11:30:00Z"
}
```

---

### 4.4 Delete Webhook

**Endpoint:** `DELETE /api/webhooks/{id}`

**Description:** Delete a webhook configuration.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Webhook ID |

**Success Response (200 OK):**
```json
{
  "message": "Webhook deleted successfully"
}
```

---

### 4.5 Test Webhook

**Endpoint:** `POST /api/webhooks/{id}/test`

**Description:** Send a test payload to the webhook URL.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Webhook ID |

**Request Body (Optional):**
```json
{
  "test_data": {
    "sku": "TEST-001",
    "name": "Test Product"
  }
}
```

**Success Response (200 OK):**
```json
{
  "success": true,
  "status_code": 200,
  "response_time_ms": 145,
  "message": "Webhook test successful"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "success": false,
  "status_code": null,
  "error": "Connection timeout after 5000ms",
  "message": "Webhook test failed"
}
```

---

### 4.6 Get Webhook Logs

**Endpoint:** `GET /api/webhooks/{id}/logs`

**Description:** Retrieve delivery logs for a webhook.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | integer | Yes | Webhook ID |

**Query Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 50 | Max number of logs (max: 200) |

**Success Response (200 OK):**
```json
[
  {
    "id": 1,
    "webhook_id": 1,
    "event_type": "product.created",
    "payload": {
      "event": "product.created",
      "data": {
        "id": 123,
        "sku": "LAPTOP-001",
        "name": "Dell Latitude"
      }
    },
    "response_status": 200,
    "response_time_ms": 150,
    "error_message": null,
    "created_at": "2025-11-18T12:30:00Z"
  }
]
```

---

## 5. Error Responses

### 5.1 Standard Error Format

All error responses follow this format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### 5.2 HTTP Status Codes

| Code | Description | Example |
|------|-------------|---------|
| 200 | OK | Successful GET, PUT, DELETE |
| 201 | Created | Successful POST (resource created) |
| 202 | Accepted | Async operation started |
| 400 | Bad Request | Invalid input, validation error |
| 404 | Not Found | Resource doesn't exist |
| 413 | Payload Too Large | File size exceeds limit |
| 422 | Unprocessable Entity | Pydantic validation error |
| 500 | Internal Server Error | Unexpected server error |

### 5.3 Validation Errors (422)

```json
{
  "detail": [
    {
      "loc": ["body", "sku"],
      "msg": "field required",
      "type": "value_error.missing"
    },
    {
      "loc": ["body", "price"],
      "msg": "ensure this value is greater than or equal to 0",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

---

## 6. Rate Limits

**Current Version:** No rate limiting implemented (as per assignment)

**Future Enhancement:**

| Endpoint Category | Limit | Window |
|------------------|-------|--------|
| Product CRUD | 100 requests | per minute |
| CSV Upload | 5 uploads | per hour |
| Webhook Tests | 10 tests | per minute |
| SSE Connections | 3 concurrent | per user |

---

## 7. Webhook Payload Examples

### 7.1 Product Created Event

```json
{
  "event": "product.created",
  "timestamp": "2025-11-18T12:30:00Z",
  "data": {
    "id": 123,
    "sku": "LAPTOP-001",
    "name": "Dell Latitude 5420",
    "description": "14-inch business laptop",
    "price": 899.99,
    "active": true,
    "created_at": "2025-11-18T12:30:00Z"
  }
}
```

### 7.2 Product Updated Event

```json
{
  "event": "product.updated",
  "timestamp": "2025-11-18T12:35:00Z",
  "data": {
    "id": 123,
    "sku": "LAPTOP-001",
    "name": "Dell Latitude 5420 (Updated)",
    "description": "14-inch business laptop - Refreshed",
    "price": 799.99,
    "active": true,
    "updated_at": "2025-11-18T12:35:00Z"
  }
}
```

### 7.3 Import Completed Event

```json
{
  "event": "import.completed",
  "timestamp": "2025-11-18T12:45:00Z",
  "data": {
    "job_id": "3f6ed567-7f87-41de-8346-9de468e6f382",
    "filename": "products.csv",
    "total_rows": 500000,
    "inserted": 377339,
    "updated": 122661,
    "duration_seconds": 127
  }
}
```

---

## 8. Quick Start Examples

### 8.1 Upload and Track Import (JavaScript)

```javascript
// Upload CSV file
async function uploadAndTrack(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  // 1. Upload file
  const uploadResponse = await fetch('/api/upload', {
    method: 'POST',
    body: formData
  });
  const { id: jobId } = await uploadResponse.json();
  
  // 2. Stream progress
  const eventSource = new EventSource(`/api/progress/${jobId}`);
  
  eventSource.onmessage = (event) => {
    const progress = JSON.parse(event.data);
    
    if (progress.status === 'processing') {
      console.log(`Progress: ${progress.percent}%`);
      updateProgressBar(progress.percent);
    }
    
    if (progress.status === 'complete') {
      console.log('Import complete!', progress);
      eventSource.close();
    }
    
    if (progress.status === 'error') {
      console.error('Import failed:', progress.error);
      eventSource.close();
    }
  };
}
```

### 8.2 Product Management (Python)

```python
import requests

BASE_URL = "http://localhost:8000"

# Create product
response = requests.post(f"{BASE_URL}/api/products", json={
    "sku": "LAPTOP-001",
    "name": "Dell Latitude 5420",
    "price": 899.99,
    "active": True
})
product = response.json()

# List products with filter
response = requests.get(f"{BASE_URL}/api/products", params={
    "page": 1,
    "page_size": 50,
    "search": "laptop",
    "active": True
})
products = response.json()

# Update product
response = requests.put(f"{BASE_URL}/api/products/{product['id']}", json={
    "name": "Dell Latitude 5420 (Updated)",
    "price": 799.99
})

# Delete product
response = requests.delete(f"{BASE_URL}/api/products/{product['id']}")
```

---

**End of API Reference**
