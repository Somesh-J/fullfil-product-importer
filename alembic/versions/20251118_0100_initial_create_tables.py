"""Initial migration - create all tables

Revision ID: initial_create_tables
Revises: 
Create Date: 2025-11-18 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'initial_create_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create products table
    op.create_table(
        'products',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('sku', sa.String(length=255), nullable=False),
        sa.Column('sku_ci', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=1024), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_products_active', 'products', ['active'], unique=False)
    op.create_index('idx_products_name', 'products', ['name'], unique=False)
    op.create_index('idx_products_sku_ci', 'products', ['sku_ci'], unique=True)
    op.create_index(op.f('ix_products_created_at'), 'products', ['created_at'], unique=False)
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)

    # Create import_jobs table
    op.create_table(
        'import_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=512), nullable=False),
        sa.Column('uploader', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), server_default=sa.text("'queued'"), nullable=False),
        sa.Column('total_rows', sa.Integer(), nullable=True),
        sa.Column('processed_rows', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_import_jobs_status', 'import_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_import_jobs_created_at'), 'import_jobs', ['created_at'], unique=False)
    op.create_index(op.f('ix_import_jobs_id'), 'import_jobs', ['id'], unique=False)

    # Create webhooks table
    op.create_table(
        'webhooks',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.String(length=2048), nullable=False),
        sa.Column('event', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('last_status', sa.Integer(), nullable=True),
        sa.Column('last_response', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_webhooks_enabled', 'webhooks', ['enabled'], unique=False)
    op.create_index('idx_webhooks_event', 'webhooks', ['event'], unique=False)
    op.create_index(op.f('ix_webhooks_id'), 'webhooks', ['id'], unique=False)

    # Create webhook_events table
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('webhook_id', sa.BigInteger(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.Integer(), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['webhook_id'], ['webhooks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_webhook_events_created_at', 'webhook_events', ['created_at'], unique=False)
    op.create_index('idx_webhook_events_webhook_id', 'webhook_events', ['webhook_id'], unique=False)
    op.create_index(op.f('ix_webhook_events_created_at'), 'webhook_events', ['created_at'], unique=False)
    op.create_index(op.f('ix_webhook_events_id'), 'webhook_events', ['id'], unique=False)
    op.create_index(op.f('ix_webhook_events_webhook_id'), 'webhook_events', ['webhook_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_webhook_events_webhook_id'), table_name='webhook_events')
    op.drop_index(op.f('ix_webhook_events_id'), table_name='webhook_events')
    op.drop_index(op.f('ix_webhook_events_created_at'), table_name='webhook_events')
    op.drop_index('idx_webhook_events_webhook_id', table_name='webhook_events')
    op.drop_index('idx_webhook_events_created_at', table_name='webhook_events')
    op.drop_table('webhook_events')

    op.drop_index(op.f('ix_webhooks_id'), table_name='webhooks')
    op.drop_index('idx_webhooks_event', table_name='webhooks')
    op.drop_index('idx_webhooks_enabled', table_name='webhooks')
    op.drop_table('webhooks')

    op.drop_index(op.f('ix_import_jobs_id'), table_name='import_jobs')
    op.drop_index(op.f('ix_import_jobs_created_at'), table_name='import_jobs')
    op.drop_index('idx_import_jobs_status', table_name='import_jobs')
    op.drop_table('import_jobs')

    op.drop_index(op.f('ix_products_id'), table_name='products')
    op.drop_index(op.f('ix_products_created_at'), table_name='products')
    op.drop_index('idx_products_sku_ci', table_name='products')
    op.drop_index('idx_products_name', table_name='products')
    op.drop_index('idx_products_active', table_name='products')
    op.drop_table('products')
