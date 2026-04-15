"""
Unit tests for historical_price tool.
"""

import pytest
import pandas as pd
from app.tools.historical_price import get_historical_stock_price

# Get the underlying function from the StructuredTool
get_historical_stock_price_func = get_historical_stock_price.func


@pytest.mark.unit
class TestGetHistoricalStockPrice:
    """Test suite for get_historical_stock_price tool."""

    def test_get_historical_price_valid_range(self, mocker, mock_historical_data):
        """
        Test historical price retrieval with valid date range.

        Given: Mock yfinance returns historical data
        When: get_historical_stock_price is called with valid dates
        Then: Returns dictionary with OHLCV data
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.history.return_value = mock_historical_data
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_historical_stock_price_func("AAPL", "2024-01-01", "2024-01-05")

        # Then
        assert isinstance(result, dict)
        assert "Close" in result
        assert "Open" in result
        assert "High" in result
        assert "Low" in result
        assert "Volume" in result

        # Verify yfinance was called with correct parameters
        mock_ticker.history.assert_called_once_with(start="2024-01-01", end="2024-01-05")

    def test_get_historical_price_empty_data(self, mocker):
        """
        Test handling of no data for date range.

        Given: yfinance returns empty DataFrame
        When: get_historical_stock_price is called
        Then: Returns error message
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()  # Empty
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_historical_stock_price_func("AAPL", "2024-01-01", "2024-01-05")

        # Then
        assert isinstance(result, str)
        assert "No historical data found" in result

    def test_get_historical_price_invalid_ticker(self, mocker):
        """
        Test error handling for invalid ticker.

        Given: yfinance raises exception
        When: get_historical_stock_price is called
        Then: Returns error message
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.history.side_effect = Exception("Invalid ticker")
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_historical_stock_price_func("INVALID", "2024-01-01", "2024-01-05")

        # Then
        assert isinstance(result, str)
        assert "Unable to fetch historical data" in result

    def test_get_historical_price_invalid_date_format(self, mocker):
        """
        Test error handling for invalid date format.

        Given: Invalid date format provided
        When: get_historical_stock_price is called
        Then: Handles error gracefully
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.history.side_effect = Exception("Invalid date format")
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_historical_stock_price_func("AAPL", "invalid-date", "2024-01-05")

        # Then
        assert isinstance(result, str)
        assert "Unable to fetch historical data" in result or "date format" in result.lower()
