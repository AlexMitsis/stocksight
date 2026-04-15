"""
Unit tests for Redis caching functionality.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from app.core.cache import cache, clear_cache_pattern


class TestCacheDecorator:
    """Test the cache decorator functionality."""

    @pytest.fixture(autouse=True)
    def mock_redis(self, monkeypatch):
        """Mock Redis client for testing."""
        mock_client = MagicMock()
        # Simulate cache miss (returns None)
        mock_client.get.return_value = None
        monkeypatch.setattr("app.core.cache.redis_client", mock_client)
        return mock_client

    def test_cache_decorator_caches_result(self, mock_redis):
        """Test that cache decorator stores and retrieves results."""
        # Given: A cached function
        call_count = 0

        @cache(ttl=60, include_timestamp=True)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return {"result": x * 2}

        # When: Called twice with same argument
        result1 = expensive_function(5)
        result2 = expensive_function(5)

        # Then: Function called only once, result cached
        assert call_count == 1
        assert result1["result"] == 10
        assert "cached_at" in result1

    def test_cache_miss_calls_function(self, mock_redis):
        """Test that cache miss triggers function call."""
        # Given: Redis returns None (cache miss)
        mock_redis.get.return_value = None

        @cache(ttl=60)
        def test_function():
            return {"data": "test"}

        # When: Function called
        result = test_function()

        # Then: Function executed, Redis get called
        assert result == {"data": "test"}
        mock_redis.get.assert_called_once()

    def test_cache_hit_returns_cached_value(self, mock_redis):
        """Test that cache hit returns cached value without calling function."""
        # Given: Redis returns cached value
        import json
        cached_data = {"data": "cached_value", "cached_at": "2024-01-01T00:00:00Z"}
        mock_redis.get.return_value = json.dumps(cached_data)

        call_count = 0

        @cache(ttl=60)
        def test_function():
            nonlocal call_count
            call_count += 1
            return {"data": "new_value"}

        # When: Function called
        result = test_function()

        # Then: Cached value returned, function not called
        assert result == cached_data
        assert call_count == 0
        mock_redis.get.assert_called_once()

    def test_cache_includes_timestamp(self, mock_redis):
        """Test that timestamp is added to cached results."""
        # Given: Cache decorator with include_timestamp=True
        @cache(ttl=60, include_timestamp=True)
        def test_function():
            return {"value": 123}

        # When: Function called
        result = test_function()

        # Then: Result includes timestamp
        assert "cached_at" in result
        assert "Z" in result["cached_at"]  # ISO format with UTC

    def test_cache_respects_ttl(self, mock_redis):
        """Test that cache TTL is set correctly."""
        # Given: Cache with specific TTL
        @cache(ttl=3600, include_timestamp=False)
        def test_function():
            return {"value": 123}

        # When: Function called
        result = test_function()

        # Then: Redis setex called with correct TTL
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3600  # TTL argument

    def test_cache_handles_different_arguments(self, mock_redis):
        """Test that cache distinguishes between different function arguments."""
        # Given: Cached function with arguments
        @cache(ttl=60)
        def test_function(ticker, date):
            return {"ticker": ticker, "date": date}

        # When: Called with different arguments
        result1 = test_function("AAPL", "2024-01-01")
        result2 = test_function("MSFT", "2024-01-02")

        # Then: Different cache keys used
        assert mock_redis.get.call_count == 2
        assert result1["ticker"] == "AAPL"
        assert result2["ticker"] == "MSFT"

    def test_cache_with_no_redis_client(self, monkeypatch):
        """Test that function works without Redis."""
        # Given: No Redis client available
        monkeypatch.setattr("app.core.cache.redis_client", None)

        @cache(ttl=60)
        def test_function():
            return {"value": 123}

        # When: Function called
        result = test_function()

        # Then: Function executed normally without caching
        assert result == {"value": 123}

    def test_cache_error_fallback(self, mock_redis):
        """Test that cache errors don't break the application."""
        # Given: Redis raises error
        mock_redis.get.side_effect = Exception("Redis connection error")

        @cache(ttl=60)
        def test_function():
            return {"value": 123}

        # When: Function called
        result = test_function()

        # Then: Function executes despite cache error
        assert result == {"value": 123}

    def test_cache_excludes_timestamp_when_not_dict(self, mock_redis):
        """Test that timestamp is only added to dict results."""
        # Given: Function returning non-dict
        @cache(ttl=60, include_timestamp=True)
        def test_function():
            return "string_result"

        # When: Function called
        result = test_function()

        # Then: Result unchanged (no timestamp added)
        assert result == "string_result"


