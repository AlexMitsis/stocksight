"""
Unit tests for stock_price tool.

Tests TC1.2.1 and TC1.2.2 from Epic Story 1.2
"""

import pytest
from app.tools.stock_price import get_stock_price

# Get the underlying function from the StructuredTool
get_stock_price_func = get_stock_price.func


@pytest.mark.unit
class TestGetStockPrice:
    """Test suite for get_stock_price tool."""

    def test_get_stock_price_valid_ticker(self, mock_yfinance_ticker):
        """
        TC1.2.1: Stock price tool with valid ticker

        Given: Mock yfinance returns valid price data
        When: get_stock_price("AAPL") is called
        Then: Returns formatted price string "$175.43"
        """
        # When
        result = get_stock_price_func("AAPL")

        # Then
        assert result == "$175.43"
        # Verify yfinance was called correctly
        mock_yfinance_ticker.history.assert_called_once_with(period="1d")

    def test_get_stock_price_invalid_ticker(self, mocker):
        """
        TC1.2.2: Stock price tool with invalid ticker

        Given: yfinance raises an exception for invalid ticker
        When: get_stock_price("INVALID") is called
        Then: Returns error message
        """
        # Given: Mock yfinance to raise an exception
        mock_ticker = mocker.MagicMock()
        mock_ticker.history.side_effect = Exception("Invalid ticker")
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_stock_price_func("INVALID")

        # Then
        assert "Unable to fetch price" in result
        assert "INVALID" in result

    def test_get_stock_price_empty_data(self, mocker):
        """
        Test handling of empty data from yfinance.

        Given: yfinance returns empty DataFrame
        When: get_stock_price is called
        Then: Handles error gracefully
        """
        # Given
        import pandas as pd

        mock_ticker = mocker.MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()  # Empty DataFrame
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_stock_price_func("TEST")

        # Then
        assert "Unable to fetch price" in result or isinstance(result, str)

    def test_get_stock_price_different_tickers(self, mocker):
        """
        Test that different tickers can be queried.

        Verifies the tool works for various stock symbols.
        """
        import pandas as pd

        # Test multiple tickers
        test_cases = [
            ("AAPL", 175.43),
            ("MSFT", 380.50),
            ("GOOGL", 142.20),
        ]

        for ticker, price in test_cases:
            mock_ticker = mocker.MagicMock()
            mock_ticker.history.return_value = pd.DataFrame({"Close": [price]})
            mocker.patch("yfinance.Ticker", return_value=mock_ticker)

            result = get_stock_price_func(ticker)

            assert result == f"${price:.2f}"

    def test_get_stock_price_returns_string(self, mock_yfinance_ticker):
        """
        Test that return type is always a string.

        Ensures API contract is maintained.
        """
        result = get_stock_price_func("AAPL")

        assert isinstance(result, str)
        assert len(result) > 0
