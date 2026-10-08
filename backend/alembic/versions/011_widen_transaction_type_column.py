"""widen transactions.type column

Revision ID: 011_widen_transaction_type
Revises: 010_transfer_adjustment_types
Create Date: 2026-10-08

Migration 010 added TRANSFER_IN (11 chars) and TRANSFER_OUT (12 chars) but left
transactions.type as VARCHAR(10), so inserting those types failed.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011_widen_transaction_type'
down_revision = '010_transfer_adjustment_types'
branch_labels = None
depends_on = None


def upgrade():
    """Widen transactions.type to fit all transaction types."""
    op.alter_column(
        'transactions', 'type',
        existing_type=sa.String(10),
        type_=sa.String(20),
        existing_nullable=False,
    )


def downgrade():
    """Shrink transactions.type back to VARCHAR(10). Fails if transfer rows exist."""
    op.alter_column(
        'transactions', 'type',
        existing_type=sa.String(20),
        type_=sa.String(10),
        existing_nullable=False,
    )
