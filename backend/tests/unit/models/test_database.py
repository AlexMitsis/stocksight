"""
Unit tests for database models.

These tests verify that database models work correctly with SQLAlchemy.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.models.database import User, Conversation, Message, ConversationEmbedding


@pytest.fixture
def db_session():
    """
    Create a fresh in-memory SQLite database for each test.
    """
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    # Cleanup
    session.close()


@pytest.mark.unit
class TestUserModel:
    """Test suite for User model."""

    def test_create_user(self, db_session):
        """Test creating a user."""
        # Given
        user = User(
            email="test@example.com",
            hashed_password="hashed_password_123",
            country="DE",
            preferred_currency="EUR",
        )

        # When
        db_session.add(user)
        db_session.commit()

        # Then
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.country == "DE"
        assert user.preferred_currency == "EUR"
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_email_unique(self, db_session):
        """Test that user email must be unique."""
        # Given
        user1 = User(email="test@example.com", hashed_password="hash1")
        user2 = User(email="test@example.com", hashed_password="hash2")

        # When
        db_session.add(user1)
        db_session.commit()

        db_session.add(user2)

        # Then
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            db_session.commit()

    def test_user_default_currency(self, db_session):
        """Test that default currency is EUR."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")

        # When
        db_session.add(user)
        db_session.commit()

        # Then
        assert user.preferred_currency == "EUR"

    def test_user_relationships(self, db_session):
        """Test user-conversation relationship."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        conversation = Conversation(user_id=user.id, thread_id="thread-123")
        db_session.add(conversation)
        db_session.commit()

        # When
        db_session.refresh(user)

        # Then
        assert len(user.conversations) == 1
        assert user.conversations[0].thread_id == "thread-123"

    def test_user_cascade_delete(self, db_session):
        """Test that deleting user cascades to conversations."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        conversation = Conversation(user_id=user.id, thread_id="thread-123")
        db_session.add(conversation)
        db_session.commit()

        # When
        db_session.delete(user)
        db_session.commit()

        # Then
        conversations = db_session.query(Conversation).all()
        assert len(conversations) == 0


@pytest.mark.unit
class TestConversationModel:
    """Test suite for Conversation model."""

    def test_create_conversation(self, db_session):
        """Test creating a conversation."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        conversation = Conversation(
            user_id=user.id, thread_id="thread-abc-123", title="My first chat"
        )

        # When
        db_session.add(conversation)
        db_session.commit()

        # Then
        assert conversation.id is not None
        assert conversation.thread_id == "thread-abc-123"
        assert conversation.title == "My first chat"
        assert conversation.user_id == user.id
        assert conversation.created_at is not None

    def test_conversation_thread_id_unique(self, db_session):
        """Test that thread_id must be unique."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        conv1 = Conversation(user_id=user.id, thread_id="thread-123")
        conv2 = Conversation(user_id=user.id, thread_id="thread-123")

        # When
        db_session.add(conv1)
        db_session.commit()

        db_session.add(conv2)

        # Then
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()

    def test_conversation_relationships(self, db_session):
        """Test conversation-message relationship."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        conversation = Conversation(user_id=user.id, thread_id="thread-123")
        db_session.add(conversation)
        db_session.commit()

        message = Message(
            conversation_id=conversation.id, role="user", content="Hello!", tokens=5
        )
        db_session.add(message)
        db_session.commit()

        # When
        db_session.refresh(conversation)

        # Then
        assert len(conversation.messages) == 1
        assert conversation.messages[0].content == "Hello!"

    def test_conversation_cascade_delete(self, db_session):
        """Test that deleting conversation cascades to messages."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        conversation = Conversation(user_id=user.id, thread_id="thread-123")
        db_session.add(conversation)
        db_session.commit()

        message = Message(
            conversation_id=conversation.id, role="user", content="Hello!"
        )
        db_session.add(message)
        db_session.commit()

        # When
        db_session.delete(conversation)
        db_session.commit()

        # Then
        messages = db_session.query(Message).all()
        assert len(messages) == 0


