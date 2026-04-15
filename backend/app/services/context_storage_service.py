"""
Context storage service for storing conversation turns with embeddings.

This service handles asynchronous storage of conversation context in PostgreSQL
with pgvector embeddings for semantic search and RAG capabilities.
"""

from datetime import datetime
from typing import List, Optional
import re
import time
from loguru import logger
from sqlalchemy.orm import Session

from app.services.embedding_service import get_embedding_service
from app.models.database import ConversationEmbedding
from app.core.database import get_db
from app.services.metrics import (
    rag_storage_duration,
    rag_storage_errors,
    rag_storage_success,
)


class ContextStorageService:
    """
    Service for storing conversation turns with embeddings in PostgreSQL.

    This service:
    - Generates embeddings for conversation turns
    - Stores embeddings in PostgreSQL with pgvector
    - Extracts metadata (tickers, timestamps, tokens)
    - Handles errors gracefully (storage failures don't crash app)
    - Supports async, non-blocking storage
    """

    def __init__(self):
        """Initialize the context storage service."""
        self.embedding_service = get_embedding_service()
        logger.info("ContextStorageService initialized")

    async def store_conversation_turn(
        self,
        thread_id: str,
        user_id: int,
        user_message: str,
        assistant_response: str,
        tokens: int,
        db: Optional[Session] = None,
    ) -> bool:
        """
        Store a conversation turn in PostgreSQL with pgvector embedding.

        This method:
        1. Combines user message and assistant response
        2. Generates embedding using EmbeddingService
        3. Extracts tickers mentioned in conversation
        4. Stores in PostgreSQL with metadata

        Args:
            thread_id: Conversation thread identifier
            user_id: User identifier for data isolation
            user_message: User's message
            assistant_response: Assistant's response
            tokens: Token count for this turn
            db: Optional database session (creates new if not provided)

        Returns:
            True if storage succeeded, False otherwise

        Example:
            >>> service = ContextStorageService()
            >>> success = await service.store_conversation_turn(
            ...     thread_id="thread-123",
            ...     user_id=1,
            ...     user_message="What's the price of AAPL?",
            ...     assistant_response="Apple Inc. (AAPL) is trading at $175.43.",
            ...     tokens=150
            ... )
        """
        # Use provided session or create new one
        db_session = db if db is not None else next(get_db())
        should_close = db is None  # Only close if we created the session

        start_time = time.time()

        try:
            # Combine user message and response for context
            full_context = f"User: {user_message}\nAssistant: {assistant_response}"

            logger.debug(f"Storing conversation turn for thread {thread_id}, {len(full_context)} chars")

            # Extract tickers mentioned in conversation
            tickers = self._extract_tickers(full_context)

            # Generate embedding for the conversation context
            # This may fail if embeddings API is not configured
            try:
                embedding = await self.embedding_service.embed(full_context)
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}. Skipping storage.")
                rag_storage_errors.inc()
                return False

            # Create metadata (using 'meta' to avoid SQLAlchemy reserved word 'metadata')
            meta = {
                "user_message": user_message,
                "assistant_response": assistant_response,
                "tokens": tokens,
                "tickers": tickers,
                "timestamp": datetime.utcnow().isoformat(),
                "message_length": len(full_context),
            }

            # Create embedding record
            embedding_record = ConversationEmbedding(
                thread_id=thread_id,
                user_id=user_id,
                content=full_context,
                embedding=embedding,
                meta=meta,
            )

            # Store in PostgreSQL
            db_session.add(embedding_record)
            db_session.commit()

            # Track storage duration and success
            duration = time.time() - start_time
            rag_storage_duration.observe(duration)
            rag_storage_success.inc()

            logger.info(
                f"Stored conversation embedding for thread {thread_id} in {duration*1000:.1f}ms "
                f"(user_id={user_id}, tickers={tickers}, tokens={tokens})"
            )

            return True

        except Exception as e:
            logger.error(f"Failed to store conversation context: {e}")
            db_session.rollback()
            rag_storage_errors.inc()
            # Don't raise - storage failure shouldn't break chat
            return False

        finally:
            if should_close:
                db_session.close()

    def _extract_tickers(self, text: str) -> List[str]:
        """
        Extract stock tickers from text.

        Uses simple regex pattern to find potential ticker symbols
        (1-5 uppercase letters) and filters out common words.

        Args:
            text: Text to extract tickers from

        Returns:
            List of ticker symbols found

        Example:
            >>> service = ContextStorageService()
            >>> service._extract_tickers("AAPL is up but TSLA is down")
            ['AAPL', 'TSLA']
            >>> service._extract_tickers("I think AI is the future")
            []  # 'AI' filtered out as common word
        """
        # Simple regex: 1-5 uppercase letters as word boundaries
        pattern = r"\b([A-Z]{1,5})\b"
        potential_tickers = re.findall(pattern, text)

        # Filter out common words that aren't tickers
        common_words = {
            "I",
            "A",
            "CEO",
            "CFO",
            "CTO",
            "AI",
            "US",
            "EU",
            "UK",
            "USA",
            "API",
            "URL",
            "HTTP",
            "HTTPS",
            "JSON",
            "XML",
            "SQL",
            "HTML",
            "CSS",
            "USD",
            "EUR",
            "GBP",
        }

        # Remove duplicates and filter
        tickers = []
        seen = set()
        for ticker in potential_tickers:
            if ticker not in common_words and ticker not in seen:
                tickers.append(ticker)
                seen.add(ticker)

        return tickers

    async def get_conversation_history(
        self, thread_id: str, user_id: int, limit: int = 10, db: Optional[Session] = None
    ) -> List[ConversationEmbedding]:
        """
        Retrieve recent conversation history for a thread.

        Args:
            thread_id: Thread identifier
            user_id: User identifier (for data isolation)
            limit: Maximum number of records to return
            db: Optional database session

        Returns:
            List of ConversationEmbedding records, newest first

        Example:
            >>> service = ContextStorageService()
            >>> history = await service.get_conversation_history("thread-123", user_id=1, limit=5)
            >>> len(history)
            5
        """
        db_session = db if db is not None else next(get_db())
        should_close = db is None

        try:
            records = (
                db_session.query(ConversationEmbedding)
                .filter(
                    ConversationEmbedding.thread_id == thread_id,
                    ConversationEmbedding.user_id == user_id,
                )
                .order_by(ConversationEmbedding.created_at.desc())
                .limit(limit)
                .all()
            )

            logger.debug(
                f"Retrieved {len(records)} conversation records for thread {thread_id}, user {user_id}"
            )

            return records

        except Exception as e:
            logger.error(f"Failed to retrieve conversation history: {e}")
            return []

        finally:
            if should_close:
                db_session.close()


# Global singleton instance
_context_storage_service: Optional[ContextStorageService] = None


def get_context_storage_service() -> ContextStorageService:
    """
    Get or create the global ContextStorageService instance.

    Returns:
        Singleton instance of ContextStorageService
    """
    global _context_storage_service
    if _context_storage_service is None:
        _context_storage_service = ContextStorageService()
    return _context_storage_service
