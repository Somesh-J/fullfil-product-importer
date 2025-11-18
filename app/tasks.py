# app/tasks.py
# Celery background tasks
# - import_csv_task: CSV import with batch processing
# - bulk_delete_task: Delete all products
# - send_webhook_task: Send webhook notifications

import os
import time
import traceback
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any

import httpx
import redis
from sqlalchemy import text, select, update
from sqlalchemy.dialects.postgresql import insert

from app.celery_app import celery_app
from app.db import SyncSessionLocal
from app.models import Product, ImportJob, Webhook, WebhookEvent
from app.utils import publish_progress, stream_csv_file, safe_float, clean_string


# Configuration
IMPORT_BATCH_SIZE = int(os.getenv("IMPORT_BATCH_SIZE", "10000"))  # Optimized batch size for maximum performance

# Redis client for checking cancellation
def get_sync_redis():
    """Get synchronous Redis client"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return redis.from_url(redis_url, decode_responses=True)


@celery_app.task(bind=True, name="app.tasks.import_csv_task")
def import_csv_task(self, job_id: str):
    """
    Import CSV file in background with batch processing and progress updates
    
    Args:
        job_id: UUID of the ImportJob record
    """
    print(f"[Task] Starting CSV import for job {job_id}")
    
    session = SyncSessionLocal()
    redis_client = get_sync_redis()
    
    try:
        # Check if job is already cancelled
        if redis_client.get(f"cancel:{job_id}"):
            print(f"[Import] Job {job_id} was cancelled before starting")
            session.close()
            return
        
        # Fetch ImportJob and CSV data from database
        import_job = session.query(ImportJob).filter(ImportJob.id == job_id).first()
        if not import_job:
            print(f"[Import] ERROR: Job {job_id} not found in database")
            session.close()
            return
        
        if not import_job.csv_data:
            print(f"[Import] ERROR: No CSV data found for job {job_id}")
            session.execute(
                update(ImportJob)
                .where(ImportJob.id == job_id)
                .values(status="failed", error="No CSV data found")
            )
            session.commit()
            session.close()
            return
        
        # Update job status to running
        session.execute(
            update(ImportJob)
            .where(ImportJob.id == job_id)
            .values(status="running")
        )
        session.commit()
        
        # Publish initial progress
        publish_progress(job_id, {
            "status": "processing",
            "processed": 0,
            "percent": 0,
            "message": "Starting CSV import..."
        })
        
        # Stream and process CSV from database
        import csv
        import io
        
        csv_reader = csv.DictReader(io.StringIO(import_job.csv_data))
        
        batch = []
        processed = 0
        total_inserted = 0
        total_updated = 0
        
        for row in csv_reader:
            # Check for cancellation every few rows
            if processed % 100 == 0 and redis_client.get(f"cancel:{job_id}"):
                print(f"[Import] Job {job_id} cancelled at {processed} rows")
                publish_progress(job_id, {
                    "status": "error",
                    "error": "Import cancelled by user",
                    "message": f"Import cancelled after processing {processed:,} rows"
                })
                session.rollback()
                session.close()
                return
            
            # Extract and clean data
            sku = clean_string(row.get('sku', ''), max_length=255)
            if not sku:
                continue  # Skip rows without SKU
            
            sku_ci = sku.lower()
            name = clean_string(row.get('name', ''), max_length=1024)
            description = clean_string(row.get('description', ''))
            
            # Parse price (optional)
            price_str = row.get('price', '')
            price = None
            if price_str:
                try:
                    price = Decimal(str(safe_float(price_str)))
                except:
                    price = None
            
            batch.append({
                'sku': sku,
                'sku_ci': sku_ci,
                'name': name or sku,  # Default name to SKU if empty
                'description': description,
                'price': price,
                'active': True
            })
            
            # Process batch when size reached
            if len(batch) >= IMPORT_BATCH_SIZE:
                # Check cancellation before batch insert
                if redis_client.get(f"cancel:{job_id}"):
                    print(f"[Import] Job {job_id} cancelled before batch insert")
                    session.rollback()
                    session.close()
                    return
                
                inserted, updated = _upsert_batch(session, batch)
                total_inserted += inserted
                total_updated += updated
                processed += len(batch)
                batch = []
                
                # Update job progress
                session.execute(
                    update(ImportJob)
                    .where(ImportJob.id == job_id)
                    .values(processed_rows=processed)
                )
                session.commit()
                
                # Publish progress with percentage (approximate based on file size would be better)
                publish_progress(job_id, {
                    "status": "processing",
                    "processed": processed,
                    "inserted": total_inserted,
                    "updated": total_updated,
                    "percent": min(99, int(processed / 5000)),  # Rough estimate, max 99%
                    "message": f"Processed {processed:,} rows"
                })
                
                print(f"[Import] Processed {processed} rows (batch size: {IMPORT_BATCH_SIZE})")
        
        # Final cancellation check
        if redis_client.get(f"cancel:{job_id}"):
            print(f"[Import] Job {job_id} cancelled before final batch")
            session.rollback()
            session.close()
            return
        
        # Process remaining rows
        if batch:
            inserted, updated = _upsert_batch(session, batch)
            total_inserted += inserted
            total_updated += updated
            processed += len(batch)
        
        # Mark job as completed
        session.execute(
            update(ImportJob)
            .where(ImportJob.id == job_id)
            .values(
                status="completed",
                total_rows=processed,
                processed_rows=processed
            )
        )
        session.commit()
        
        # Publish completion
        publish_progress(job_id, {
            "status": "complete",
            "processed": processed,
            "inserted": total_inserted,
            "updated": total_updated,
            "percent": 100,
            "message": f"Import complete! Processed {processed:,} products ({total_inserted:,} new, {total_updated:,} updated)"
        })
        
        print(f"[Import] Completed successfully: {processed} rows processed")
        
        # Cleanup: Remove uploaded file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"[Import] Deleted temporary file: {file_path}")
        except Exception as e:
            print(f"[Import] Warning: Could not delete file {file_path}: {e}")
            
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        print(f"[Import] ERROR: {error_msg}")
        print(error_trace)
        
        # Mark job as failed
        try:
            session.rollback()
            session.execute(
                update(ImportJob)
                .where(ImportJob.id == job_id)
                .values(
                    status="failed",
                    error=error_trace
                )
            )
            session.commit()
        except Exception as db_err:
            print(f"[Import] Failed to update job status: {db_err}")
        
        # Publish error
        publish_progress(job_id, {
            "status": "error",
            "error": error_msg,
            "message": f"Import failed: {error_msg}"
        })
        
        raise
    finally:
        session.close()


def _upsert_batch(session, batch: List[Dict[str, Any]]) -> tuple[int, int]:
    """
    Upsert batch of products using PostgreSQL ON CONFLICT
    
    Args:
        session: Sync Session
        batch: List of product dicts
        
    Returns:
        Tuple of (inserted_count, updated_count)
    """
    if not batch:
        return 0, 0
    
    # Deduplicate batch by sku_ci (keep last occurrence)
    seen = {}
    for row in batch:
        seen[row['sku_ci']] = row
    deduped_batch = list(seen.values())
    
    # Track inserted vs updated
    skus_ci = [row['sku_ci'] for row in deduped_batch]
    result = session.execute(
        select(Product.sku_ci).where(Product.sku_ci.in_(skus_ci))
    )
    existing_skus = {row[0] for row in result.fetchall()}
    
    updated_count = len(existing_skus)
    inserted_count = len(deduped_batch) - updated_count
    
    # Perform upsert
    stmt = insert(Product).values(deduped_batch)
    stmt = stmt.on_conflict_do_update(
        index_elements=['sku_ci'],
        set_={
            'sku': stmt.excluded.sku,
            'name': stmt.excluded.name,
            'description': stmt.excluded.description,
            'price': stmt.excluded.price,
            'active': stmt.excluded.active,
            'updated_at': text('now()')
        }
    )
    
    session.execute(stmt)
    session.commit()
    
    return inserted_count, updated_count


@celery_app.task(bind=True, name="app.tasks.bulk_delete_task")
def bulk_delete_task(self, job_id: str = None):
    """
    Delete all products from database
    
    Args:
        job_id: Optional job ID for progress tracking
    """
    print(f"[Task] Starting bulk delete, job_id: {job_id}")
    
    session = SyncSessionLocal()
    
    try:
        if job_id:
            publish_progress(job_id, {
                "status": "processing",
                "message": "Deleting all products..."
            })
        
        # Execute TRUNCATE for fast deletion
        session.execute(text("TRUNCATE TABLE products RESTART IDENTITY CASCADE"))
        session.commit()
        
        print("[Bulk Delete] All products deleted successfully")
        
        if job_id:
            publish_progress(job_id, {
                "status": "complete",
                "message": "Bulk delete completed. All products removed."
            })
            
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        print(f"[Bulk Delete] ERROR: {error_msg}")
        print(error_trace)
        
        if job_id:
            publish_progress(job_id, {
                "status": "error",
                "error": error_msg,
                "message": f"Bulk delete failed: {error_msg}"
            })
        
        raise
    finally:
        session.close()


@celery_app.task(bind=True, name="app.tasks.send_webhook_task")
def send_webhook_task(self, webhook_id: int, event_type: str, payload: Dict[str, Any]):
    """
    Send webhook notification in background
    
    Args:
        webhook_id: ID of webhook configuration
        event_type: Event type (e.g., 'product.created')
        payload: JSON payload to send
    """
    print(f"[Task] Sending webhook {webhook_id} for event {event_type}")
    
    session = SyncSessionLocal()
    
    try:
        # Fetch webhook configuration
        result = session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            print(f"[Webhook] Webhook {webhook_id} not found")
            return
        
        if not webhook.enabled:
            print(f"[Webhook] Webhook {webhook_id} is disabled, skipping")
            return
        
        # Send HTTP POST request
        start_time = time.time()
        
        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                webhook.url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ProductImporter-Webhook/1.0"
                }
            )
            
            response_time_ms = int((time.time() - start_time) * 1000)
            status_code = response.status_code
            response_text = response.text[:1000]  # Limit response text
            
            print(f"[Webhook] Sent to {webhook.url}, status: {status_code}, time: {response_time_ms}ms")
            
            # Update webhook last status
            session.execute(
                update(Webhook)
                .where(Webhook.id == webhook_id)
                .values(
                    last_status=status_code,
                    last_response=response_text,
                    updated_at=text('now()')
                )
            )
            
            # Create webhook event log
            event = WebhookEvent(
                webhook_id=webhook_id,
                event_type=event_type,
                payload=payload,
                status=status_code,
                response_text=response_text,
                response_time_ms=response_time_ms
            )
            session.add(event)
            
            session.commit()
            
    except httpx.TimeoutException as e:
        error_msg = f"Timeout: {str(e)}"
        print(f"[Webhook] Timeout sending to webhook {webhook_id}: {error_msg}")
        
        # Log failed attempt
        event = WebhookEvent(
            webhook_id=webhook_id,
            event_type=event_type,
            payload=payload,
            status=0,
            response_text=error_msg,
            response_time_ms=10000  # Timeout threshold
        )
        session.add(event)
        session.commit()
        
    except Exception as e:
        error_msg = str(e)
        error_trace = traceback.format_exc()
        
        print(f"[Webhook] ERROR sending webhook {webhook_id}: {error_msg}")
        print(error_trace)
        
        # Log failed attempt
        event = WebhookEvent(
            webhook_id=webhook_id,
            event_type=event_type,
            payload=payload,
            status=0,
            response_text=error_msg,
            response_time_ms=0
        )
        session.add(event)
        session.commit()
    finally:
        session.close()
