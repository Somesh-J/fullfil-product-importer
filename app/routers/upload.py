# app/routers/upload.py
# CSV upload endpoints
# - POST /api/upload: Upload CSV and trigger Celery task
# - GET /api/progress/{task_id}: SSE stream for real-time progress

import os
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.models import ImportJob
from app.schemas import ImportJobResponse, MessageResponse
from app.tasks import import_csv_task
from app.utils import get_async_redis

router = APIRouter()

# Configuration
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "100")) * 1024 * 1024  # 100MB default


@router.post("/upload", response_model=ImportJobResponse, status_code=202)
async def upload_csv(
    file: UploadFile = File(..., description="CSV file to import")
):
    """
    Upload CSV file and start import task
    
    - Validates file type and size
    - Saves file to disk
    - Creates ImportJob record
    - Triggers Celery background task
    - Returns job ID for progress tracking
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed"
        )
    
    # Validate content type
    if file.content_type and file.content_type not in ['text/csv', 'application/csv', 'application/vnd.ms-excel']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type: {file.content_type}. Expected CSV file."
        )
    
    # Generate unique job ID
    job_id = uuid.uuid4()
    
    # Read CSV content into memory (for Railway shared access between services)
    try:
        total_size = 0
        csv_content = ""
        
        while chunk := await file.read(8192):  # 8KB chunks
            total_size += len(chunk)
            
            # Check file size limit
            if total_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB"
                )
            
            csv_content += chunk.decode('utf-8', errors='replace')
        
        print(f"[Upload] Read CSV file: {file.filename} ({total_size:,} bytes)")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read file: {str(e)}"
        )
    
    # Create ImportJob record with CSV data
    async with AsyncSessionLocal() as session:
        try:
            import_job = ImportJob(
                id=job_id,
                filename=file.filename,
                csv_data=csv_content,  # Store CSV in database
                status="queued",
                total_rows=None,
                processed_rows=0
            )
            session.add(import_job)
            await session.commit()
            await session.refresh(import_job)
            
            print(f"[Upload] Created ImportJob: {job_id}")
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create import job: {str(e)}"
            )
    
    # Trigger Celery task (pass job_id only, worker will fetch CSV from DB)
    try:
        import_csv_task.delay(str(job_id))
        print(f"[Upload] Triggered import task for job {job_id}")
        
    except Exception as e:
        # Update job status to failed
        async with AsyncSessionLocal() as session:
            import_job.status = "failed"
            import_job.error = f"Failed to start task: {str(e)}"
            session.add(import_job)
            await session.commit()
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start import task: {str(e)}"
        )
    
    return import_job


@router.get("/progress/{job_id}")
async def stream_progress(job_id: str):
    """
    Server-Sent Events endpoint for real-time progress updates
    
    - Subscribes to Redis pub/sub channel for job
    - Streams progress messages as SSE events
    - Auto-closes when job completes or errors
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from Redis pub/sub"""
        import redis.asyncio as aioredis
        import json
        
        # Create a new Redis connection for this SSE stream
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = await aioredis.from_url(
            redis_url,
            decode_responses=True,
            encoding="utf-8"
        )
        pubsub = redis_client.pubsub()
        
        channel = f"job:{job_id}"
        await pubsub.subscribe(channel)
        
        print(f"[SSE] Client connected to progress stream for job {job_id}")
        print(f"[SSE] Subscribed to Redis channel: {channel}")
        
        try:
            # Send initial connection message
            initial_msg = json.dumps({"status": "connected", "job_id": job_id})
            yield f"data: {initial_msg}\n\n"
            
            # Listen for messages
            message_count = 0
            async for message in pubsub.listen():
                print(f"[SSE] Received message type: {message['type']}, data: {message.get('data', 'N/A')}")
                
                if message['type'] == 'message':
                    data = message['data']
                    message_count += 1
                    print(f"[SSE] Forwarding message #{message_count} to client for job {job_id}")
                    
                    # Forward message to client
                    yield f"data: {data}\n\n"
                    
                    # Check if job is complete or failed
                    try:
                        msg_data = json.loads(data)
                        if msg_data.get('status') in ['complete', 'error', 'cancelled']:
                            print(f"[SSE] Job {job_id} finished with status: {msg_data.get('status')}")
                            break
                    except json.JSONDecodeError:
                        pass
                    
        except Exception as e:
            print(f"[SSE] Error in event stream: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {{'status': 'error', 'error': '{str(e)}'}}\n\n"
            
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await redis_client.close()
            print(f"[SSE] Client disconnected from job {job_id}, forwarded {message_count} messages")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/jobs/{job_id}", response_model=ImportJobResponse)
async def get_job_status(job_id: str):
    """
    Get import job status
    
    - Returns current status of import job
    - Useful for polling-based clients
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ImportJob).where(ImportJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Import job {job_id} not found"
            )
        
        return job


@router.post("/jobs/{job_id}/cancel", response_model=MessageResponse)
async def cancel_job(job_id: str):
    """
    Cancel an import job
    
    - Marks job as cancelled in database
    - Sets cancellation flag in Redis
    - Background task will check this flag and stop processing
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ImportJob).where(ImportJob.id == job_id)
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Import job {job_id} not found"
            )
        
        if job.status in ["completed", "failed", "cancelled"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel job with status: {job.status}"
            )
        
        # Set cancellation flag in Redis
        redis_client = await get_async_redis()
        await redis_client.setex(f"cancel:{job_id}", 300, "1")  # Expire after 5 minutes
        
        # Update job status
        from sqlalchemy import update
        await session.execute(
            update(ImportJob)
            .where(ImportJob.id == job_id)
            .values(status="cancelled", error="Cancelled by user")
        )
        await session.commit()
        
        print(f"[Cancel] Job {job_id} marked for cancellation")
        
        return {"message": f"Job {job_id} has been cancelled"}


