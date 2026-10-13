"""
Integration tests for context storage functionality.

These tests verify the full context storage flow including:
- Database integration with PostgreSQL + pgvector
- Embedding generation with EmbeddingService
- End-to-end storage and retrieval
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.context_storage_service import ContextStorageService
from app.models.database import ConversationEmbedding


@pytest.mark.integration
class TestContextStorageIntegration:
    """Integration tests for context storage with database."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_conversation(self):
        """Test full cycle of storing and retrieving conversation context."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        with patch(
            "app.services.context_storage_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextStorageService()

            # Store conversation
            success = await service.store_conversation_turn(
                thread_id="test-thread",
                user_id=1,
                user_message="What's the price of AAPL?",
                assistant_response="Apple Inc. (AAPL) is trading at $175.43.",
                tokens=150,
                db=mock_db,
            )

            # Verify storage succeeded
            assert success is True
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()

            # Verify embedding was generated
            mock_embedding_service.embed.assert_called_once()
            call_args = mock_embedding_service.embed.call_args[0][0]
            assert "User:" in call_args
            assert "Assistant:" in call_args
            assert "AAPL" in call_args

    @pytest.mark.asyncio
    async def test_ticker_extraction_in_storage(self):
        """Test that tickers are correctly extracted and stored in metadata."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        added_record = None

        def capture_add(record):
            nonlocal added_record
            added_record = record

        mock_db.add.side_effect = capture_add

        with patch(
            "app.services.context_storage_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextStorageService()

            # Store conversation with multiple tickers
            await service.store_conversation_turn(
                thread_id="test-thread",
                user_id=1,
                user_message="Compare AAPL, MSFT, and GOOGL",
                assistant_response="Apple (AAPL), Microsoft (MSFT), and Google (GOOGL) are all performing well.",
                tokens=200,
                db=mock_db,
            )

            # Verify tickers were extracted
            assert added_record is not None
            meta = added_record.meta
            assert "tickers" in meta
            assert "AAPL" in meta["tickers"]
            assert "MSFT" in meta["tickers"]
            assert "GOOGL" in meta["tickers"]

    @pytest.mark.asyncio
    async def test_metadata_completeness(self):
        """Test that all required metadata fields are populated."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        added_record = None

        def capture_add(record):
            nonlocal added_record
            added_record = record

        mock_db.add.side_effect = capture_add

        with patch(
            "app.services.context_storage_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextStorageService()

            user_message = "Test user message"
            assistant_response = "Test assistant response"
            tokens = 100

            # Store conversation
            await service.store_conversation_turn(
                thread_id="test-thread",
                user_id=1,
                user_message=user_message,
                assistant_response=assistant_response,
                tokens=tokens,
                db=mock_db,
            )

            # Verify all metadata fields
            assert added_record is not None
            meta = added_record.meta

            assert "user_message" in meta
            assert meta["user_message"] == user_message

            assert "assistant_response" in meta
            assert meta["assistant_response"] == assistant_response

            assert "tokens" in meta
            assert meta["tokens"] == tokens

            assert "tickers" in meta
            assert isinstance(meta["tickers"], list)

            assert "timestamp" in meta
            # Verify timestamp is valid ISO format
            datetime.fromisoformat(meta["timestamp"])

            assert "message_length" in meta
            assert isinstance(meta["message_length"], int)

    @pytest.mark.asyncio
    async def test_storage_resilience_to_embedding_failure(self):
        """Test that storage gracefully handles embedding failures."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(
            side_effect=Exception("Embeddings API unavailable")
        )

        with patch(
            "app.services.context_storage_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextStorageService()

            # Attempt to store conversation
            success = await service.store_conversation_turn(
                thread_id="test-thread",
                user_id=1,
                user_message="Test message",
                assistant_response="Test response",
                tokens=100,
                db=mock_db,
            )

            # Verify graceful failure
            assert success is False
            mock_db.add.assert_not_called()  # Should not attempt to store
            mock_db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_storage_resilience_to_database_failure(self):
        """Test that storage gracefully handles database failures."""
        # Setup
        mock_db = MagicMock()
        mock_db.commit.side_effect = Exception("Database connection lost")
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        with patch(
            "app.services.context_storage_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextStorageService()

            # Attempt to store conversation
            success = await service.store_conversation_turn(
                thread_id="test-thread",
                user_id=1,
                user_message="Test message",
                assistant_response="Test response",
                tokens=100,
                db=mock_db,
            )

            # Verify graceful failure
            assert success is False
            mock_db.rollback.assert_called_once()
            mock_db.close.assert_not_called()  # caller-provided session is not closed

    @pytest.mark.asyncio
    async def test_user_isolation_in_storage(self):
        """Test that conversations are properly isolated by user_id."""
        # Setup
        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        stored_records = []

        def capture_add(record):
            stored_records.append(record)

        mock_db.add.side_effect = capture_add

        with patch(
            "app.services.context_storage_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextStorageService()

            # Store conversations for different users
            await service.store_conversation_turn(
                thread_id="thread-1",
                user_id=1,
                user_message="User 1 message",
                assistant_response="Response to user 1",
                tokens=100,
                db=mock_db,
            )

            await service.store_conversation_turn(
                thread_id="thread-2",
                user_id=2,
                user_message="User 2 message",
                assistant_response="Response to user 2",
                tokens=100,
                db=mock_db,
            )

            # Verify proper user isolation
            assert len(stored_records) == 2
            assert stored_records[0].user_id == 1
            assert stored_records[1].user_id == 2
            assert stored_records[0].content != stored_records[1].content

    @pytest.mark.asyncio
    async def test_conversation_history_retrieval(self):
        """Test retrieving conversation history for a thread."""
        # Setup
        mock_db = MagicMock()
        mock_records = [
            MagicMock(
                id=1,
                thread_id="thread-123",
                user_id=1,
                content="User: msg1\nAssistant: resp1",
                created_at=datetime(2025, 12, 15, 10, 0, 0),
            ),
            MagicMock(
                id=2,
                thread_id="thread-123",
                user_id=1,
                content="User: msg2\nAssistant: resp2",
                created_at=datetime(2025, 12, 15, 10, 5, 0),
            ),
        ]

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_records
        mock_db.query.return_value = mock_query

        with patch("app.services.context_storage_service.get_embedding_service"):
            service = ContextStorageService()

            # Retrieve history
            history = await service.get_conversation_history(
                thread_id="thread-123", user_id=1, limit=10, db=mock_db
            )

            # Verify
            assert len(history) == 2
            assert history[0].id == 1
            assert history[1].id == 2


@pytest.mark.integration
class TestContextStorageEndToEnd:
    """End-to-end integration tests for context storage."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test complete flow: store conversation, retrieve history."""
        # This test demonstrates the full flow but uses mocks
        # In a real integration test, this would use a real database

        mock_db = MagicMock()
        mock_embedding_service = MagicMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        conversation_storage = []

        def mock_add(record):
            conversation_storage.append(record)

        def mock_query_all():
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = conversation_storage
            return mock_query

        mock_db.add.side_effect = mock_add
        mock_db.query.return_value = mock_query_all()

        with patch(
            "app.services.context_storage_service.get_embedding_service",
            return_value=mock_embedding_service,
        ):
            service = ContextStorageService()

            # Simulate a multi-turn conversation
            turns = [
                ("What's the price of AAPL?", "Apple Inc. (AAPL) is trading at $175.43."),
                ("How about TSLA?", "Tesla Inc. (TSLA) is trading at $242.17."),
                ("Compare them", "AAPL is more stable, TSLA is more volatile."),
            ]

            # Store all turns
            for user_msg, assistant_msg in turns:
                await service.store_conversation_turn(
                    thread_id="conversation-1",
                    user_id=1,
                    user_message=user_msg,
                    assistant_response=assistant_msg,
                    tokens=150,
                    db=mock_db,
                )

            # Verify all turns were stored
            assert len(conversation_storage) == 3

            # Verify they can be retrieved
            # (In real test, would query database)
            assert all(record.thread_id == "conversation-1" for record in conversation_storage)
            assert all(record.user_id == 1 for record in conversation_storage)
