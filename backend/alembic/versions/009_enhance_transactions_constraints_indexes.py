"""enhance transactions table with constraints and indexes

Revision ID: 009_enhance_transactions
Revises: 008_drop_unique_user_ticker
Create Date: 2026-01-31

Adds:
- CHECK constraint for quantity validation (quantity > 0 for BUY/SELL, NULL for DIVIDEND)
- Composite index on (user_id, ticker) for faster lookups
- Index on type for filtering by transaction type
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009_enhance_transactions'
down_revision = '008_drop_unique_user_ticker'
branch_labels = None
depends_on = None


def upgrade():
    """Add constraints and indexes to transactions table."""

    # Add CHECK constraint for quantity validation
    # - BUY/SELL must have quantity > 0
    # - DIVIDEND must have quantity NULL
    op.execute("""
        ALTER TABLE transactions
        ADD CONSTRAINT check_quantity_for_trades
        CHECK (
            (type = 'DIVIDEND' AND quantity IS NULL) OR
            (type IN ('BUY', 'SELL') AND quantity > 0)
        )
    """)

    # Add composite index on (user_id, ticker) for faster queries
    # This optimizes queries that filter by both user and ticker
    op.create_index(
        'idx_transactions_user_ticker',
        'transactions',
        ['user_id', 'ticker']
    )

    # Add index on type for filtering by transaction type
    op.create_index(
        'idx_transactions_type',
        'transactions',
        ['type']
    )


def downgrade():
    """Remove constraints and indexes from transactions table."""

    # Drop indexes
    op.drop_index('idx_transactions_type', table_name='transactions')
    op.drop_index('idx_transactions_user_ticker', table_name='transactions')

    # Drop constraint
    op.execute("""
        ALTER TABLE transactions
        DROP CONSTRAINT IF EXISTS check_quantity_for_trades
    """)
