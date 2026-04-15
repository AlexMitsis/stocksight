"""
Embedding service for generating vector embeddings.

This service uses OpenAI's text-embedding-3-small model for generating embeddings
used for RAG context storage and retrieval.
"""

from typing import List
from loguru import logger
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


class EmbeddingService:
    """
    Service for generating embeddings using OpenAI's text-embedding-3-small model.

    Uses LangChain's OpenAIEmbeddings for generating 1536-dimensional vectors
    used in RAG context storage and retrieval.
    """

    def __init__(self):
        """Initialize the embedding service with OpenAI text-embedding-3-small model."""
        # Use dedicated embeddings API key if available, otherwise fall back to main key
        api_key = settings.OPENAI_EMBEDDINGS_API_KEY or settings.OPENAI_API_KEY

        # Only use custom base URL if using the main API key (no dedicated embeddings key)
        # When using dedicated embeddings key, use standard OpenAI endpoint
        if settings.OPENAI_EMBEDDINGS_API_KEY:
            # Use standard OpenAI embeddings endpoint
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=api_key,
                model="text-embedding-3-small",  # Latest model, 62% cheaper than ada-002
            )
            logger.info("EmbeddingService initialized with text-embedding-3-small via standard OpenAI API")
        else:
            # Fall back to custom endpoint (may not support embeddings)
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=api_key,
                model="text-embedding-3-small",
                openai_api_base=settings.MODEL_BASE_URL,
            )
            logger.warning(
                f"EmbeddingService using custom endpoint {settings.MODEL_BASE_URL} "
                "(may not support embeddings - consider setting OPENAI_EMBEDDINGS_API_KEY)"
            )

    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            1536-dimensional embedding vector

        Example:
            >>> service = EmbeddingService()
            >>> embedding = await service.embed("Apple is a technology company")
            >>> len(embedding)
            1536
        """
        try:
            logger.debug(f"Generating embedding for text: {text[:100]}...")
            embedding = await self.embeddings.aembed_query(text)
            logger.info(f"Embedding generated: {len(embedding)} dimensions")
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with automatic caching.

        Each text is cached independently, so partial cache hits are possible.
        For example, if you embed ["AAPL analysis", "TSLA analysis", "MSFT analysis"]
        and "AAPL analysis" was previously embedded, only 2 API calls will be made.

        Args:
            texts: List of texts to embed

        Returns:
            List of 1536-dimensional embedding vectors

        Example:
            >>> service = EmbeddingService()
            >>> embeddings = await service.embed_batch(["text1", "text2", "text3"])
            >>> len(embeddings)
            3
            >>> len(embeddings[0])
            1536
        """
        try:
            logger.debug(f"Generating embeddings for {len(texts)} texts")
            embeddings = await self.embeddings.aembed_documents(texts)
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings

        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
            raise


# Global singleton instance
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """
    Get or create the global EmbeddingService instance.

    Returns:
        Singleton instance of EmbeddingService
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
