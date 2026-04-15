"""
Stock price retrieval tool with multi-currency support.
"""

from langchain.tools import tool
from loguru import logger
from typing import Dict, Any
import yfinance as yf
from app.core.cache import cache
from app.services.currency_service import get_currency_service


@cache(ttl=60, include_timestamp=True)  # 60 second cache
def _fetch_stock_price_cached(ticker: str) -> Dict[str, Any]:
    """
    Internal cached function to fetch stock price in USD.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with price and ticker info (always in USD)
    """
    stock = yf.Ticker(ticker)
    price = stock.history(period="1d")["Close"].iloc[-1]
    return {
        "ticker": ticker,
        "price_usd": float(price),
        "cached_at": None  # Will be added by cache decorator
    }


@tool(
    "get_stock_price",
    description="""Retrieves the most recent closing price for a given stock ticker symbol.
    Use this when users ask about current stock prices or want to know what a stock is trading at.
    Automatically converts prices to the user's preferred currency (EUR, GBP, CHF, or USD).
    Returns price with timestamp showing data freshness (cached for 60 seconds).

    Parameters:
    - ticker: Stock ticker symbol (e.g., "AAPL", "TSLA")
    - user_currency: Target currency for the price (default: "USD"). Options: "EUR", "GBP", "CHF", "USD"

    Example: get_stock_price("AAPL", "EUR") returns Apple's price in euros.""",
)
def get_stock_price(ticker: str, user_currency: str = "USD") -> str:
    """
    Fetch the current stock price for a given ticker symbol in the user's preferred currency.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        user_currency: Target currency code (e.g., "EUR", "GBP", "CHF", "USD")

    Returns:
        Formatted price string with timestamp or error message
    """
    logger.info(f"Getting stock price for ticker: {ticker} in {user_currency}")
    try:
        # Fetch USD price (cached)
        result = _fetch_stock_price_cached(ticker)
        price_usd = result['price_usd']
        cached_at = result.get('cached_at', '')

        # Convert to user's currency
        currency_service = get_currency_service()
        price_converted = currency_service.convert(price_usd, "USD", user_currency)

        # Format with appropriate currency symbol
        formatted_price = currency_service.format_currency(price_converted, user_currency)

        timestamp_info = f" (as of {cached_at})" if cached_at else ""
        logger.info(f"Stock price for {ticker}: {formatted_price}{timestamp_info}")
        return f"{formatted_price}{timestamp_info}"

    except Exception as e:
        logger.error(f"Error fetching price for {ticker}: {e}")
        return f"Unable to fetch price for {ticker}. Please verify the ticker symbol is correct."
