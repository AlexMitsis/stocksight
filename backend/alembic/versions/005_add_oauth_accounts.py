"""Add OAuth accounts table

Revision ID: 005_oauth_accounts
Revises: 004_password_reset
Create Date: 2025-12-21

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '005_oauth_accounts'
down_revision = '004_password_reset'
branch_labels = None
depends_on = None


def upgrade():
    """Create oauth_accounts table."""
    op.create_table(
        'oauth_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),  # 'google' or 'github'
        sa.Column('provider_user_id', sa.String(length=255), nullable=False),  # OAuth provider's user ID
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),  # Store provider's access token
        sa.Column('refresh_token', sa.Text(), nullable=True),  # Store provider's refresh token
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('provider', 'provider_user_id', name='unique_provider_user')
    )

    # Create indexes for performance
    op.create_index('idx_oauth_user_id', 'oauth_accounts', ['user_id'])
    op.create_index('idx_oauth_provider', 'oauth_accounts', ['provider'])


def downgrade():
    """Drop oauth_accounts table."""
    op.drop_index('idx_oauth_provider', table_name='oauth_accounts')
    op.drop_index('idx_oauth_user_id', table_name='oauth_accounts')
    op.drop_table('oauth_accounts')
