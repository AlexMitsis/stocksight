"""add holdings table

Revision ID: 006_add_holdings_table
Revises: 005_add_oauth_accounts
Create Date: 2026-01-05 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_holdings_table'
down_revision = '005_oauth_accounts'
branch_labels = None
depends_on = None


def upgrade():
    """Create holdings table for portfolio tracking."""
    op.create_table(
        'holdings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('cost_basis', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('purchase_date', sa.Date(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.CheckConstraint('quantity > 0', name='check_quantity_positive'),
        sa.CheckConstraint('cost_basis > 0', name='check_cost_basis_positive'),
        sa.UniqueConstraint('user_id', 'ticker', name='unique_user_ticker')
    )

    # Create indexes for performance
    op.create_index('idx_holdings_user_id', 'holdings', ['user_id'])
    op.create_index('idx_holdings_ticker', 'holdings', ['ticker'])


def downgrade():
    """Drop holdings table and indexes."""
    op.drop_index('idx_holdings_ticker', table_name='holdings')
    op.drop_index('idx_holdings_user_id', table_name='holdings')
    op.drop_table('holdings')
