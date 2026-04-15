"""Add pgvector extension and conversation_embeddings table

Revision ID: 003_pgvector
Revises: 893f862b679e
Create Date: 2025-12-15 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '003_pgvector'
down_revision: Union[str, Sequence[str], None] = '893f862b679e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Enable pgvector extension and create conversation_embeddings table.

    This migration:
    1. Enables the pgvector PostgreSQL extension for vector similarity search
    2. Creates conversation_embeddings table for storing conversation context as vectors
    3. Creates indexes for efficient querying (thread_id, created_at, vector similarity)
    """
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create conversation_embeddings table
    op.create_table(
        'conversation_embeddings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.String(255), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(1536), nullable=False),
        sa.Column('meta', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                 server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for efficient querying
    op.create_index(
        op.f('ix_conversation_embeddings_id'),
        'conversation_embeddings',
        ['id'],
        unique=False
    )
    op.create_index(
        op.f('ix_conversation_embeddings_thread_id'),
        'conversation_embeddings',
        ['thread_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_conversation_embeddings_created_at'),
        'conversation_embeddings',
        ['created_at'],
        unique=False
    )

    # Create IVFFlat vector similarity index for fast approximate nearest neighbor search
    # Using 100 lists as recommended for datasets up to 100K embeddings
    op.execute("""
        CREATE INDEX conversation_embeddings_vector_idx
        ON conversation_embeddings
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 100)
    """)


def downgrade() -> None:
    """
    Remove conversation_embeddings table and pgvector extension.
    """
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS conversation_embeddings_vector_idx")
    op.drop_index(op.f('ix_conversation_embeddings_created_at'), table_name='conversation_embeddings')
    op.drop_index(op.f('ix_conversation_embeddings_thread_id'), table_name='conversation_embeddings')
    op.drop_index(op.f('ix_conversation_embeddings_id'), table_name='conversation_embeddings')

    # Drop table
    op.drop_table('conversation_embeddings')

    # Drop extension (commented out to avoid breaking other potential uses)
    # op.execute("DROP EXTENSION IF EXISTS vector")
