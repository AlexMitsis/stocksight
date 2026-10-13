"""
Unit tests for the context storage service.

These tests verify the context storage service correctly:
- Generates embeddings for conversation turns
- Stores conversations in PostgreSQL with pgvector
- Extracts metadata (tickers, timestamps)
- Handles errors gracefully
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.context_storage_service import (
    ContextStorageService,
    get_context_storage_service,
)
from app.models.database import ConversationEmbedding


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    with patch("app.services.context_storage_service.get_embedding_service") as mock:
        mock_service = MagicMock()
        mock_service.embed = AsyncMock(return_value=[0.1] * 1536)
        mock.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    session = MagicMock()
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.close = MagicMock()
    session.query = MagicMock()
    return session


@pytest.mark.unit
class TestContextStorageService:
    """Test cases for ContextStorageService."""

    def test_initialization(self, mock_embedding_service):
        """Test that ContextStorageService initializes correctly."""
        service = ContextStorageService()

        assert service.embedding_service is not None

    @pytest.mark.asyncio
    async def test_store_conversation_turn_success(
        self, mock_embedding_service, mock_db_session
    ):
        """Test successful storage of conversation turn."""
        # Setup
        service = ContextStorageService()
        thread_id = "thread-123"
        user_id = 1
        user_message = "What's the price of AAPL?"
        assistant_response = "Apple Inc. (AAPL) is trading at $175.43."
        tokens = 150

        # Execute
        result = await service.store_conversation_turn(
            thread_id=thread_id,
            user_id=user_id,
            user_message=user_message,
            assistant_response=assistant_response,
            tokens=tokens,
            db=mock_db_session,
        )

        # Verify
        assert result is True
        mock_embedding_service.embed.assert_called_once()
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.close.assert_not_called()  # caller-provided session is not closed

    @pytest.mark.asyncio
    async def test_store_conversation_turn_embedding_failure(
        self, mock_embedding_service, mock_db_session
    ):
        """Test that embedding failure is handled gracefully."""
        # Setup
        service = ContextStorageService()
        mock_embedding_service.embed.side_effect = Exception("Embedding API error")

        # Execute
        result = await service.store_conversation_turn(
            thread_id="thread-123",
            user_id=1,
            user_message="Test message",
            assistant_response="Test response",
            tokens=100,
            db=mock_db_session,
        )

        # Verify
        assert result is False  # Should return False on embedding failure
        mock_db_session.add.assert_not_called()  # Should not try to store
        mock_db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_store_conversation_turn_database_failure(
        self, mock_embedding_service, mock_db_session
    ):
        """Test that database failure is handled gracefully."""
        # Setup
        service = ContextStorageService()
        mock_db_session.commit.side_effect = Exception("Database error")

        # Execute
        result = await service.store_conversation_turn(
            thread_id="thread-123",
            user_id=1,
            user_message="Test message",
            assistant_response="Test response",
            tokens=100,
            db=mock_db_session,
        )

        # Verify
        assert result is False  # Should return False on database failure
        mock_db_session.rollback.assert_called_once()
        mock_db_session.close.assert_not_called()  # caller-provided session is not closed

    @pytest.mark.asyncio
    async def test_store_conversation_turn_creates_correct_metadata(
        self, mock_embedding_service, mock_db_session
    ):
        """Test that metadata is correctly created."""
        # Setup
        service = ContextStorageService()
        user_message = "What about TSLA and NVDA?"
        assistant_response = "Tesla (TSLA) and NVIDIA (NVDA) are both up today."
        tokens = 200

        # Capture the added record
        added_record = None

        def capture_add(record):
            nonlocal added_record
            added_record = record

        mock_db_session.add.side_effect = capture_add

        # Execute
        await service.store_conversation_turn(
            thread_id="thread-123",
            user_id=1,
            user_message=user_message,
            assistant_response=assistant_response,
            tokens=tokens,
            db=mock_db_session,
        )

        # Verify
        assert added_record is not None
        assert isinstance(added_record, ConversationEmbedding)
        assert added_record.thread_id == "thread-123"
        assert added_record.user_id == 1
        assert "User:" in added_record.content
        assert "Assistant:" in added_record.content
        assert user_message in added_record.content
        assert assistant_response in added_record.content

        # Check metadata
        meta = added_record.meta
        assert meta["user_message"] == user_message
        assert meta["assistant_response"] == assistant_response
        assert meta["tokens"] == tokens
        assert "TSLA" in meta["tickers"]
        assert "NVDA" in meta["tickers"]
        assert "timestamp" in meta
        assert "message_length" in meta

    def test_extract_tickers_finds_valid_tickers(self):
        """Test that ticker extraction finds valid ticker symbols."""
        # Setup
        service = ContextStorageService()
        text = "AAPL is up 5% while TSLA and NVDA are down. MSFT remains flat."

        # Execute
        tickers = service._extract_tickers(text)

        # Verify
        assert "AAPL" in tickers
        assert "TSLA" in tickers
        assert "NVDA" in tickers
        assert "MSFT" in tickers
        assert len(tickers) == 4

    def test_extract_tickers_filters_common_words(self):
        """Test that common words are filtered out."""
        # Setup
        service = ContextStorageService()
        text = "I think AI is the future. A new CEO was appointed in the US."

        # Execute
        tickers = service._extract_tickers(text)

        # Verify
        # Common words like I, A, AI, CEO, US should be filtered
        assert "I" not in tickers
        assert "A" not in tickers
        assert "AI" not in tickers
        assert "CEO" not in tickers
        assert "US" not in tickers

    def test_extract_tickers_removes_duplicates(self):
        """Test that duplicate tickers are removed."""
        # Setup
        service = ContextStorageService()
        text = "AAPL is mentioned. AAPL again. And AAPL once more."

        # Execute
        tickers = service._extract_tickers(text)

        # Verify
        assert tickers.count("AAPL") == 1  # Should appear only once
        assert len(tickers) == 1

    def test_extract_tickers_handles_mixed_case(self):
        """Test that only uppercase ticker symbols are extracted."""
        # Setup
        service = ContextStorageService()
        text = "Apple (AAPL) is different from aapl or Aapl."

        # Execute
        tickers = service._extract_tickers(text)

        # Verify
        assert "AAPL" in tickers
        assert "aapl" not in tickers
        assert "Aapl" not in tickers

    def test_extract_tickers_respects_length_limit(self):
        """Test that only 1-5 character symbols are extracted."""
        # Setup
        service = ContextStorageService()
        text = "A is 1 char, ABCDE is 5 chars, ABCDEF is 6 chars (invalid)."

        # Execute
        tickers = service._extract_tickers(text)

        # Verify
        assert "ABCDE" in tickers  # 5 chars is valid
        assert "ABCDEF" not in tickers  # 6 chars is invalid
        # 'A' would be filtered as common word

    @pytest.mark.asyncio
    async def test_get_conversation_history_success(self, mock_db_session):
        """Test successful retrieval of conversation history."""
        # Setup
        service = ContextStorageService()
        mock_records = [
            MagicMock(
                id=1,
                thread_id="thread-123",
                content="User: msg1\nAssistant: resp1",
            ),
            MagicMock(
                id=2,
                thread_id="thread-123",
                content="User: msg2\nAssistant: resp2",
            ),
        ]

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_records
        mock_db_session.query.return_value = mock_query

        # Execute
        result = await service.get_conversation_history(
            thread_id="thread-123", user_id=1, limit=10, db=mock_db_session
        )

        # Verify
        assert len(result) == 2
        assert result == mock_records
        mock_db_session.close.assert_not_called()  # caller-provided session is not closed

    @pytest.mark.asyncio
    async def test_get_conversation_history_empty_result(self, mock_db_session):
        """Test that empty history is handled correctly."""
        # Setup
        service = ContextStorageService()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query

        # Execute
        result = await service.get_conversation_history(
            thread_id="thread-999", user_id=1, limit=10, db=mock_db_session
        )

        # Verify
        assert result == []
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_conversation_history_database_error(self, mock_db_session):
        """Test that database errors are handled gracefully."""
        # Setup
        service = ContextStorageService()
        mock_db_session.query.side_effect = Exception("Database connection error")

        # Execute
        result = await service.get_conversation_history(
            thread_id="thread-123", user_id=1, limit=10, db=mock_db_session
        )

        # Verify
        assert result == []  # Should return empty list on error
        mock_db_session.close.assert_not_called()  # caller-provided session is not closed


@pytest.mark.unit
class TestGetContextStorageService:
    """Test cases for get_context_storage_service singleton."""

    def test_singleton_returns_same_instance(self):
        """Test that get_context_storage_service returns the same instance."""
        # Reset the global instance
        import app.services.context_storage_service as module

        module._context_storage_service = None

        # Get instances
        with patch("app.services.context_storage_service.get_embedding_service"):
            service1 = get_context_storage_service()
            service2 = get_context_storage_service()

            # Verify they're the same instance
            assert service1 is service2

    def test_singleton_creates_on_first_call(self):
        """Test that singleton creates instance on first call."""
        # Reset the global instance
        import app.services.context_storage_service as module

        module._context_storage_service = None

        with patch("app.services.context_storage_service.get_embedding_service"):
            # First call should create instance
            assert module._context_storage_service is None
            service = get_context_storage_service()
            assert module._context_storage_service is not None
            assert service is module._context_storage_service
