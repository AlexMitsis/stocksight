"""add portfolio performance tables

Revision ID: 007_add_portfolio_performance_tables
Revises: 006_add_holdings_table
Create Date: 2026-01-06 01:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_portfolio_performance'
down_revision = '006_add_holdings_table'
branch_labels = None
depends_on = None


def upgrade():
    """Create portfolio performance tracking tables."""

    # Portfolio snapshots for TWR calculation
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('total_value', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('total_cost_basis', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('holdings_json', postgresql.JSONB(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'snapshot_date', name='unique_user_snapshot_date')
    )

    op.create_index('idx_snapshots_user_id', 'portfolio_snapshots', ['user_id'])
    op.create_index('idx_snapshots_date', 'portfolio_snapshots', ['snapshot_date'])

    # Transactions for MWR calculation
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('type', sa.String(length=10), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=15, scale=6), nullable=True),
        sa.Column('price', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('fees', sa.Numeric(precision=15, scale=2), server_default='0', nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint("type IN ('BUY', 'SELL', 'DIVIDEND')", name='check_transaction_type')
    )

    op.create_index('idx_transactions_user_id', 'transactions', ['user_id'])
    op.create_index('idx_transactions_date', 'transactions', ['transaction_date'])
    op.create_index('idx_transactions_ticker', 'transactions', ['ticker'])

    # Dividends tracking
    op.create_table(
        'dividends',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('ex_date', sa.Date(), nullable=False),
        sa.Column('pay_date', sa.Date(), nullable=True),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint("status IN ('PENDING', 'PAID')", name='check_dividend_status')
    )

    op.create_index('idx_dividends_user_id', 'dividends', ['user_id'])
    op.create_index('idx_dividends_ticker', 'dividends', ['ticker'])
    op.create_index('idx_dividends_ex_date', 'dividends', ['ex_date'])


def downgrade():
    """Drop portfolio performance tracking tables."""
    op.drop_index('idx_dividends_ex_date', table_name='dividends')
    op.drop_index('idx_dividends_ticker', table_name='dividends')
    op.drop_index('idx_dividends_user_id', table_name='dividends')
    op.drop_table('dividends')

    op.drop_index('idx_transactions_ticker', table_name='transactions')
    op.drop_index('idx_transactions_date', table_name='transactions')
    op.drop_index('idx_transactions_user_id', table_name='transactions')
    op.drop_table('transactions')

    op.drop_index('idx_snapshots_date', table_name='portfolio_snapshots')
    op.drop_index('idx_snapshots_user_id', table_name='portfolio_snapshots')
    op.drop_table('portfolio_snapshots')
