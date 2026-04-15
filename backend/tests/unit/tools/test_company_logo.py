"""
Unit tests for company_logo tool.
"""

import pytest
from app.tools.company_logo import get_company_logo

# Get the underlying function from the StructuredTool
get_company_logo_func = get_company_logo.func


@pytest.mark.unit
class TestGetCompanyLogo:
    """Test suite for get_company_logo tool."""

    def test_get_company_logo_valid_ticker(self, mock_yfinance_ticker):
        """
        Test logo retrieval with valid ticker.

        Given: Mock yfinance returns company info
        When: get_company_logo_func("AAPL") is called
        Then: Returns dict with ticker, company_name, and logo_url
        """
        # When
        result = get_company_logo_func("AAPL")

        # Then
        assert isinstance(result, dict)
        assert "ticker" in result
        assert "company_name" in result
        assert "logo_url" in result
        assert result["ticker"] == "AAPL"
        assert result["company_name"] == "Apple Inc."
        assert "parqet.com" in result["logo_url"]
        assert "AAPL" in result["logo_url"]

    def test_get_company_logo_normalizes_ticker(self, mock_yfinance_ticker):
        """
        Test that ticker is normalized to uppercase.

        Given: Lowercase ticker provided
        When: get_company_logo is called
        Then: Ticker is converted to uppercase
        """
        # When
        result = get_company_logo_func("  aapl  ")  # lowercase with spaces

        # Then
        assert result["ticker"] == "AAPL"
        assert "AAPL" in result["logo_url"]

    def test_get_company_logo_uses_shortname_fallback(self, mocker):
        """
        Test fallback to shortName when longName is not available.

        Given: yfinance info has shortName but not longName
        When: get_company_logo is called
        Then: Uses shortName for company_name
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.info = {
            "shortName": "Apple",
            # No longName
        }
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_company_logo_func("AAPL")

        # Then
        assert result["company_name"] == "Apple"

    def test_get_company_logo_uses_ticker_fallback(self, mocker):
        """
        Test fallback to ticker when neither longName nor shortName available.

        Given: yfinance info has no company names
        When: get_company_logo is called
        Then: Uses ticker symbol for company_name
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.info = {}  # No names
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_company_logo_func("TEST")

        # Then
        assert result["company_name"] == "TEST"

    def test_get_company_logo_invalid_ticker(self, mocker):
        """
        Test error handling for invalid ticker.

        Given: yfinance raises exception
        When: get_company_logo is called
        Then: Returns error message
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.info = property(lambda self: (_ for _ in ()).throw(Exception("Invalid")))
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_company_logo_func("INVALID")

        # Then
        assert isinstance(result, str)
        assert "Unable to fetch logo" in result

    def test_get_company_logo_url_format(self, mock_yfinance_ticker):
        """
        Test that logo URL follows expected format.

        Verifies Parqet API URL structure.
        """
        # When
        result = get_company_logo_func("AAPL")

        # Then
        assert result["logo_url"] == "https://assets.parqet.com/logos/symbol/AAPL"
