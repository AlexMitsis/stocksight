"""
Unit tests for the context retrieval service.

These tests verify the context retrieval service correctly:
- Generates embeddings for queries
- Performs semantic search using pgvector
- Filters by thread_id and user_id
- Returns top-k relevant results
- Formats context for prompts
- Handles errors gracefully
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.context_retrieval_service import (
    ContextRetrievalService,
    get_context_retrieval_service,
)


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    with patch("app.services.context_retrieval_service.get_embedding_service") as mock:
        mock_service = MagicMock()
        mock_service.embed = AsyncMock(return_value=[0.1] * 1536)
        mock.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_db_session():
    """Mock database session for testing."""
    session = MagicMock()
    session.query = MagicMock()
    session.close = MagicMock()
    return session


@pytest.mark.unit
class TestContextRetrievalService:
    """Test cases for ContextRetrievalService."""

    def test_initialization(self, mock_embedding_service):
        """Test that ContextRetrievalService initializes correctly."""
        service = ContextRetrievalService()

        assert service.embedding_service is not None

    @pytest.mark.asyncio
    async def test_retrieve_relevant_context_success(
        self, mock_embedding_service, mock_db_session
    ):
        """Test successful retrieval of relevant context."""
        # Setup
        service = ContextRetrievalService()

        # Mock database results
        mock_result = MagicMock()
        mock_result.meta = {
            "user_message": "What's the price of AAPL?",
            "assistant_response": "Apple Inc. is trading at $175.43.",
            "timestamp": "2025-12-16T10:00:00",
            "tickers": ["AAPL"],
        }
        mock_result._distance = 0.1  # High similarity

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [(r, r._distance) for r in [mock_result]]
        mock_db_session.query.return_value = mock_query

        # Execute
        contexts = await service.retrieve_relevant_context(
            query="How is Apple doing?",
            thread_id="thread-123",
            user_id=1,
            top_k=5,
            db=mock_db_session,
        )

        # Verify
        assert len(contexts) == 1
        assert contexts[0]["user_message"] == "What's the price of AAPL?"
        assert contexts[0]["assistant_response"] == "Apple Inc. is trading at $175.43."
        assert contexts[0]["relevance_score"] > 0.8  # 1 - 0.1 = 0.9
        assert "AAPL" in contexts[0]["tickers"]
        mock_embedding_service.embed.assert_called_once()
        mock_db_session.close.assert_not_called()  # caller-provided session is not closed

    @pytest.mark.asyncio
    async def test_retrieve_relevant_context_empty_results(
        self, mock_embedding_service, mock_db_session
    ):
        """Test retrieval when no relevant context exists."""
        # Setup
        service = ContextRetrievalService()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []  # No results
        mock_db_session.query.return_value = mock_query

        # Execute
        contexts = await service.retrieve_relevant_context(
            query="Random query",
            thread_id="thread-999",
            user_id=1,
            db=mock_db_session,
        )

        # Verify
        assert contexts == []
        assert len(contexts) == 0

    @pytest.mark.asyncio
    async def test_retrieve_relevant_context_embedding_failure(
        self, mock_embedding_service, mock_db_session
    ):
        """Test that embedding failure is handled gracefully."""
        # Setup
        service = ContextRetrievalService()
        mock_embedding_service.embed.side_effect = Exception("Embedding API error")

        # Execute
        contexts = await service.retrieve_relevant_context(
            query="Test query",
            thread_id="thread-123",
            user_id=1,
            db=mock_db_session,
        )

        # Verify
        assert contexts == []  # Should return empty list
        mock_db_session.query.assert_not_called()  # Should not query database

    @pytest.mark.asyncio
    async def test_retrieve_relevant_context_database_failure(
        self, mock_embedding_service, mock_db_session
    ):
        """Test that database failure is handled gracefully."""
        # Setup
        service = ContextRetrievalService()
        mock_db_session.query.side_effect = Exception("Database connection error")

        # Execute
        contexts = await service.retrieve_relevant_context(
            query="Test query",
            thread_id="thread-123",
            user_id=1,
            db=mock_db_session,
        )

        # Verify
        assert contexts == []  # Should return empty list
        mock_db_session.close.assert_not_called()  # caller-provided session is not closed

    @pytest.mark.asyncio
    async def test_retrieve_relevant_context_respects_top_k(
        self, mock_embedding_service, mock_db_session
    ):
        """Test that top_k parameter limits results."""
        # Setup
        service = ContextRetrievalService()

        # Create 10 mock results
        mock_results = []
        for i in range(10):
            mock_result = MagicMock()
            mock_result.meta = {
                "user_message": f"Message {i}",
                "assistant_response": f"Response {i}",
                "timestamp": "2025-12-16T10:00:00",
                "tickers": [],
            }
            mock_result._distance = 0.1 * i
            mock_results.append(mock_result)

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [(r, r._distance) for r in mock_results[:3]]  # Simulate LIMIT 3
        mock_db_session.query.return_value = mock_query

        # Execute
        contexts = await service.retrieve_relevant_context(
            query="Test query",
            thread_id="thread-123",
            user_id=1,
            top_k=3,
            db=mock_db_session,
        )

        # Verify
        assert len(contexts) == 3
        mock_query.limit.assert_called_with(3)

    @pytest.mark.asyncio
    async def test_retrieve_relevant_context_filters_by_user_and_thread(
        self, mock_embedding_service, mock_db_session
    ):
        """Test that retrieval filters by thread_id and user_id."""
        # Setup
        service = ContextRetrievalService()

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db_session.query.return_value = mock_query

        # Execute
        await service.retrieve_relevant_context(
            query="Test query",
            thread_id="thread-123",
            user_id=42,
            db=mock_db_session,
        )

        # Verify filter was called (can't easily verify exact args with and_())
        mock_query.filter.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_relevant_context_calculates_relevance_scores(
        self, mock_embedding_service, mock_db_session
    ):
        """Test that relevance scores are calculated correctly."""
        # Setup
        service = ContextRetrievalService()

        # Create results with different distances
        mock_result1 = MagicMock()
        mock_result1.meta = {
            "user_message": "High relevance",
            "assistant_response": "Response 1",
            "timestamp": "2025-12-16T10:00:00",
            "tickers": [],
        }
        mock_result1._distance = 0.1  # similarity = 0.9

        mock_result2 = MagicMock()
        mock_result2.meta = {
            "user_message": "Low relevance",
            "assistant_response": "Response 2",
            "timestamp": "2025-12-16T10:00:00",
            "tickers": [],
        }
        mock_result2._distance = 0.5  # similarity = 0.5

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [(r, r._distance) for r in [mock_result1, mock_result2]]
        mock_db_session.query.return_value = mock_query

        # Execute
        contexts = await service.retrieve_relevant_context(
            query="Test query",
            thread_id="thread-123",
            user_id=1,
            db=mock_db_session,
        )

        # Verify
        assert len(contexts) == 2
        assert contexts[0]["relevance_score"] == pytest.approx(0.9, rel=0.01)
        assert contexts[1]["relevance_score"] == pytest.approx(0.5, rel=0.01)
        assert contexts[0]["relevance_score"] > contexts[1]["relevance_score"]

    def test_format_context_for_prompt_with_context(self):
        """Test formatting context into prompt string."""
        # Setup
        service = ContextRetrievalService()
        contexts = [
            {
                "user_message": "What's the price of AAPL?",
                "assistant_response": "Apple Inc. is trading at $175.43.",
                "relevance_score": 0.9,
            },
            {
                "user_message": "How about TSLA?",
                "assistant_response": "Tesla Inc. is trading at $242.17.",
                "relevance_score": 0.8,
            },
        ]

        # Execute
        formatted = service.format_context_for_prompt(contexts)

        # Verify
        assert "Relevant past conversation:" in formatted
        assert "What's the price of AAPL?" in formatted
        assert "Apple Inc. is trading at $175.43." in formatted
        assert "How about TSLA?" in formatted
        assert "Tesla Inc. is trading at $242.17." in formatted
        assert formatted.count("User:") == 2
        assert formatted.count("Assistant:") == 2

    def test_format_context_for_prompt_empty(self):
        """Test formatting with no context."""
        # Setup
        service = ContextRetrievalService()
        contexts = []

        # Execute
        formatted = service.format_context_for_prompt(contexts)

        # Verify
        assert formatted == ""

    def test_format_context_for_prompt_with_missing_fields(self):
        """Test formatting handles missing fields gracefully."""
        # Setup
        service = ContextRetrievalService()
        contexts = [
            {
                "user_message": "Question",
                # assistant_response missing
                "relevance_score": 0.9,
            },
            {
                # user_message missing
                "assistant_response": "Answer",
                "relevance_score": 0.8,
            },
        ]

        # Execute
        formatted = service.format_context_for_prompt(contexts)

        # Verify - should handle missing fields without crashing
        assert "Question" in formatted
        assert "Answer" in formatted

    def test_format_context_for_prompt_with_scores(self):
        """Test formatting context with relevance scores for debugging."""
        # Setup
        service = ContextRetrievalService()
        contexts = [
            {
                "user_message": "Test question",
                "assistant_response": "Test answer",
                "relevance_score": 0.92,
            }
        ]

        # Execute
        formatted = service.format_context_for_prompt_with_scores(contexts)

        # Verify
        assert "relevance: 0.920" in formatted
        assert "Test question" in formatted
        assert "Test answer" in formatted
        assert "[Context 1" in formatted

    def test_format_context_for_prompt_with_scores_empty(self):
        """Test formatting with scores when no context."""
        # Setup
        service = ContextRetrievalService()
        contexts = []

        # Execute
        formatted = service.format_context_for_prompt_with_scores(contexts)

        # Verify
        assert formatted == ""

    @pytest.mark.asyncio
    async def test_retrieve_relevant_context_handles_missing_metadata(
        self, mock_embedding_service, mock_db_session
    ):
        """Test that retrieval handles missing metadata fields gracefully."""
        # Setup
        service = ContextRetrievalService()

        # Mock result with incomplete metadata
        mock_result = MagicMock()
        mock_result.meta = {
            "user_message": "Test",
            # Missing other fields
        }
        mock_result._distance = 0.2

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [(r, r._distance) for r in [mock_result]]
        mock_db_session.query.return_value = mock_query

        # Execute
        contexts = await service.retrieve_relevant_context(
            query="Test query",
            thread_id="thread-123",
            user_id=1,
            db=mock_db_session,
        )

        # Verify - should handle missing fields with defaults
        assert len(contexts) == 1
        assert contexts[0]["user_message"] == "Test"
        assert contexts[0]["assistant_response"] == ""  # Default
        assert contexts[0]["timestamp"] == ""  # Default
        assert contexts[0]["tickers"] == []  # Default


@pytest.mark.unit
class TestGetContextRetrievalService:
    """Test cases for get_context_retrieval_service singleton."""

    def test_singleton_returns_same_instance(self):
        """Test that get_context_retrieval_service returns the same instance."""
        # Reset the global instance
        import app.services.context_retrieval_service as module

        module._context_retrieval_service = None

        # Get instances
        with patch("app.services.context_retrieval_service.get_embedding_service"):
            service1 = get_context_retrieval_service()
            service2 = get_context_retrieval_service()

            # Verify they're the same instance
            assert service1 is service2

    def test_singleton_creates_on_first_call(self):
        """Test that singleton creates instance on first call."""
        # Reset the global instance
        import app.services.context_retrieval_service as module

        module._context_retrieval_service = None

        with patch("app.services.context_retrieval_service.get_embedding_service"):
            # First call should create instance
            assert module._context_retrieval_service is None
            service = get_context_retrieval_service()
            assert module._context_retrieval_service is not None
            assert service is module._context_retrieval_service
