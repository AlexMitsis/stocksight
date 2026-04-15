"""
Company logo retrieval tool.
"""

from langchain.tools import tool
from loguru import logger
from typing import Dict, Any
import yfinance as yf
from app.core.cache import cache


@cache(ttl=604800, include_timestamp=True)  # 7 day cache
def _fetch_company_logo_cached(ticker: str) -> Dict[str, Any]:
    """
    Internal cached function to fetch company logo.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with logo information
    """
    # Normalize ticker to uppercase
    ticker = ticker.upper().strip()

    # Get company name for context
    stock = yf.Ticker(ticker)
    info = stock.info
    company_name = info.get("longName", info.get("shortName", ticker))

    # Use Parqet's free logo API (works reliably for major stocks)
    logo_url = f"https://assets.parqet.com/logos/symbol/{ticker}"

    return {
        "ticker": ticker,
        "company_name": company_name,
        "logo_url": logo_url
    }


@tool(
    "get_company_logo",
    description="""Retrieves the company logo URL for a given stock ticker symbol.
    Use this when you need to display or reference a company's visual branding.
    Returns a direct URL to the company's logo image that can be embedded or displayed.
    Essential for visual presentation, branding context, and professional user interfaces.
    Logo URLs are cached for 7 days as they rarely change.
    Example: Use when introducing a company, creating visual stock comparisons, or enhancing UI with brand logos.""",
)
def get_company_logo(ticker: str) -> Dict[str, Any] | str:
    """
    Fetch company logo URL using Parqet's free logo service.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")

    Returns:
        Dictionary with ticker, company name, and logo URL or error message
    """
    logger.info(f"Getting company logo for ticker: {ticker}")
    try:
        result = _fetch_company_logo_cached(ticker)
        logger.info(f"Generated logo URL for {result['ticker']}: {result['logo_url']}")
        return result
    except Exception as e:
        logger.error(f"Error fetching logo for {ticker}: {e}")
        return f"Unable to fetch logo for {ticker}."
