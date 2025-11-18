"""Add csv_data to import_jobs

Revision ID: b74aa5bd31f6
Revises: initial_create_tables
Create Date: 2025-11-18 15:12:17.157532

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b74aa5bd31f6'
down_revision = 'initial_create_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add csv_data column to store CSV content temporarily
    op.add_column('import_jobs', sa.Column('csv_data', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove csv_data column
    op.drop_column('import_jobs', 'csv_data')
