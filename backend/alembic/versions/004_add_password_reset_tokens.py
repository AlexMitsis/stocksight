"""Add password reset tokens table

Revision ID: 004_password_reset
Revises: 003_pgvector
Create Date: 2025-12-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_password_reset'
down_revision = '003_pgvector'
branch_labels = None
depends_on = None


def upgrade():
    """Create password_reset_tokens table."""
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('used_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('is_used', sa.Boolean(), server_default=sa.text('FALSE'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('token')
    )

    # Create indexes for performance
    op.create_index('idx_reset_token', 'password_reset_tokens', ['token'])
    op.create_index('idx_reset_user_id', 'password_reset_tokens', ['user_id'])
    op.create_index('idx_reset_expires', 'password_reset_tokens', ['expires_at'])


def downgrade():
    """Drop password_reset_tokens table."""
    op.drop_index('idx_reset_expires', table_name='password_reset_tokens')
    op.drop_index('idx_reset_user_id', table_name='password_reset_tokens')
    op.drop_index('idx_reset_token', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
