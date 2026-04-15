"""add transfer and adjustment transaction types

Revision ID: 010_transfer_adjustment_types
Revises: 009_enhance_transactions
Create Date: 2026-01-31

Adds:
- New transaction types: TRANSFER_IN, TRANSFER_OUT, ADJUSTMENT
- cost_basis_known column for TRANSFER_IN transactions with unknown cost basis
- Updated constraints for new transaction types
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010_transfer_adjustment_types'
down_revision = '009_enhance_transactions'
branch_labels = None
depends_on = None


def upgrade():
    """Add new transaction types and cost_basis_known column."""

    # Drop existing constraints that need to be updated
    op.execute("""
        ALTER TABLE transactions
        DROP CONSTRAINT IF EXISTS check_transaction_type
    """)
    op.execute("""
        ALTER TABLE transactions
        DROP CONSTRAINT IF EXISTS check_quantity_for_trades
    """)

    # Add cost_basis_known column (defaults to TRUE)
    op.add_column(
        'transactions',
        sa.Column('cost_basis_known', sa.Boolean(), nullable=False, server_default='true')
    )

    # Add new CHECK constraint for transaction types
    # Now includes: BUY, SELL, DIVIDEND, TRANSFER_IN, TRANSFER_OUT, ADJUSTMENT
    op.execute("""
        ALTER TABLE transactions
        ADD CONSTRAINT check_transaction_type
        CHECK (type IN ('BUY', 'SELL', 'DIVIDEND', 'TRANSFER_IN', 'TRANSFER_OUT', 'ADJUSTMENT'))
    """)

    # Add updated CHECK constraint for quantity validation
    # - BUY/SELL: quantity > 0
    # - DIVIDEND: quantity IS NULL
    # - TRANSFER_IN/TRANSFER_OUT: quantity > 0
    # - ADJUSTMENT: quantity != 0 (can be positive or negative)
    op.execute("""
        ALTER TABLE transactions
        ADD CONSTRAINT check_quantity_for_trades
        CHECK (
            (type = 'DIVIDEND' AND quantity IS NULL) OR
            (type IN ('BUY', 'SELL', 'TRANSFER_IN', 'TRANSFER_OUT') AND quantity > 0) OR
            (type = 'ADJUSTMENT' AND quantity IS NOT NULL AND quantity != 0)
        )
    """)


def downgrade():
    """Remove new transaction types and cost_basis_known column."""

    # Drop updated constraints
    op.execute("""
        ALTER TABLE transactions
        DROP CONSTRAINT IF EXISTS check_transaction_type
    """)
    op.execute("""
        ALTER TABLE transactions
        DROP CONSTRAINT IF EXISTS check_quantity_for_trades
    """)

    # Remove cost_basis_known column
    op.drop_column('transactions', 'cost_basis_known')

    # Restore original constraints (from migrations 007 and 009)
    op.execute("""
        ALTER TABLE transactions
        ADD CONSTRAINT check_transaction_type
        CHECK (type IN ('BUY', 'SELL', 'DIVIDEND'))
    """)
    op.execute("""
        ALTER TABLE transactions
        ADD CONSTRAINT check_quantity_for_trades
        CHECK (
            (type = 'DIVIDEND' AND quantity IS NULL) OR
            (type IN ('BUY', 'SELL') AND quantity > 0)
        )
    """)
