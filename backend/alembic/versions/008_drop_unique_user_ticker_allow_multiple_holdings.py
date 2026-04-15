"""drop unique_user_ticker constraint to allow multiple holdings per ticker

Revision ID: 008_drop_unique_user_ticker
Revises: 007_portfolio_performance
Create Date: 2026-01-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '008_drop_unique_user_ticker'
down_revision = '007_portfolio_performance'
branch_labels = None
depends_on = None


def upgrade():
    """
    Drop the unique constraint on (user_id, ticker) to allow multiple holdings per ticker.

    This enables:
    - Multiple purchases of the same stock at different dates/prices
    - Proper lot tracking for FIFO/LIFO cost basis calculations
    - Better transaction history management

    The holdings table will now represent aggregated current positions,
    with transactions table storing the detailed history.
    """
    # Drop the unique constraint
    op.drop_constraint('unique_user_ticker', 'holdings', type_='unique')

    # Add a composite index for performance (user_id, ticker) without uniqueness
    op.create_index('idx_holdings_user_ticker', 'holdings', ['user_id', 'ticker'])


def downgrade():
    """
    Restore the unique constraint.

    WARNING: This will fail if there are multiple holdings for the same ticker.
    Manual data cleanup may be required before downgrade.
    """
    # Drop the index
    op.drop_index('idx_holdings_user_ticker', table_name='holdings')

    # Restore unique constraint
    op.create_unique_constraint('unique_user_ticker', 'holdings', ['user_id', 'ticker'])
