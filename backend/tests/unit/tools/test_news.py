"""
Unit tests for news tool.
"""

import pytest
from app.tools.news import get_stock_news

# Get the underlying function from the StructuredTool
get_stock_news_func = get_stock_news.func


@pytest.mark.unit
class TestGetStockNews:
    """Test suite for get_stock_news tool."""

    def test_get_stock_news_valid_ticker(self, mock_yfinance_ticker):
        """
        Test news retrieval with valid ticker.

        Given: Mock yfinance returns news articles
        When: get_stock_news_func("AAPL") is called
        Then: Returns list of news articles
        """
        # When
        result = get_stock_news_func("AAPL")

        # Then
        assert isinstance(result, list)
        assert len(result) > 0
        # Check first article structure
        article = result[0]
        assert "title" in article
        assert "publisher" in article
        assert "link" in article
        assert "publish_time" in article

    def test_get_stock_news_no_articles(self, mocker):
        """
        Test handling when no news is available.

        Given: yfinance returns empty news list
        When: get_stock_news is called
        Then: Returns "no news" message
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.news = []
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_stock_news_func("TEST")

        # Then
        assert isinstance(result, str)
        assert "No recent news found" in result

    def test_get_stock_news_limits_to_10(self, mocker):
        """
        Test that news is limited to 10 most recent articles.

        Given: yfinance returns 20 news articles
        When: get_stock_news is called
        Then: Returns only 10 articles
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.news = [
            {
                "title": f"Article {i}",
                "publisher": "Test",
                "link": f"http://test.com/{i}",
                "providerPublishTime": i,
            }
            for i in range(20)
        ]
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_stock_news_func("TEST")

        # Then
        assert isinstance(result, list)
        assert len(result) == 10

    def test_get_stock_news_invalid_ticker(self, mocker):
        """
        Test error handling for invalid ticker.

        Given: yfinance raises exception
        When: get_stock_news is called
        Then: Returns error message
        """
        # Given
        mock_ticker = mocker.MagicMock()
        mock_ticker.news = property(lambda self: (_ for _ in ()).throw(Exception("Invalid")))
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)

        # When
        result = get_stock_news_func("INVALID")

        # Then
        assert isinstance(result, str)
        assert "Unable to fetch news" in result
