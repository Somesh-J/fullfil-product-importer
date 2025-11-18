# Railway Deployment - Important Notes

## 🚨 CSV Storage Architecture

### Problem
Railway services (web + worker) run in **separate containers** without shared file systems. Traditional file-based uploads would fail because:
- Web service saves file to `/uploads` directory
- Worker service can't access `/uploads` from web container
- Result: `FileNotFoundError` in worker

### Solution
**CSV content is stored in the PostgreSQL database** instead of file system:

1. **Upload Process:**
   - User uploads CSV file
   - Web service reads entire CSV content into memory
   - Stores content in `import_jobs.csv_data` (TEXT column)
   - Creates job record with status="queued"

2. **Worker Process:**
   - Fetches job from database by `job_id`
   - Reads CSV from `csv_data` column
   - Parses using `csv.DictReader(io.StringIO(csv_data))`
   - Processes rows in batches

### Benefits
✅ Works across separate Railway containers  
✅ No shared file system needed  
✅ Survives container restarts  
✅ Enables horizontal scaling  
✅ Simplifies deployment

### Tradeoffs
⚠️ Database size increases (temporary - can clean up after import)  
⚠️ Large CSVs (500MB+) stored in database  
⚠️ Memory usage during upload (mitigated by streaming read in chunks)

### Production Recommendations
For very large files (1GB+), consider:
- Using Railway Volumes for shared storage
- Using object storage (S3, GCS, R2)
- Implementing streaming upload to object storage
- Adding cleanup job to delete old CSV data

---

## 📁 File Structure Changes

### Before (Local Development)
```python
# Upload endpoint
file_path = f"/uploads/{job_id}.csv"
with open(file_path, 'wb') as f:
    f.write(await file.read())
    
# Celery task
import_csv_task.delay(job_id, file_path)
```

### After (Railway Production)
```python
# Upload endpoint
csv_content = (await file.read()).decode('utf-8')
import_job.csv_data = csv_content

# Celery task
import_csv_task.delay(job_id)  # No file path needed
```

---

## 🔧 Environment Variables

### Web Service & Worker Service (Same Config)

```bash
# Database (Railway managed)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (Railway managed)
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}

# Import Configuration
IMPORT_BATCH_SIZE=10000
CELERY_CONCURRENCY=4

# File Upload
MAX_FILE_SIZE_MB=500
ALLOWED_ORIGINS=*
```

**Note:** `UPLOAD_DIR` is no longer needed since files are stored in database.

---

## 🗄️ Database Schema

### ImportJob Model

```python
class ImportJob(Base):
    __tablename__ = "import_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    filename = Column(String(512), nullable=False)
    csv_data = Column(Text, nullable=True)  # ← NEW: Stores CSV content
    status = Column(String(50))
    total_rows = Column(Integer)
    processed_rows = Column(Integer)
    error = Column(Text)
    created_at = Column(DateTime)
```

---

## 🚀 Migration Applied

**File:** `alembic/versions/20251118_1512_b74aa5bd31f6_add_csv_data_to_import_jobs.py`

```python
def upgrade() -> None:
    op.add_column('import_jobs', 
        sa.Column('csv_data', sa.Text(), nullable=True))

def downgrade() -> None:
    op.drop_column('import_jobs', 'csv_data')
```

This migration runs automatically on Railway deployment via `docker-entrypoint.sh`.

---

## ✅ Verification

After deployment, check that:

1. **Migration ran successfully:**
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_name = 'import_jobs' AND column_name = 'csv_data';
   ```

2. **CSV stored in database:**
   ```sql
   SELECT id, filename, length(csv_data) as csv_size_bytes 
   FROM import_jobs ORDER BY created_at DESC LIMIT 5;
   ```

3. **Worker can process:**
   - Upload test CSV
   - Check worker logs for successful processing
   - Verify products imported

---

## 📊 Performance Impact

### Database Size
- 500K products CSV (~50MB raw) = ~50MB database storage
- Cleaned up after successful import (optional)

### Memory Usage
- Web service: Reads CSV in 8KB chunks (low memory)
- Worker service: Loads CSV into StringIO (proportional to file size)

### Network Impact
- Worker fetches CSV once from database per job
- No additional network calls during processing

---

## 🔄 Local Development

For local development with Docker Compose, the same architecture works seamlessly:

```yaml
# docker-compose.yml (no changes needed)
services:
  web:
    volumes:
      - .:/app  # Code only, no upload volumes needed
  
  worker:
    volumes:
      - .:/app  # Code only, no upload volumes needed
```

Both services share the same PostgreSQL database, so CSV data is accessible to both.

---

**Last Updated:** November 18, 2025  
**Applies To:** Railway production deployment
