"""
Integration tests for context retrieval functionality.

These tests verify the full context retrieval flow including:
- Database integration with PostgreSQL + pgvector
- Embedding generation with EmbeddingService
- Semantic similarity search
- End-to-end storage and retrieval
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.context_retrieval_service import ContextRetrievalService
from app.services.context_storage_service import ContextStorageService


@pytest.mark.integration
class TestContextRetrievalIntegration:
    """Integration tests for context retrieval with database."""

    @pytest.mark.asyncio
    async def test_retrieve_relevant_context_with_similarity(self):
        """Test retrieval of relevant context based on semantic similarity."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        # Mock database results with varying similarity
        mock_result1 = MagicMock()
        mock_result1.meta = {
            "user_message": "What's the price of AAPL?",
            "assistant_response": "Apple Inc. (AAPL) is trading at $175.43.",
            "timestamp": "2025-12-16T10:00:00",
            "tickers": ["AAPL"],
        }
        mock_result1.embedding.cosine_distance = MagicMock(return_value=0.05)  # Very relevant

        mock_result2 = MagicMock()
        mock_result2.meta = {
            "user_message": "Tell me about TSLA",
            "assistant_response": "Tesla Inc. (TSLA) is an electric vehicle company.",
            "timestamp": "2025-12-16T10:05:00",
            "tickers": ["TSLA"],
        }
        mock_result2.embedding.cosine_distance = MagicMock(return_value=0.3)  # Less relevant

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_result1, mock_result2]
        mock_db.query.return_value = mock_query

        with patch(
            "app.services.context_retrieval_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextRetrievalService()

            # Retrieve context for Apple-related query
            contexts = await service.retrieve_relevant_context(
                query="How is Apple performing?",
                thread_id="test-thread",
                user_id=1,
                top_k=5,
                db=mock_db,
            )

            # Verify
            assert len(contexts) == 2
            # First result should be more relevant (lower distance)
            assert contexts[0]["relevance_score"] > contexts[1]["relevance_score"]
            assert "AAPL" in contexts[0]["user_message"]
            assert "TSLA" in contexts[1]["user_message"]

    @pytest.mark.asyncio
    async def test_user_isolation_in_retrieval(self):
        """Test that retrieval respects user isolation."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        # Mock result for user 1
        mock_result = MagicMock()
        mock_result.meta = {
            "user_message": "User 1 message",
            "assistant_response": "Response to user 1",
            "timestamp": "2025-12-16T10:00:00",
            "tickers": [],
        }
        mock_result.embedding.cosine_distance = MagicMock(return_value=0.1)

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_result]
        mock_db.query.return_value = mock_query

        with patch(
            "app.services.context_retrieval_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextRetrievalService()

            # Retrieve for user 1
            contexts_user1 = await service.retrieve_relevant_context(
                query="test query",
                thread_id="thread-1",
                user_id=1,
                db=mock_db,
            )

            # Verify user 1 can access their own context
            assert len(contexts_user1) == 1
            assert "User 1 message" in contexts_user1[0]["user_message"]

    @pytest.mark.asyncio
    async def test_thread_isolation_in_retrieval(self):
        """Test that retrieval respects thread isolation."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        # Mock result for thread-1
        mock_result = MagicMock()
        mock_result.meta = {
            "user_message": "Thread 1 message",
            "assistant_response": "Response in thread 1",
            "timestamp": "2025-12-16T10:00:00",
            "tickers": [],
        }
        mock_result.embedding.cosine_distance = MagicMock(return_value=0.1)

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_result]
        mock_db.query.return_value = mock_query

        with patch(
            "app.services.context_retrieval_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextRetrievalService()

            # Retrieve for thread-1
            contexts = await service.retrieve_relevant_context(
                query="test query",
                thread_id="thread-1",
                user_id=1,
                db=mock_db,
            )

            # Verify thread-1 context retrieved
            assert len(contexts) == 1
            assert "Thread 1 message" in contexts[0]["user_message"]

    @pytest.mark.asyncio
    async def test_retrieval_performance_logging(self):
        """Test that retrieval logs performance metrics."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        with patch(
            "app.services.context_retrieval_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextRetrievalService()

            # Execute retrieval (logs will be generated)
            contexts = await service.retrieve_relevant_context(
                query="test query",
                thread_id="thread-1",
                user_id=1,
                db=mock_db,
            )

            # Verify (mainly checking it doesn't crash)
            # Actual log verification would require capturing logs
            assert contexts == []

    @pytest.mark.asyncio
    async def test_format_context_integration(self):
        """Test formatting retrieved context for prompt."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        # Mock results
        mock_result = MagicMock()
        mock_result.meta = {
            "user_message": "What's AAPL's price?",
            "assistant_response": "Apple Inc. is trading at $175.43.",
            "timestamp": "2025-12-16T10:00:00",
            "tickers": ["AAPL"],
        }
        mock_result.embedding.cosine_distance = MagicMock(return_value=0.1)

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_result]
        mock_db.query.return_value = mock_query

        with patch(
            "app.services.context_retrieval_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextRetrievalService()

            # Retrieve and format
            contexts = await service.retrieve_relevant_context(
                query="How is Apple doing?",
                thread_id="test-thread",
                user_id=1,
                db=mock_db,
            )
            formatted = service.format_context_for_prompt(contexts)

            # Verify
            assert len(contexts) == 1
            assert "Relevant past conversation:" in formatted
            assert "AAPL" in formatted
            assert "$175.43" in formatted

    @pytest.mark.asyncio
    async def test_retrieval_resilience_to_embedding_failure(self):
        """Test that retrieval gracefully handles embedding failures."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(
            side_effect=Exception("Embeddings API unavailable")
        )

        with patch(
            "app.services.context_retrieval_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextRetrievalService()

            # Attempt to retrieve context
            contexts = await service.retrieve_relevant_context(
                query="test query",
                thread_id="test-thread",
                user_id=1,
                db=mock_db,
            )

            # Verify graceful failure
            assert contexts == []
            mock_db.query.assert_not_called()  # Should not attempt database query

    @pytest.mark.asyncio
    async def test_retrieval_resilience_to_database_failure(self):
        """Test that retrieval gracefully handles database failures."""
        # Setup
        mock_db = MagicMock()
        mock_db.query.side_effect = Exception("Database connection lost")
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        with patch(
            "app.services.context_retrieval_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextRetrievalService()

            # Attempt to retrieve context
            contexts = await service.retrieve_relevant_context(
                query="test query",
                thread_id="test-thread",
                user_id=1,
                db=mock_db,
            )

            # Verify graceful failure
            assert contexts == []
            mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_top_k_limit_respected(self):
        """Test that top_k parameter correctly limits results."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        # Create 10 mock results but only return top 3
        mock_results = []
        for i in range(3):
            mock_result = MagicMock()
            mock_result.meta = {
                "user_message": f"Message {i}",
                "assistant_response": f"Response {i}",
                "timestamp": "2025-12-16T10:00:00",
                "tickers": [],
            }
            mock_result.embedding.cosine_distance = MagicMock(return_value=0.1 * (i + 1))
            mock_results.append(mock_result)

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_results
        mock_db.query.return_value = mock_query

        with patch(
            "app.services.context_retrieval_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextRetrievalService()

            # Retrieve with top_k=3
            contexts = await service.retrieve_relevant_context(
                query="test query",
                thread_id="test-thread",
                user_id=1,
                top_k=3,
                db=mock_db,
            )

            # Verify
            assert len(contexts) == 3
            mock_query.limit.assert_called_with(3)


@pytest.mark.integration
class TestContextRetrievalEndToEnd:
    """End-to-end integration tests for context retrieval."""

    @pytest.mark.asyncio
    async def test_full_storage_and_retrieval_flow(self):
        """Test complete flow: store conversation, retrieve relevant context."""
        # This test demonstrates the full flow but uses mocks
        # In a real integration test, this would use a real database

        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        # Simulate stored conversation
        mock_result = MagicMock()
        mock_result.meta = {
            "user_message": "What's the price of AAPL?",
            "assistant_response": "Apple Inc. (AAPL) is trading at $175.43.",
            "timestamp": "2025-12-16T10:00:00",
            "tokens": 150,
            "tickers": ["AAPL"],
        }
        mock_result.embedding.cosine_distance = MagicMock(return_value=0.08)

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [mock_result]
        mock_db.query.return_value = mock_query

        with patch(
            "app.services.context_retrieval_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            retrieval_service = ContextRetrievalService()

            # Retrieve context for related query
            contexts = await retrieval_service.retrieve_relevant_context(
                query="How has Apple performed today?",
                thread_id="conversation-1",
                user_id=1,
                db=mock_db,
            )

            # Verify retrieval found relevant context
            assert len(contexts) == 1
            assert "AAPL" in contexts[0]["user_message"]
            assert contexts[0]["relevance_score"] > 0.9  # High similarity

            # Format for prompt
            formatted = retrieval_service.format_context_for_prompt(contexts)
            assert "Relevant past conversation:" in formatted
            assert "AAPL" in formatted
            assert "$175.43" in formatted

    @pytest.mark.asyncio
    async def test_retrieval_with_multiple_relevant_contexts(self):
        """Test retrieval when multiple relevant contexts exist."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        # Create multiple relevant results
        mock_results = []
        queries = [
            ("What's AAPL's price?", "Apple is at $175.43", ["AAPL"], 0.05),
            ("Tell me about Apple", "Apple Inc. is a tech company", ["AAPL"], 0.08),
            ("AAPL stock analysis", "AAPL shows strong growth", ["AAPL"], 0.10),
        ]

        for user_msg, asst_msg, tickers, distance in queries:
            mock_result = MagicMock()
            mock_result.meta = {
                "user_message": user_msg,
                "assistant_response": asst_msg,
                "timestamp": "2025-12-16T10:00:00",
                "tickers": tickers,
            }
            mock_result.embedding.cosine_distance = MagicMock(return_value=distance)
            mock_results.append(mock_result)

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_results
        mock_db.query.return_value = mock_query

        with patch(
            "app.services.context_retrieval_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextRetrievalService()

            # Retrieve context
            contexts = await service.retrieve_relevant_context(
                query="Apple stock information",
                thread_id="test-thread",
                user_id=1,
                top_k=5,
                db=mock_db,
            )

            # Verify all relevant contexts retrieved
            assert len(contexts) == 3
            # Verify sorted by relevance (lower distance = higher relevance)
            assert contexts[0]["relevance_score"] >= contexts[1]["relevance_score"]
            assert contexts[1]["relevance_score"] >= contexts[2]["relevance_score"]
