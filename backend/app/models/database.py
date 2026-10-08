"""
SQLAlchemy database models for users, conversations, messages, and portfolio.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Date, Numeric, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class User(Base):
    """
    User model for storing user account information.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    is_active = Column(Boolean, default=True)
    country = Column(String(2))  # ISO country code (e.g., "DE", "US")
    preferred_currency = Column(String(3), default="EUR")  # Currency code (e.g., "EUR", "USD")

    # Relationships
    conversations = relationship(
        "Conversation", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"


class Conversation(Base):
    """
    Conversation model for storing chat threads.
    """

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    thread_id = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, thread_id='{self.thread_id}')>"


class Message(Base):
    """
    Message model for storing individual chat messages.
    """

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    tokens = Column(Integer)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id={self.id}, role='{self.role}', conversation_id={self.conversation_id})>"


class ConversationEmbedding(Base):
    """
    ConversationEmbedding model for storing conversation context as vector embeddings.

    Used for semantic search and RAG (Retrieval Augmented Generation) to retrieve
    relevant past conversation context using pgvector similarity search.
    """

    __tablename__ = "conversation_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    thread_id = Column(String(255), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text, nullable=False)  # Original conversation text
    embedding = Column(Vector(1536), nullable=False)  # text-embedding-3-small dimension
    meta = Column(JSONB)  # Stores tokens, tickers, timestamps, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<ConversationEmbedding(id={self.id}, thread_id='{self.thread_id}', user_id={self.user_id})>"


class PasswordResetToken(Base):
    """
    PasswordResetToken model for secure password reset functionality.

    Tokens are single-use, expire after 1 hour, and are hashed before storage.
    """

    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)  # Hashed token
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)
    is_used = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, is_used={self.is_used})>"


class OAuthAccount(Base):
    """
    OAuthAccount model for storing OAuth provider credentials.

    Links user accounts to OAuth providers (Google, GitHub, etc.)
    and stores provider access/refresh tokens.
    """

    __tablename__ = "oauth_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)  # 'google', 'github'
    provider_user_id = Column(String(255), nullable=False)  # Provider's unique user ID
    email = Column(String(255), nullable=True)  # Email from provider
    access_token = Column(Text, nullable=True)  # Provider's access token
    refresh_token = Column(Text, nullable=True)  # Provider's refresh token
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<OAuthAccount(id={self.id}, user_id={self.user_id}, provider='{self.provider}')>"


class Holding(Base):
    """
    Holding model for storing user's stock/ETF portfolio holdings.

    Each user can have one holding per ticker. The cost_basis represents the total
    purchase cost (quantity * purchase_price), not the per-share price.
    """

    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    quantity = Column(Numeric(15, 6), nullable=False)  # Supports fractional shares
    cost_basis = Column(Numeric(15, 2), nullable=False)  # Total cost (qty * price)
    purchase_date = Column(Date, nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<Holding(id={self.id}, user_id={self.user_id}, ticker='{self.ticker}', quantity={self.quantity})>"


class PortfolioSnapshot(Base):
    """
    PortfolioSnapshot model for storing daily portfolio values.

    Used for calculating Time-Weighted Return (TWR) and historical performance charts.
    """

    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    total_value = Column(Numeric(15, 2), nullable=False)
    total_cost_basis = Column(Numeric(15, 2), nullable=False)
    holdings_json = Column(JSONB, nullable=False)  # Snapshot of all holdings at this date
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<PortfolioSnapshot(id={self.id}, user_id={self.user_id}, date={self.snapshot_date}, value={self.total_value})>"


class Transaction(Base):
    """
    Transaction model for storing buy/sell/dividend/transfer transactions.

    Used for calculating Money-Weighted Return (MWR/IRR) and tracking cash flows.
    Transactions are the single source of truth for holdings.
    """

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    type = Column(String(20), nullable=False)  # 'BUY', 'SELL', 'DIVIDEND', 'TRANSFER_IN', 'TRANSFER_OUT', 'ADJUSTMENT'
    quantity = Column(Numeric(15, 6), nullable=True)  # Null for dividends
    price = Column(Numeric(15, 2), nullable=True)  # Per-share price
    fees = Column(Numeric(15, 2), nullable=False, default=0)
    total_amount = Column(Numeric(15, 2), nullable=False)  # Total cash flow
    transaction_date = Column(Date, nullable=False, index=True)
    currency = Column(String(3), nullable=False, default="USD")
    notes = Column(Text, nullable=True)
    cost_basis_known = Column(Boolean, nullable=False, default=True)  # For TRANSFER_IN with unknown cost
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Constraints (actual constraints managed by Alembic migrations)
    __table_args__ = (
        CheckConstraint(
            "type IN ('BUY', 'SELL', 'DIVIDEND', 'TRANSFER_IN', 'TRANSFER_OUT', 'ADJUSTMENT')",
            name='check_transaction_type'
        ),
        CheckConstraint(
            "(type = 'DIVIDEND' AND quantity IS NULL) OR "
            "(type IN ('BUY', 'SELL', 'TRANSFER_IN', 'TRANSFER_OUT') AND quantity > 0) OR "
            "(type = 'ADJUSTMENT' AND quantity IS NOT NULL AND quantity != 0)",
            name='check_quantity_for_trades'
        ),
        Index('idx_transactions_user_ticker', 'user_id', 'ticker'),
        Index('idx_transactions_type', 'type'),
    )

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, user_id={self.user_id}, type={self.type}, ticker='{self.ticker}', amount={self.total_amount})>"


class Dividend(Base):
    """
    Dividend model for tracking dividend payments.

    Stores dividend income from holdings for tax reporting and income tracking.
    """

    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker = Column(String(20), nullable=False, index=True)
    amount = Column(Numeric(15, 2), nullable=False)
    ex_date = Column(Date, nullable=False, index=True)  # Ex-dividend date
    pay_date = Column(Date, nullable=True)  # Payment date
    currency = Column(String(3), nullable=False, default="USD")
    status = Column(String(20), nullable=False, default="PENDING")  # 'PENDING', 'PAID'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'PAID')", name='check_dividend_status'),
    )

    # Relationships
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<Dividend(id={self.id}, user_id={self.user_id}, ticker='{self.ticker}', amount={self.amount}, status={self.status})>"
