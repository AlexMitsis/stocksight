"""
Stock news retrieval tool.
"""

from langchain.tools import tool
from loguru import logger
from typing import List, Dict, Any
import yfinance as yf


@tool(
    "get_stock_news",
    description="""Retrieves the latest news articles and press releases related to a stock.
    Use this for sentiment analysis, identifying catalysts, and understanding recent developments.
    Returns news headlines, summaries, publishers, and timestamps.
    Critical for understanding market-moving events like earnings reports, product launches,
    regulatory changes, management updates, and analyst ratings.
    Always analyze news context when significant price movements occur.""",
)
def get_stock_news(ticker: str) -> List[Dict[str, Any]] | str:
    """
    Fetch recent news for sentiment analysis and catalyst identification.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")

    Returns:
        List of news articles with metadata or error message
    """
    logger.info(f"Getting news for ticker: {ticker}")
    try:
        stock = yf.Ticker(ticker)
        news = stock.news

        if not news:
            return f"No recent news found for {ticker}."

        logger.info(f"Retrieved {len(news)} news articles for {ticker}")

        # Format news in a more readable way
        formatted_news = []
        for article in news[:10]:  # Limit to 10 most recent
            formatted_news.append(
                {
                    "title": article.get("title", "N/A"),
                    "publisher": article.get("publisher", "N/A"),
                    "link": article.get("link", "N/A"),
                    "publish_time": article.get("providerPublishTime", "N/A"),
                }
            )

        return formatted_news
    except Exception as e:
        logger.error(f"Error fetching news for {ticker}: {e}")
        return f"Unable to fetch news for {ticker}."
