"""
Integration tests for RAG (Retrieval-Augmented Generation) functionality in chat endpoint.

Tests the complete flow:
1. Store conversation context with embeddings
2. Retrieve relevant context during chat
3. Include context in agent prompt
4. Store new conversation turn
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.context_storage_service import get_context_storage_service
from app.services.context_retrieval_service import get_context_retrieval_service
from app.models.database import ConversationEmbedding


@pytest.mark.integration
class TestRAGIntegration:
    """Test RAG integration in chat endpoint."""

    @pytest.mark.asyncio
    async def test_rag_retrieves_relevant_context(
        self, db_session, fastapi_test_client, mock_agent
    ):
        """
        Test that chat endpoint retrieves relevant context from pgvector.

        Flow:
        1. Store a conversation about AAPL
        2. Make a new chat request about Apple
        3. Verify that the context was retrieved (check logs or mock calls)
        """
        # Given: Store a previous conversation about AAPL
        thread_id = "test-rag-thread-1"
        user_id = 1

        context_storage = get_context_storage_service()
        success = await context_storage.store_conversation_turn(
            thread_id=thread_id,
            user_id=user_id,
            user_message="What's AAPL's current price?",
            assistant_response="Apple Inc (AAPL) is currently trading at $175.43.",
            tokens=50,
        )
        assert success, "Failed to store context"

        # Wait briefly for async storage
        await asyncio.sleep(0.5)

        # Verify it was stored
        stored = db_session.query(ConversationEmbedding).filter_by(
            thread_id=thread_id
        ).first()
        assert stored is not None
        assert len(stored.embedding) == 1536

        # When: Make a chat request with related query
        request = {
            "prompt": {
                "content": "What did we discuss about Apple?",
                "id": "2",
                "role": "user"
            },
            "threadId": thread_id,
            "responseId": "resp2",
        }

        response = fastapi_test_client.post("/api/chat", json=request)

        # Then: Should succeed
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rag_filters_by_thread_id(
        self, db_session, fastapi_test_client, mock_agent
    ):
        """
        Test that RAG only retrieves context from the same thread.
        """
        # Given: Store conversations in different threads
        context_storage = get_context_storage_service()

        # Thread 1: About AAPL
        await context_storage.store_conversation_turn(
            thread_id="thread-aapl",
            user_id=1,
            user_message="What's AAPL's price?",
            assistant_response="AAPL is at $175.",
            tokens=20,
        )

        # Thread 2: About MSFT
        await context_storage.store_conversation_turn(
            thread_id="thread-msft",
            user_id=1,
            user_message="What's MSFT's price?",
            assistant_response="MSFT is at $380.",
            tokens=20,
        )

        await asyncio.sleep(0.5)

        # When: Query in thread 1
        context_retrieval = get_context_retrieval_service()
        contexts = await context_retrieval.retrieve_relevant_context(
            query="What stock did we discuss?",
            thread_id="thread-aapl",
            user_id=1,
            top_k=5,
        )

        # Then: Should only retrieve AAPL context
        assert len(contexts) >= 1
        context_text = " ".join(c["user_message"] for c in contexts)
        assert "AAPL" in context_text
        assert "MSFT" not in context_text

    @pytest.mark.asyncio
    async def test_rag_filters_by_user_id(self, db_session):
        """
        Test that RAG enforces user isolation.
        """
        # Given: Different users discussing in the same thread
        context_storage = get_context_storage_service()
        thread_id = "shared-thread"

        # User 1's conversation
        await context_storage.store_conversation_turn(
            thread_id=thread_id,
            user_id=1,
            user_message="My secret stock pick is SECRETCO",
            assistant_response="Noted.",
            tokens=10,
        )

        # User 2's conversation
        await context_storage.store_conversation_turn(
            thread_id=thread_id,
            user_id=2,
            user_message="What's AAPL's price?",
            assistant_response="AAPL is at $175.",
            tokens=15,
        )

        await asyncio.sleep(0.5)

        # When: User 2 queries the thread
        context_retrieval = get_context_retrieval_service()
        contexts = await context_retrieval.retrieve_relevant_context(
            query="What stocks did we discuss?",
            thread_id=thread_id,
            user_id=2,
            top_k=5,
        )

        # Then: User 2 should NOT see User 1's context
        context_text = " ".join(
            c["user_message"] + " " + c["assistant_response"] for c in contexts
        )
        assert "SECRETCO" not in context_text
        assert "AAPL" in context_text or len(contexts) >= 1

    @pytest.mark.asyncio
    async def test_rag_handles_no_context(self, fastapi_test_client, mock_agent):
        """
        Test that chat works normally when no relevant context exists.
        """
        # Given: New thread with no history
        request = {
            "prompt": {
                "content": "What's AAPL's price?",
                "id": "1",
                "role": "user"
            },
            "threadId": "brand-new-thread",
            "responseId": "resp1",
        }

        # When: Make chat request
        response = fastapi_test_client.post("/api/chat", json=request)

        # Then: Should still work
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rag_graceful_fallback_on_retrieval_error(
        self, fastapi_test_client, mocker, mock_agent
    ):
        """
        Test that chat continues to work if context retrieval fails.
        """
        # Given: Mock context retrieval to fail
        mock_retrieval = AsyncMock(side_effect=Exception("Database connection failed"))
        mocker.patch(
            "app.routers.chat.get_context_retrieval_service",
            return_value=MagicMock(retrieve_relevant_context=mock_retrieval)
        )

        request = {
            "prompt": {
                "content": "What's AAPL's price?",
                "id": "1",
                "role": "user"
            },
            "threadId": "test-thread",
            "responseId": "resp1",
        }

        # When: Make chat request
        response = fastapi_test_client.post("/api/chat", json=request)

        # Then: Should still work (graceful degradation)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rag_token_counting_includes_context(
        self, db_session, fastapi_test_client, mocker, mock_agent
    ):
        """
        Test that token counting includes the retrieved context.
        """
        # Given: Store a conversation
        thread_id = "test-token-counting"
        context_storage = get_context_storage_service()
        await context_storage.store_conversation_turn(
            thread_id=thread_id,
            user_id=1,
            user_message="Previous message about stocks",
            assistant_response="Previous response about stocks",
            tokens=30,
        )

        await asyncio.sleep(0.5)

        # Mock token counter to track calls
        mock_count_tokens = mocker.patch("app.routers.chat.count_tokens")
        mock_count_tokens.return_value = 10

        request = {
            "prompt": {
                "content": "Tell me more",
                "id": "2",
                "role": "user"
            },
            "threadId": thread_id,
            "responseId": "resp2",
        }

        # When: Make chat request
        response = fastapi_test_client.post("/api/chat", json=request)

        # Then: Token counter should be called (for message and potentially context)
        assert response.status_code == 200
        assert mock_count_tokens.call_count >= 1

    @pytest.mark.asyncio
    async def test_rag_stores_new_conversation(
        self, db_session, fastapi_test_client, mock_agent
    ):
        """
        Test that new conversations are still stored after RAG integration.
        """
        # Given: New thread
        thread_id = "test-storage-after-rag"

        request = {
            "prompt": {
                "content": "What's AAPL's price?",
                "id": "1",
                "role": "user"
            },
            "threadId": thread_id,
            "responseId": "resp1",
        }

        # When: Make chat request
        response = fastapi_test_client.post("/api/chat", json=request)
        assert response.status_code == 200

        # Wait for background storage
        await asyncio.sleep(2)

        # Then: Conversation should be stored
        stored = db_session.query(ConversationEmbedding).filter_by(
            thread_id=thread_id
        ).first()
        assert stored is not None

    @pytest.mark.asyncio
    async def test_rag_end_to_end_flow(self, db_session, fastapi_test_client, mock_agent):
        """
        Test complete RAG flow: store -> retrieve -> respond -> store.
        """
        thread_id = "test-e2e-rag"

        # Step 1: Store initial conversation
        context_storage = get_context_storage_service()
        await context_storage.store_conversation_turn(
            thread_id=thread_id,
            user_id=1,
            user_message="What's AAPL's price?",
            assistant_response="Apple Inc (AAPL) is trading at $175.43.",
            tokens=40,
        )

        await asyncio.sleep(0.5)

        # Step 2: Make follow-up request that should retrieve context
        request = {
            "prompt": {
                "content": "How has that stock performed this year?",
                "id": "2",
                "role": "user"
            },
            "threadId": thread_id,
            "responseId": "resp2",
        }

        response = fastapi_test_client.post("/api/chat", json=request)
        assert response.status_code == 200

        # Step 3: Verify context was available for retrieval
        context_retrieval = get_context_retrieval_service()
        contexts = await context_retrieval.retrieve_relevant_context(
            query="stock performance",
            thread_id=thread_id,
            user_id=1,
            top_k=5,
        )

        assert len(contexts) >= 1
        assert "AAPL" in contexts[0]["user_message"] or "AAPL" in contexts[0]["assistant_response"]

        # Step 4: Wait for new conversation to be stored
        await asyncio.sleep(2)

        # Step 5: Verify both conversations are stored
        all_contexts = db_session.query(ConversationEmbedding).filter_by(
            thread_id=thread_id
        ).all()
        # Should have at least the initial conversation stored
        assert len(all_contexts) >= 1


@pytest.mark.integration
class TestRAGPerformance:
    """Test RAG performance characteristics."""

    @pytest.mark.asyncio
    async def test_rag_retrieval_is_fast(self, db_session):
        """
        Test that context retrieval completes within acceptable time.
        """
        # Given: Store some conversations
        context_storage = get_context_storage_service()
        thread_id = "perf-test"
        user_id = 1

        for i in range(10):
            await context_storage.store_conversation_turn(
                thread_id=thread_id,
                user_id=user_id,
                user_message=f"Question {i} about stocks",
                assistant_response=f"Answer {i} about stocks",
                tokens=20,
            )

        await asyncio.sleep(1)

        # When: Retrieve context
        context_retrieval = get_context_retrieval_service()
        start_time = time.time()
        contexts = await context_retrieval.retrieve_relevant_context(
            query="Tell me about stocks",
            thread_id=thread_id,
            user_id=user_id,
            top_k=5,
        )
        duration = time.time() - start_time

        # Then: Should be fast (<200ms)
        assert duration < 0.2, f"Retrieval took {duration*1000:.1f}ms, expected <200ms"
        assert len(contexts) <= 5

    @pytest.mark.asyncio
    async def test_rag_retrieves_most_relevant(self, db_session):
        """
        Test that RAG retrieves most semantically relevant context.
        """
        # Given: Store conversations about different topics
        context_storage = get_context_storage_service()
        thread_id = "relevance-test"
        user_id = 1

        # Highly relevant
        await context_storage.store_conversation_turn(
            thread_id=thread_id,
            user_id=user_id,
            user_message="What's Apple's stock price?",
            assistant_response="Apple (AAPL) is trading at $175.",
            tokens=20,
        )

        # Less relevant
        await context_storage.store_conversation_turn(
            thread_id=thread_id,
            user_id=user_id,
            user_message="What's the weather today?",
            assistant_response="The weather is sunny.",
            tokens=15,
        )

        await asyncio.sleep(0.5)

        # When: Query about Apple
        context_retrieval = get_context_retrieval_service()
        contexts = await context_retrieval.retrieve_relevant_context(
            query="Tell me about Apple stock",
            thread_id=thread_id,
            user_id=user_id,
            top_k=1,  # Only get the most relevant
        )

        # Then: Should retrieve the Apple conversation, not weather
        assert len(contexts) >= 1
        most_relevant = contexts[0]
        assert "Apple" in most_relevant["user_message"] or "AAPL" in most_relevant["assistant_response"]
        assert "weather" not in most_relevant["user_message"].lower()
