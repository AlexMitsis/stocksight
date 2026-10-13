"""
Context retrieval service for retrieving relevant conversation context using pgvector.

This service handles semantic search of past conversation context using
PostgreSQL pgvector for RAG (Retrieval-Augmented Generation) capabilities.
"""

from typing import List, Dict, Optional
import time
from loguru import logger
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.services.embedding_service import get_embedding_service
from app.models.database import ConversationEmbedding
from app.core.database import get_db
from app.services.metrics import (
    rag_retrieval_duration,
    rag_chunks_retrieved,
    rag_relevance_score,
)


class ContextRetrievalService:
    """
    Service for retrieving relevant conversation context using pgvector similarity search.

    This service:
    - Generates embeddings for user queries
    - Performs semantic search using pgvector cosine similarity
    - Filters by thread_id and user_id for data isolation
    - Returns top-k most relevant context chunks
    - Formats context for inclusion in LLM prompts
    - Handles errors gracefully (retrieval failures don't crash app)
    """

    def __init__(self):
        """Initialize the context retrieval service."""
        self.embedding_service = get_embedding_service()
        logger.info("ContextRetrievalService initialized")

    async def retrieve_relevant_context(
        self,
        query: str,
        thread_id: str,
        user_id: int,
        top_k: int = 5,
        db: Optional[Session] = None,
    ) -> List[Dict]:
        """
        Retrieve relevant past context using pgvector similarity search.

        This method:
        1. Generates embedding for user query
        2. Searches PostgreSQL using cosine similarity
        3. Filters by thread_id and user_id (data isolation)
        4. Returns top-k most relevant chunks with metadata

        Args:
            query: User query to find relevant context for
            thread_id: Conversation thread identifier
            user_id: User identifier (for data isolation)
            top_k: Number of most relevant chunks to return (default: 5)
            db: Optional database session (creates new if not provided)

        Returns:
            List of context dictionaries with keys:
                - user_message: Original user message
                - assistant_response: Original assistant response
                - timestamp: ISO format timestamp
                - relevance_score: Similarity score (0-1, higher is more relevant)
                - tickers: List of stock tickers mentioned

        Example:
            >>> service = ContextRetrievalService()
            >>> contexts = await service.retrieve_relevant_context(
            ...     query="How has Apple performed?",
            ...     thread_id="thread-123",
            ...     user_id=1,
            ...     top_k=5
            ... )
            >>> len(contexts)
            5
            >>> contexts[0]["relevance_score"]
            0.92
        """
        db_session = db if db is not None else next(get_db())
        should_close = db is None

        try:
            start_time = time.time()

            logger.debug(
                f"Retrieving context for query: {query[:100]}... "
                f"(thread_id={thread_id}, user_id={user_id}, top_k={top_k})"
            )

            # Generate embedding for query
            # This may fail if embeddings API is not configured
            try:
                query_embedding = await self.embedding_service.embed(query)
            except Exception as e:
                logger.warning(f"Failed to generate query embedding: {e}. Returning empty context.")
                return []

            # Semantic search using pgvector cosine similarity
            # Filter by thread_id AND user_id for data isolation
            distance = ConversationEmbedding.embedding.cosine_distance(query_embedding).label(
                "distance"
            )
            results = (
                db_session.query(ConversationEmbedding, distance)
                .filter(
                    and_(
                        ConversationEmbedding.thread_id == thread_id,
                        ConversationEmbedding.user_id == user_id,
                    )
                )
                .order_by(distance)
                .limit(top_k)
                .all()
            )

            duration = time.time() - start_time

            # Track retrieval duration metric
            rag_retrieval_duration.observe(duration)

            # Track number of chunks retrieved
            rag_chunks_retrieved.observe(len(results))

            logger.info(
                f"Retrieved {len(results)} context chunks in {duration*1000:.1f}ms "
                f"(thread_id={thread_id}, user_id={user_id})"
            )

            # Extract and format context with metadata
            contexts = []
            for result, result_distance in results:
                similarity = 1 - result_distance  # cosine similarity

                contexts.append(
                    {
                        "user_message": result.meta.get("user_message", ""),
                        "assistant_response": result.meta.get("assistant_response", ""),
                        "timestamp": result.meta.get("timestamp", ""),
                        "relevance_score": float(similarity),
                        "tickers": result.meta.get("tickers", []),
                    }
                )

            # Log average relevance score for monitoring
            if contexts:
                avg_score = sum(c["relevance_score"] for c in contexts) / len(contexts)

                # Track average relevance score metric
                rag_relevance_score.observe(avg_score)

                logger.info(
                    f"Average relevance score: {avg_score:.3f} "
                    f"(min: {min(c['relevance_score'] for c in contexts):.3f}, "
                    f"max: {max(c['relevance_score'] for c in contexts):.3f})"
                )
            else:
                logger.info(f"No context found for thread {thread_id}, user {user_id}")

            return contexts

        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return []  # Return empty list, don't crash

        finally:
            if should_close:
                db_session.close()

    def format_context_for_prompt(self, contexts: List[Dict]) -> str:
        """
        Format retrieved context for inclusion in LLM prompt.

        Converts list of context dictionaries into a formatted string
        suitable for inclusion in the system message or user prompt.

        Args:
            contexts: List of context dictionaries from retrieve_relevant_context()

        Returns:
            Formatted string with past conversation context, or empty string if no context

        Example:
            >>> contexts = [
            ...     {
            ...         "user_message": "What's AAPL's price?",
            ...         "assistant_response": "Apple Inc. is trading at $175.43.",
            ...         "relevance_score": 0.92
            ...     }
            ... ]
            >>> service = ContextRetrievalService()
            >>> formatted = service.format_context_for_prompt(contexts)
            >>> print(formatted)
            Relevant past conversation:

            User: What's AAPL's price?
            Assistant: Apple Inc. is trading at $175.43.
        """
        if not contexts:
            return ""

        formatted = "Relevant past conversation:\n\n"

        for ctx in contexts:
            user_msg = ctx.get("user_message", "")
            assistant_msg = ctx.get("assistant_response", "")

            if user_msg:
                formatted += f"User: {user_msg}\n"
            if assistant_msg:
                formatted += f"Assistant: {assistant_msg}\n"

            # Add separator between context chunks
            formatted += "\n"

        return formatted.rstrip() + "\n\n"  # Clean up trailing whitespace

    def format_context_for_prompt_with_scores(self, contexts: List[Dict]) -> str:
        """
        Format retrieved context with relevance scores (for debugging).

        Similar to format_context_for_prompt() but includes relevance scores
        for debugging and monitoring purposes.

        Args:
            contexts: List of context dictionaries from retrieve_relevant_context()

        Returns:
            Formatted string with context and relevance scores

        Example:
            >>> contexts = [{"user_message": "Test", "assistant_response": "Response", "relevance_score": 0.92}]
            >>> service = ContextRetrievalService()
            >>> formatted = service.format_context_for_prompt_with_scores(contexts)
            >>> "relevance: 0.92" in formatted
            True
        """
        if not contexts:
            return ""

        formatted = "Relevant past conversation (with relevance scores):\n\n"

        for i, ctx in enumerate(contexts, 1):
            user_msg = ctx.get("user_message", "")
            assistant_msg = ctx.get("assistant_response", "")
            score = ctx.get("relevance_score", 0.0)

            formatted += f"[Context {i} - relevance: {score:.3f}]\n"

            if user_msg:
                formatted += f"User: {user_msg}\n"
            if assistant_msg:
                formatted += f"Assistant: {assistant_msg}\n"

            formatted += "\n"

        return formatted.rstrip() + "\n\n"


# Global singleton instance
_context_retrieval_service: Optional[ContextRetrievalService] = None


def get_context_retrieval_service() -> ContextRetrievalService:
    """
    Get or create the global ContextRetrievalService instance.

    Returns:
        Singleton instance of ContextRetrievalService
    """
    global _context_retrieval_service
    if _context_retrieval_service is None:
        _context_retrieval_service = ContextRetrievalService()
    return _context_retrieval_service