@pytest.mark.unit
class TestMessageModel:
    """Test suite for Message model."""

    def test_create_message(self, db_session):
        """Test creating a message."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        conversation = Conversation(user_id=user.id, thread_id="thread-123")
        db_session.add(conversation)
        db_session.commit()

        message = Message(
            conversation_id=conversation.id,
            role="user",
            content="What is AAPL stock price?",
            tokens=10,
        )

        # When
        db_session.add(message)
        db_session.commit()

        # Then
        assert message.id is not None
        assert message.conversation_id == conversation.id
        assert message.role == "user"
        assert message.content == "What is AAPL stock price?"
        assert message.tokens == 10
        assert message.timestamp is not None

    def test_message_roles(self, db_session):
        """Test different message roles."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        conversation = Conversation(user_id=user.id, thread_id="thread-123")
        db_session.add(conversation)
        db_session.commit()

        # When
        user_msg = Message(
            conversation_id=conversation.id, role="user", content="Hello"
        )
        assistant_msg = Message(
            conversation_id=conversation.id, role="assistant", content="Hi there!"
        )
        system_msg = Message(
            conversation_id=conversation.id, role="system", content="System message"
        )

        db_session.add_all([user_msg, assistant_msg, system_msg])
        db_session.commit()

        # Then
        messages = db_session.query(Message).all()
        assert len(messages) == 3
        assert {msg.role for msg in messages} == {"user", "assistant", "system"}

    def test_message_ordering(self, db_session):
        """Test messages are ordered by timestamp."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        conversation = Conversation(user_id=user.id, thread_id="thread-123")
        db_session.add(conversation)
        db_session.commit()

        msg1 = Message(conversation_id=conversation.id, role="user", content="First")
        msg2 = Message(
            conversation_id=conversation.id, role="assistant", content="Second"
        )
        msg3 = Message(conversation_id=conversation.id, role="user", content="Third")

        # When
        db_session.add_all([msg1, msg2, msg3])
        db_session.commit()

        # Then
        messages = (
            db_session.query(Message).order_by(Message.timestamp.asc()).all()
        )
        assert messages[0].content == "First"
        assert messages[1].content == "Second"
        assert messages[2].content == "Third"


@pytest.mark.unit
class TestDatabaseIntegration:
    """Integration tests for database models working together."""

    def test_full_conversation_flow(self, db_session):
        """Test complete conversation flow with user, conversation, and messages."""
        # Given
        user = User(
            email="investor@example.com",
            hashed_password="hashed_pw",
            country="US",
            preferred_currency="USD",
        )
        db_session.add(user)
        db_session.commit()

        # Create conversation
        conversation = Conversation(
            user_id=user.id,
            thread_id="conv-001",
            title="Stock Analysis Discussion",
        )
        db_session.add(conversation)
        db_session.commit()

        # Add messages
        messages_data = [
            ("user", "What's the price of AAPL?", 8),
            ("assistant", "Apple (AAPL) is trading at $175.43", 12),
            ("user", "How about MSFT?", 6),
            ("assistant", "Microsoft (MSFT) is at $380.25", 11),
        ]

        for role, content, tokens in messages_data:
            msg = Message(
                conversation_id=conversation.id,
                role=role,
                content=content,
                tokens=tokens,
            )
            db_session.add(msg)

        db_session.commit()

        # When
        retrieved_conversation = (
            db_session.query(Conversation).filter_by(thread_id="conv-001").first()
        )

        # Then
        assert retrieved_conversation is not None
        assert retrieved_conversation.user.email == "investor@example.com"
        assert len(retrieved_conversation.messages) == 4
        assert retrieved_conversation.messages[0].role == "user"
        assert retrieved_conversation.messages[1].role == "assistant"

        # Verify total tokens
        total_tokens = sum(msg.tokens for msg in retrieved_conversation.messages)
        assert total_tokens == 37


@pytest.mark.unit
class TestConversationEmbeddingModel:
    """
    Test suite for ConversationEmbedding model.

    Note: Vector similarity tests require PostgreSQL with pgvector extension.
    These tests focus on basic CRUD operations that work with SQLite.
    """

    @pytest.mark.skip(reason="Requires PostgreSQL with pgvector extension")
    def test_create_conversation_embedding(self, db_session):
        """Test creating a conversation embedding with vector."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        # Create a dummy 1536-dimensional embedding
        embedding = [0.1] * 1536

        conversation_emb = ConversationEmbedding(
            thread_id="thread-123",
            user_id=user.id,
            content="User: What's AAPL price?\nAssistant: AAPL is at $175",
            embedding=embedding,
            meta={
                "tokens": 20,
                "tickers": ["AAPL"],
                "timestamp": "2025-12-15T22:00:00Z"
            }
        )

        # When
        db_session.add(conversation_emb)
        db_session.commit()

        # Then
        assert conversation_emb.id is not None
        assert conversation_emb.thread_id == "thread-123"
        assert conversation_emb.user_id == user.id
        assert "AAPL" in conversation_emb.content
        assert len(conversation_emb.embedding) == 1536
        assert conversation_emb.meta["tokens"] == 20
        assert "AAPL" in conversation_emb.meta["tickers"]
        assert conversation_emb.created_at is not None

    @pytest.mark.skip(reason="Requires PostgreSQL with pgvector extension")
    def test_query_embeddings_by_thread(self, db_session):
        """Test querying embeddings by thread_id."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        # Create multiple embeddings for same thread
        embedding1 = [0.1] * 1536
        embedding2 = [0.2] * 1536

        emb1 = ConversationEmbedding(
            thread_id="thread-123",
            user_id=user.id,
            content="Turn 1",
            embedding=embedding1,
            meta={"turn": 1}
        )
        emb2 = ConversationEmbedding(
            thread_id="thread-123",
            user_id=user.id,
            content="Turn 2",
            embedding=embedding2,
            meta={"turn": 2}
        )

        db_session.add_all([emb1, emb2])
        db_session.commit()

        # When
        results = db_session.query(ConversationEmbedding).filter_by(
            thread_id="thread-123"
        ).all()

        # Then
        assert len(results) == 2
        assert results[0].meta["turn"] == 1
        assert results[1].meta["turn"] == 2

    @pytest.mark.skip(reason="Requires PostgreSQL with pgvector extension")
    def test_user_isolation(self, db_session):
        """Test that embeddings are properly isolated by user_id."""
        # Given
        user1 = User(email="user1@example.com", hashed_password="hash1")
        user2 = User(email="user2@example.com", hashed_password="hash2")
        db_session.add_all([user1, user2])
        db_session.commit()

        embedding = [0.1] * 1536

        # User 1's embedding
        emb1 = ConversationEmbedding(
            thread_id="thread-123",
            user_id=user1.id,
            content="User 1 conversation",
            embedding=embedding,
            meta={"user": "user1"}
        )

        # User 2's embedding (same thread_id, different user)
        emb2 = ConversationEmbedding(
            thread_id="thread-123",
            user_id=user2.id,
            content="User 2 conversation",
            embedding=embedding,
            meta={"user": "user2"}
        )

        db_session.add_all([emb1, emb2])
        db_session.commit()

        # When: Query user 1's embeddings
        user1_results = db_session.query(ConversationEmbedding).filter_by(
            thread_id="thread-123",
            user_id=user1.id
        ).all()

        # Then: Only user 1's embedding is returned
        assert len(user1_results) == 1
        assert user1_results[0].meta["user"] == "user1"

    @pytest.mark.skip(reason="Requires PostgreSQL with pgvector extension")
    def test_metadata_storage(self, db_session):
        """Test that JSONB meta stores complex data."""
        # Given
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        embedding = [0.1] * 1536

        complex_meta = {
            "user_message": "What's AAPL doing?",
            "assistant_response": "AAPL is up 2%",
            "tokens": 25,
            "tickers": ["AAPL", "MSFT", "GOOGL"],
            "timestamp": "2025-12-15T22:00:00Z",
            "relevance_score": 0.95,
            "nested": {
                "key1": "value1",
                "key2": [1, 2, 3]
            }
        }

        conversation_emb = ConversationEmbedding(
            thread_id="thread-123",
            user_id=user.id,
            content="Test content",
            embedding=embedding,
            meta=complex_meta
        )

        # When
        db_session.add(conversation_emb)
        db_session.commit()

        # Retrieve
        retrieved = db_session.query(ConversationEmbedding).filter_by(
            thread_id="thread-123"
        ).first()

        # Then: All meta preserved
        assert retrieved.meta["tokens"] == 25
        assert "AAPL" in retrieved.meta["tickers"]
        assert retrieved.meta["nested"]["key1"] == "value1"
        assert retrieved.meta["nested"]["key2"] == [1, 2, 3]

    def test_conversation_embedding_repr(self, db_session):
        """Test ConversationEmbedding __repr__ method (no pgvector required)."""
        # This test doesn't require actual database insertion with vectors
        # Just tests the repr format
        user = User(email="test@example.com", hashed_password="hash")
        db_session.add(user)
        db_session.commit()

        # Create object without committing (to avoid vector requirement)
        emb = ConversationEmbedding(
            thread_id="thread-123",
            user_id=user.id,
            content="Test content"
        )
        emb.id = 42  # Manually set for repr test

        # When
        repr_str = repr(emb)

        # Then
        assert "ConversationEmbedding" in repr_str
        assert "thread-123" in repr_str
        assert str(user.id) in repr_str
