# app/routers/webhooks.py
# Webhook CRUD endpoints
# - GET /api/webhooks: List all webhooks
# - GET /api/webhooks/{id}: Get single webhook
# - POST /api/webhooks: Create webhook
# - PUT /api/webhooks/{id}: Update webhook
# - DELETE /api/webhooks/{id}: Delete webhook
# - POST /api/webhooks/{id}/test: Test webhook
# - GET /api/webhooks/{id}/logs: Get webhook logs

from typing import List

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db import AsyncSessionLocal
from app.models import Webhook, WebhookEvent
from app.schemas import (
    WebhookCreate,
    WebhookUpdate,
    WebhookResponse,
    WebhookEventResponse,
    DeleteResponse,
    MessageResponse,
)
from app.tasks import send_webhook_task

router = APIRouter()


@router.get("/webhooks", response_model=List[WebhookResponse])
async def list_webhooks():
    """
    List all webhooks
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Webhook).order_by(Webhook.created_at.desc())
        )
        webhooks = result.scalars().all()
        
        return [WebhookResponse.model_validate(w) for w in webhooks]


@router.get("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(webhook_id: int):
    """
    Get single webhook by ID
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(
                status_code=404,
                detail=f"Webhook {webhook_id} not found"
            )
        
        return WebhookResponse.model_validate(webhook)


@router.post("/webhooks", response_model=WebhookResponse, status_code=201)
async def create_webhook(webhook_data: WebhookCreate):
    """
    Create a new webhook
    
    - URL must be valid HTTP/HTTPS endpoint
    - Event type must be valid
    """
    async with AsyncSessionLocal() as session:
        try:
            webhook = Webhook(
                name=webhook_data.name,
                url=webhook_data.url,
                event=webhook_data.event,
                enabled=webhook_data.enabled
            )
            
            session.add(webhook)
            await session.commit()
            await session.refresh(webhook)
            
            print(f"[Webhooks] Created webhook: {webhook.id} ({webhook.name})")
            
            return WebhookResponse.model_validate(webhook)
            
        except IntegrityError as e:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Database error: {str(e.orig)}"
            )


@router.put("/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(webhook_id: int, webhook_data: WebhookUpdate):
    """
    Update existing webhook
    
    - All fields are optional
    """
    async with AsyncSessionLocal() as session:
        # Fetch webhook
        result = await session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(
                status_code=404,
                detail=f"Webhook {webhook_id} not found"
            )
        
        try:
            # Update fields if provided
            if webhook_data.name is not None:
                webhook.name = webhook_data.name
            
            if webhook_data.url is not None:
                webhook.url = webhook_data.url
            
            if webhook_data.event is not None:
                webhook.event = webhook_data.event
            
            if webhook_data.enabled is not None:
                webhook.enabled = webhook_data.enabled
            
            await session.commit()
            await session.refresh(webhook)
            
            print(f"[Webhooks] Updated webhook: {webhook.id}")
            
            return WebhookResponse.model_validate(webhook)
            
        except IntegrityError as e:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Database error: {str(e.orig)}"
            )


@router.delete("/webhooks/{webhook_id}", response_model=DeleteResponse)
async def delete_webhook(webhook_id: int):
    """
    Delete a webhook by ID
    
    - Also deletes all associated webhook events (cascade)
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(
                status_code=404,
                detail=f"Webhook {webhook_id} not found"
            )
        
        await session.delete(webhook)
        await session.commit()
        
        print(f"[Webhooks] Deleted webhook: {webhook_id}")
        
        return DeleteResponse(
            deleted=webhook_id,
            message=f"Webhook {webhook_id} deleted successfully"
        )


@router.post("/webhooks/{webhook_id}/test", response_model=MessageResponse)
async def test_webhook(webhook_id: int):
    """
    Test webhook by sending a test event
    
    - Sends test payload to webhook URL
    - Creates webhook event log
    - Returns immediately (webhook sent in background)
    """
    async with AsyncSessionLocal() as session:
        # Fetch webhook
        result = await session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(
                status_code=404,
                detail=f"Webhook {webhook_id} not found"
            )
        
        if not webhook.enabled:
            raise HTTPException(
                status_code=400,
                detail=f"Webhook {webhook_id} is disabled. Enable it first."
            )
    
    # Prepare test payload
    test_payload = {
        "event": "test",
        "webhook_id": webhook_id,
        "message": "This is a test webhook event",
        "timestamp": "2025-11-18T00:00:00Z"
    }
    
    # Trigger webhook task
    try:
        send_webhook_task.delay(webhook_id, "test", test_payload)
        print(f"[Webhooks] Test webhook dispatched for webhook {webhook_id}")
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to dispatch test webhook: {str(e)}"
        )
    
    return MessageResponse(
        message=f"Test webhook dispatched to {webhook.url}. Check logs for results."
    )


@router.get("/webhooks/{webhook_id}/logs", response_model=List[WebhookEventResponse])
async def get_webhook_logs(
    webhook_id: int,
    limit: int = Query(50, ge=1, le=500, description="Number of logs to return")
):
    """
    Get webhook event logs
    
    - Returns recent delivery attempts
    - Ordered by most recent first
    """
    async with AsyncSessionLocal() as session:
        # Verify webhook exists
        result = await session.execute(
            select(Webhook).where(Webhook.id == webhook_id)
        )
        webhook = result.scalar_one_or_none()
        
        if not webhook:
            raise HTTPException(
                status_code=404,
                detail=f"Webhook {webhook_id} not found"
            )
        
        # Fetch logs
        result = await session.execute(
            select(WebhookEvent)
            .where(WebhookEvent.webhook_id == webhook_id)
            .order_by(WebhookEvent.created_at.desc())
            .limit(limit)
        )
        events = result.scalars().all()
        
        return [WebhookEventResponse.model_validate(e) for e in events]

