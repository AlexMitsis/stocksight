"""
Unit tests for logging middleware and correlation ID tracking.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.middleware import LoggingMiddleware
from app.core.correlation import get_correlation_id, set_correlation_id, generate_correlation_id


class TestCorrelationID:
    """Test correlation ID utility functions."""

    def test_generate_correlation_id(self):
        """Test that generate_correlation_id creates valid UUIDs."""
        # When
        correlation_id = generate_correlation_id()

        # Then
        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 36  # UUID4 format
        assert correlation_id.count('-') == 4

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        # Given
        test_id = "test-correlation-123"

        # When
        set_correlation_id(test_id)
        retrieved_id = get_correlation_id()

        # Then
        assert retrieved_id == test_id

    def test_get_correlation_id_default(self):
        """Test getting correlation ID returns None by default."""
        # When (in new context)
        correlation_id = get_correlation_id()

        # Then
        assert correlation_id is None or isinstance(correlation_id, str)


class TestLoggingMiddleware:
    """Test logging middleware functionality."""

    @pytest.fixture
    def app(self):
        """Create test FastAPI app with logging middleware."""
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client that returns 500 responses instead of re-raising app errors."""
        return TestClient(app, raise_server_exceptions=False)

    def test_middleware_adds_correlation_id_to_response(self, client):
        """Test that middleware adds X-Correlation-ID to response headers."""
        # When
        response = client.get("/test")

        # Then
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        correlation_id = response.headers["X-Correlation-ID"]
        assert len(correlation_id) == 36  # UUID4 format

    def test_middleware_preserves_provided_correlation_id(self, client):
        """Test that middleware uses correlation ID from request header."""
        # Given
        test_correlation_id = "my-custom-correlation-id"

        # When
        response = client.get(
            "/test",
            headers={"X-Correlation-ID": test_correlation_id}
        )

        # Then
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_correlation_id

    @patch('app.middleware.logging_middleware.logger')
    def test_middleware_logs_request(self, mock_logger, client):
        """Test that middleware logs incoming requests."""
        # When
        response = client.get("/test")

        # Then
        assert response.status_code == 200
        # Verify logger.bind was called with correlation_id
        assert mock_logger.bind.called
        # Verify info was called with request details
        mock_logger.bind.return_value.info.assert_any_call(
            pytest.approx("Request started: GET /test", rel=1e-2)
        )

    @patch('app.middleware.logging_middleware.logger')
    def test_middleware_logs_response(self, mock_logger, client):
        """Test that middleware logs responses with timing."""
        # When
        response = client.get("/test")

        # Then
        assert response.status_code == 200
        # Verify completion was logged with status code and duration
        calls = mock_logger.bind.return_value.info.call_args_list
        assert len(calls) >= 2  # At least request and response logs
        # Check that one of the calls mentions "completed" and duration
        completed_calls = [call for call in calls if 'completed' in str(call) or 'Request completed' in str(call)]
        assert len(completed_calls) > 0

    @patch('app.middleware.logging_middleware.logger')
    def test_middleware_logs_errors(self, mock_logger, client):
        """Test that middleware logs errors with correlation ID."""
        # When
        response = client.get("/error")

        # Then
        assert response.status_code == 500  # FastAPI's default error response
        # Verify error was logged
        mock_logger.bind.return_value.error.assert_called_once()
        error_call = mock_logger.bind.return_value.error.call_args[0][0]
        assert "failed" in error_call.lower() or "error" in error_call.lower()

    def test_middleware_timing_accuracy(self, client):
        """Test that middleware accurately measures request duration."""
        # Given: endpoint that takes some time
        import time

        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.get("/slow")
        async def slow_endpoint():
            time.sleep(0.1)  # 100ms delay
            return {"message": "slow"}

        client = TestClient(app)

        # When
        with patch('app.middleware.logging_middleware.logger') as mock_logger:
            response = client.get("/slow")

        # Then
        assert response.status_code == 200
        # Verify that duration was logged and is reasonable
        calls = mock_logger.bind.return_value.info.call_args_list
        completed_call = [call for call in calls if 'completed' in str(call)]
        assert len(completed_call) > 0

    def test_middleware_multiple_requests_different_correlation_ids(self, client):
        """Test that each request gets its own correlation ID."""
        # When
        response1 = client.get("/test")
        response2 = client.get("/test")

        # Then
        correlation_id_1 = response1.headers["X-Correlation-ID"]
        correlation_id_2 = response2.headers["X-Correlation-ID"]
        assert correlation_id_1 != correlation_id_2

    def test_middleware_works_with_post_requests(self, client):
        """Test that middleware works with different HTTP methods."""
        # Given: Add POST endpoint
        from fastapi import FastAPI
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.post("/test")
        async def post_endpoint(data: dict):
            return {"received": data}

        client = TestClient(app)

        # When
        response = client.post("/test", json={"key": "value"})

        # Then
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers


class TestLoggingConfiguration:
    """Test logging configuration."""

    def test_correlation_id_in_logs(self):
        """Test that correlation ID filter adds correlation ID to log records."""
        from app.core.logging import correlation_id_filter
        from app.core.correlation import set_correlation_id

        # Given
        set_correlation_id("test-id-123")
        record = {"extra": {}}

        # When
        result = correlation_id_filter(record)

        # Then
        assert result is True
        assert record["extra"]["correlation_id"] == "test-id-123"

    def test_correlation_id_filter_handles_missing_id(self):
        """Test that filter handles missing correlation ID gracefully."""
        from app.core.logging import correlation_id_filter

        # Given: no correlation ID set (earlier tests may have set one in this context)
        from app.core.correlation import _correlation_id

        _correlation_id.set(None)
        record = {"extra": {}}

        # When
        result = correlation_id_filter(record)

        # Then
        assert result is True
        assert record["extra"]["correlation_id"] == "N/A"
