# app/schemas.py
# Pydantic schemas for request/response validation
# - Product schemas (Create, Update, Response)
# - Webhook schemas (Create, Update, Response)
# - Pagination schemas
# - Progress schemas

from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ============================================================================
# Product Schemas
# ============================================================================

class ProductBase(BaseModel):
    """Base product schema with common fields"""
    sku: str = Field(..., min_length=1, max_length=255, description="Stock Keeping Unit")
    name: str = Field(..., min_length=1, max_length=1024, description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    price: Optional[Decimal] = Field(None, ge=0, description="Product price")
    active: bool = Field(True, description="Product active status")


class ProductCreate(ProductBase):
    """Schema for creating a product"""
    pass


class ProductUpdate(BaseModel):
    """Schema for updating a product (all fields optional)"""
    sku: Optional[str] = Field(None, min_length=1, max_length=255)
    name: Optional[str] = Field(None, min_length=1, max_length=1024)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, ge=0)
    active: Optional[bool] = None


class ProductResponse(ProductBase):
    """Schema for product response"""
    id: int
    sku_ci: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProductListResponse(BaseModel):
    """Schema for paginated product list"""
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int
    pages: int


# ============================================================================
# Webhook Schemas
# ============================================================================

class WebhookBase(BaseModel):
    """Base webhook schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Webhook name")
    url: str = Field(..., max_length=2048, description="Webhook URL")
    event: str = Field(..., min_length=1, max_length=100, description="Event type")
    enabled: bool = Field(True, description="Webhook enabled status")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    @field_validator('event')
    @classmethod
    def validate_event(cls, v: str) -> str:
        """Validate event type"""
        valid_events = [
            'product.created',
            'product.updated',
            'product.deleted',
            'import.completed',
            'test'
        ]
        if v not in valid_events:
            raise ValueError(f'Event must be one of: {", ".join(valid_events)}')
        return v


class WebhookCreate(WebhookBase):
    """Schema for creating a webhook"""
    pass


class WebhookUpdate(BaseModel):
    """Schema for updating a webhook (all fields optional)"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = Field(None, max_length=2048)
    event: Optional[str] = Field(None, min_length=1, max_length=100)
    enabled: Optional[bool] = None

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        """Validate URL format"""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class WebhookResponse(WebhookBase):
    """Schema for webhook response"""
    id: int
    last_status: Optional[int] = None
    last_response: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookEventResponse(BaseModel):
    """Schema for webhook event log"""
    id: int
    webhook_id: int
    event_type: str
    payload: Optional[dict] = None
    status: Optional[int] = None
    response_text: Optional[str] = None
    response_time_ms: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Import Job Schemas
# ============================================================================

class ImportJobResponse(BaseModel):
    """Schema for import job response"""
    id: UUID
    filename: str
    uploader: Optional[str] = None
    status: str
    total_rows: Optional[int] = None
    processed_rows: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Progress Schemas
# ============================================================================

class ProgressMessage(BaseModel):
    """Schema for progress updates"""
    status: str
    processed: Optional[int] = None
    total: Optional[int] = None
    inserted: Optional[int] = None
    updated: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None


# ============================================================================
# Generic Response Schemas
# ============================================================================

class MessageResponse(BaseModel):
    """Generic message response"""
    message: str


class DeleteResponse(BaseModel):
    """Response for delete operations"""
    deleted: int
    message: str


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete operation"""
    job_id: str
    message: str
    status: str