class TestClearCachePattern:
    """Test cache clearing functionality."""

    @pytest.fixture
    def mock_redis(self, monkeypatch):
        """Mock Redis client for testing."""
        mock_client = MagicMock()
        monkeypatch.setattr("app.core.cache.redis_client", mock_client)
        return mock_client

    def test_clear_cache_pattern_deletes_keys(self, mock_redis):
        """Test that clear_cache_pattern deletes matching keys."""
        # Given: Keys exist in Redis
        mock_redis.keys.return_value = [
            "cache:get_stock_price:AAPL",
            "cache:get_stock_price:MSFT"
        ]
        mock_redis.delete.return_value = 2

        # When: Clear cache for pattern
        deleted = clear_cache_pattern("get_stock_price:*")

        # Then: Keys deleted
        assert deleted == 2
        mock_redis.keys.assert_called_once_with("cache:get_stock_price:*")
        mock_redis.delete.assert_called_once()

    def test_clear_cache_pattern_no_keys(self, mock_redis):
        """Test clearing cache when no keys match."""
        # Given: No matching keys
        mock_redis.keys.return_value = []

        # When: Clear cache for pattern
        deleted = clear_cache_pattern("nonexistent:*")

        # Then: No keys deleted
        assert deleted == 0
        mock_redis.delete.assert_not_called()

    def test_clear_cache_pattern_no_redis(self, monkeypatch):
        """Test clearing cache without Redis client."""
        # Given: No Redis client
        monkeypatch.setattr("app.core.cache.redis_client", None)

        # When: Clear cache
        deleted = clear_cache_pattern("test:*")

        # Then: Returns 0 without error
        assert deleted == 0

    def test_clear_cache_pattern_error_handling(self, mock_redis):
        """Test that errors during clear are handled gracefully."""
        # Given: Redis raises error
        mock_redis.keys.side_effect = Exception("Redis error")

        # When: Clear cache
        deleted = clear_cache_pattern("test:*")

        # Then: Returns 0 without raising
        assert deleted == 0


class TestCacheIntegrationWithTools:
    """Integration tests for cache with actual tool functions."""

    @pytest.fixture
    def mock_redis(self, monkeypatch):
        """Mock Redis client for integration tests."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        monkeypatch.setattr("app.core.cache.redis_client", mock_client)
        return mock_client

    def test_stock_price_caching(self, mock_redis, mocker):
        """Test that stock price tool uses cache correctly."""
        from app.tools.stock_price import _fetch_stock_price_cached

        # Given: Mock yfinance
        mock_yf = mocker.patch("app.tools.stock_price.yf.Ticker")
        mock_stock = Mock()
        mock_stock.history.return_value = {"Close": [175.43]}
        mock_stock.history.return_value.__getitem__ = lambda self, key: [175.43]
        mock_yf.return_value = mock_stock

        # When: Fetch price (will be cached)
        result = _fetch_stock_price_cached("AAPL")

        # Then: Result has expected structure
        assert result["ticker"] == "AAPL"
        assert "price" in result
        assert "formatted" in result
        assert "cached_at" in result

    def test_balance_sheet_caching(self, mock_redis, mocker):
        """Test that balance sheet tool uses cache correctly."""
        from app.tools.balance_sheet import _fetch_balance_sheet_cached

        # Given: Mock yfinance with balance sheet
        mock_yf = mocker.patch("app.tools.balance_sheet.yf.Ticker")
        mock_stock = Mock()
        mock_df = Mock()
        mock_df.empty = False
        mock_df.to_dict.return_value = {"Total Assets": 1000000}
        mock_stock.balance_sheet = mock_df
        mock_yf.return_value = mock_stock

        # When: Fetch balance sheet (will be cached)
        result = _fetch_balance_sheet_cached("AAPL")

        # Then: Result has expected structure
        assert result["ticker"] == "AAPL"
        assert "data" in result
        assert "cached_at" in result
