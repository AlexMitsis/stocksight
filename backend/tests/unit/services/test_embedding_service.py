"""
Unit tests for the embedding service.

These tests verify the embedding service correctly generates embeddings
for RAG context storage and retrieval.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.embedding_service import EmbeddingService, get_embedding_service


@pytest.fixture
def mock_openai_embeddings():
    """Mock OpenAIEmbeddings for testing."""
    with patch("app.services.embedding_service.OpenAIEmbeddings") as mock:
        # Create a mock instance
        mock_instance = MagicMock()
        mock_instance.aembed_query = AsyncMock()
        mock_instance.aembed_documents = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.mark.unit
class TestEmbeddingService:
    """Test cases for EmbeddingService."""

    def test_initialization(self, mock_openai_embeddings):
        """Test that EmbeddingService initializes correctly."""
        service = EmbeddingService()

        assert service.embeddings is not None
        assert isinstance(service.embeddings, MagicMock)

    @pytest.mark.asyncio
    async def test_embed_single_text(self, mock_openai_embeddings):
        """Test embedding a single text."""
        # Setup
        service = EmbeddingService()
        test_text = "Apple is a technology company"
        expected_embedding = [0.1] * 1536  # Mock 1536-dimensional embedding

        mock_openai_embeddings.aembed_query.return_value = expected_embedding

        # Execute
        result = await service.embed(test_text)

        # Verify
        assert result == expected_embedding
        assert len(result) == 1536
        mock_openai_embeddings.aembed_query.assert_called_once_with(test_text)

    @pytest.mark.asyncio
    async def test_embed_batch(self, mock_openai_embeddings):
        """Test embedding multiple texts in batch."""
        # Setup
        service = EmbeddingService()
        test_texts = ["Text 1", "Text 2", "Text 3"]
        expected_embeddings = [[0.1] * 1536, [0.2] * 1536, [0.3] * 1536]

        mock_openai_embeddings.aembed_documents.return_value = expected_embeddings

        # Execute
        result = await service.embed_batch(test_texts)

        # Verify
        assert len(result) == 3
        assert result == expected_embeddings
        assert all(len(emb) == 1536 for emb in result)
        mock_openai_embeddings.aembed_documents.assert_called_once_with(test_texts)

    @pytest.mark.asyncio
    async def test_embed_error_handling(self, mock_openai_embeddings):
        """Test that errors are properly raised."""
        # Setup
        service = EmbeddingService()
        mock_openai_embeddings.aembed_query.side_effect = Exception("API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            await service.embed("Test text")

        assert "API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_embed_batch_error_handling(self, mock_openai_embeddings):
        """Test that batch errors are properly raised."""
        # Setup
        service = EmbeddingService()
        mock_openai_embeddings.aembed_documents.side_effect = Exception("Batch API Error")

        # Execute & Verify
        with pytest.raises(Exception) as exc_info:
            await service.embed_batch(["Text 1", "Text 2"])

        assert "Batch API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_embed_empty_string(self, mock_openai_embeddings):
        """Test embedding an empty string."""
        # Setup
        service = EmbeddingService()
        expected_embedding = [0.0] * 1536

        mock_openai_embeddings.aembed_query.return_value = expected_embedding

        # Execute
        result = await service.embed("")

        # Verify
        assert len(result) == 1536
        mock_openai_embeddings.aembed_query.assert_called_once_with("")

    @pytest.mark.asyncio
    async def test_embed_long_text(self, mock_openai_embeddings):
        """Test embedding a long text."""
        # Setup
        service = EmbeddingService()
        long_text = "A" * 10000  # Very long text
        expected_embedding = [0.5] * 1536

        mock_openai_embeddings.aembed_query.return_value = expected_embedding

        # Execute
        result = await service.embed(long_text)

        # Verify
        assert len(result) == 1536
        mock_openai_embeddings.aembed_query.assert_called_once_with(long_text)


@pytest.mark.unit
class TestGetEmbeddingService:
    """Test cases for get_embedding_service singleton."""

    def test_singleton_returns_same_instance(self):
        """Test that get_embedding_service returns the same instance."""
        # Reset the global instance
        import app.services.embedding_service as module
        module._embedding_service = None

        # Get instances
        with patch("app.services.embedding_service.OpenAIEmbeddings"):
            service1 = get_embedding_service()
            service2 = get_embedding_service()

            # Verify they're the same instance
            assert service1 is service2

    def test_singleton_creates_on_first_call(self):
        """Test that singleton creates instance on first call."""
        # Reset the global instance
        import app.services.embedding_service as module
        module._embedding_service = None

        with patch("app.services.embedding_service.OpenAIEmbeddings"):
            # First call should create instance
            assert module._embedding_service is None
            service = get_embedding_service()
            assert module._embedding_service is not None
            assert service is module._embedding_service
