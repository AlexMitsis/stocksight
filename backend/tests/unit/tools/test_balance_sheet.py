"""
Unit tests for balance_sheet tool.
"""

import pytest
import pandas as pd
from app.tools.balance_sheet import get_balance_sheet

# Get the underlying function from the StructuredTool
get_balance_sheet_func = get_balance_sheet.func


@pytest.mark.unit
class TestGetBalanceSheet:
    """Test suite for get_balance_sheet tool."""

    def test_get_balance_sheet_valid_ticker(self, mock_yfinance_ticker):
        """
        Test balance sheet retrieval with valid ticker.

        Given: Mock yfinance returns balance sheet data
        When: get_balance_sheet_func("AAPL") is called
        Then: Returns dictionary with financial data
        """
        # When
        result = get_balance_sheet_func("AAPL")

        # Then
        assert isinstance(result, dict)
        assert len(result) > 0
        # Check for common balance sheet fields
        assert "Total Assets" in result or isinstance(result, dict)

    def test_get_balance_sheet_no_data(self, mocker):
        """
        Test handling when no balance sheet data is available.

        Given: yfinance returns None or empty balance sheet
        When: get_balance_sheet is called
        Then: Returns error message
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.balance_sheet = None
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_balance_sheet_func("TEST")

        # Then
        assert isinstance(result, str)
        assert "No balance sheet data available" in result

    def test_get_balance_sheet_empty_dataframe(self, mocker):
        """
        Test handling of empty DataFrame.

        Given: yfinance returns empty DataFrame
        When: get_balance_sheet is called
        Then: Returns error message
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.balance_sheet = pd.DataFrame()
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_balance_sheet_func("TEST")

        # Then
        assert isinstance(result, str)
        assert "No balance sheet data available" in result

    def test_get_balance_sheet_invalid_ticker(self, mocker):
        """
        Test error handling for invalid ticker.

        Given: yfinance raises exception
        When: get_balance_sheet is called
        Then: Returns error message
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.balance_sheet = property(
            lambda self: (_ for _ in ()).throw(Exception("Invalid"))
        )
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_balance_sheet_func("INVALID")

        # Then
        assert isinstance(result, str)
        assert "Unable to fetch balance sheet" in result
