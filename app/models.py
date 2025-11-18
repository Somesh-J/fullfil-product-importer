# app/models.py
# SQLAlchemy ORM models
# - Product model
# - ImportJob model
# - Webhook model
# - WebhookEvent model

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from app.db import Base
import uuid


class Product(Base):
    """
    Product model with case-insensitive SKU uniqueness
    """
    __tablename__ = "products"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    sku = Column(String(255), nullable=False)
    sku_ci = Column(String(255), nullable=False, unique=True, index=True)  # Lowercase SKU for uniqueness
    name = Column(String(1024), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=True)
    active = Column(Boolean, default=True, nullable=False, server_default=text("true"))
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )

    __table_args__ = (
        Index("idx_products_sku_ci", "sku_ci", unique=True),
        Index("idx_products_active", "active"),
        Index("idx_products_name", "name"),
    )

    def __repr__(self):
        return f"<Product(id={self.id}, sku={self.sku}, name={self.name})>"


class ImportJob(Base):
    """
    Import job tracking for CSV uploads
    """
    __tablename__ = "import_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    filename = Column(String(512), nullable=False)
    csv_data = Column(Text, nullable=True)  # Store CSV content for worker access
    uploader = Column(String(255), nullable=True)  # Future: user who uploaded
    status = Column(
        String(50),
        nullable=False,
        default="queued",
        server_default=text("'queued'")
    )  # queued, running, completed, failed
    total_rows = Column(Integer, nullable=True)
    processed_rows = Column(Integer, nullable=True, default=0, server_default=text("0"))
    error = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        index=True
    )

    __table_args__ = (
        Index("idx_import_jobs_status", "status"),
    )

    def __repr__(self):
        return f"<ImportJob(id={self.id}, filename={self.filename}, status={self.status})>"


class Webhook(Base):
    """
    Webhook configuration for event notifications
    """
    __tablename__ = "webhooks"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    event = Column(String(100), nullable=False, index=True)  # product.created, product.updated, product.deleted
    enabled = Column(Boolean, default=True, nullable=False, server_default=text("true"))
    last_status = Column(Integer, nullable=True)  # HTTP status code of last response
    last_response = Column(Text, nullable=True)  # Last response body
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()")
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        onupdate=text("now()"),
    )

    # Relationship to events
    events = relationship("WebhookEvent", back_populates="webhook", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_webhooks_event", "event"),
        Index("idx_webhooks_enabled", "enabled"),
    )

    def __repr__(self):
        return f"<Webhook(id={self.id}, name={self.name}, event={self.event})>"


class WebhookEvent(Base):
    """
    Webhook event log (history of all webhook deliveries)
    """
    __tablename__ = "webhook_events"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    webhook_id = Column(BigInteger, ForeignKey("webhooks.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)  # product.created, product.updated, etc.
    payload = Column(JSONB, nullable=True)  # JSON payload sent to webhook
    status = Column(Integer, nullable=True)  # HTTP response status code
    response_text = Column(Text, nullable=True)  # Response body from webhook
    response_time_ms = Column(Integer, nullable=True)  # Response time in milliseconds
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        index=True
    )

    # Relationship to webhook
    webhook = relationship("Webhook", back_populates="events")

    __table_args__ = (
        Index("idx_webhook_events_webhook_id", "webhook_id"),
        Index("idx_webhook_events_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<WebhookEvent(id={self.id}, webhook_id={self.webhook_id}, event_type={self.event_type})>"
