# app/utils.py
# Utility functions
# - CSV processing (streaming, batch upsert)
# - Redis pub/sub for progress updates
# - Webhook HTTP client

import csv
import json
import os
from typing import AsyncGenerator, Dict, Any, Optional
import redis.asyncio as aioredis
import redis

# Redis clients
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Sync Redis client for Celery tasks
sync_redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Async Redis client for FastAPI
async_redis_client = None


async def get_async_redis():
    """Get or create async Redis client"""
    global async_redis_client
    if async_redis_client is None:
        async_redis_client = await aioredis.from_url(
            REDIS_URL,
            decode_responses=True,
            encoding="utf-8"
        )
    return async_redis_client


def publish_progress(job_id: str, data: Dict[str, Any]) -> None:
    """
    Publish progress update to Redis channel (sync version for Celery tasks)
    
    Args:
        job_id: Import job UUID
        data: Progress data dict (status, processed, total, etc.)
    """
    channel = f"job:{job_id}"
    message = json.dumps(data)
    
    try:
        sync_redis_client.publish(channel, message)
        print(f"[Redis Pub/Sub] Published to {channel}: {message}")
    except Exception as e:
        print(f"[Redis Pub/Sub] Error publishing: {e}")


async def publish_progress_async(job_id: str, data: Dict[str, Any]) -> None:
    """
    Async version of publish_progress for FastAPI/async contexts
    
    Args:
        job_id: Import job UUID
        data: Progress data dict
    """
    channel = f"job:{job_id}"
    message = json.dumps(data)
    
    try:
        redis_client = await get_async_redis()
        await redis_client.publish(channel, message)
        print(f"[Redis Pub/Sub] Published to {channel}: {message}")
    except Exception as e:
        print(f"[Redis Pub/Sub] Error publishing: {e}")


def stream_csv_file(file_path: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream CSV file row by row without loading entire file into memory
    
    Args:
        file_path: Path to CSV file
        
    Yields:
        Dict for each row with CSV headers as keys
    """
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield row


def safe_int(value: Any, default: int = 0) -> int:
    """
    Safely cast value to integer
    
    Args:
        value: Value to cast
        default: Default value if casting fails
        
    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely cast value to float
    
    Args:
        value: Value to cast
        default: Default value if casting fails
        
    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def clean_string(value: Any, max_length: Optional[int] = None) -> str:
    """
    Clean and normalize string value
    
    Args:
        value: Value to clean
        max_length: Optional max length to truncate
        
    Returns:
        Cleaned string
    """
    if value is None:
        return ""
    
    result = str(value).strip()
    
    if max_length and len(result) > max_length:
        result = result[:max_length]
    
    return result
