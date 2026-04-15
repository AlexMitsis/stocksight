"""
Balance sheet retrieval tool with multi-currency support.
"""

from langchain.tools import tool
from loguru import logger
from typing import Dict, Any
import yfinance as yf
from app.core.cache import cache
from app.services.currency_service import get_currency_service


@cache(ttl=86400, include_timestamp=True)  # 24 hour cache
def _fetch_balance_sheet_cached(ticker: str) -> Dict[str, Any]:
    """
    Internal cached function to fetch balance sheet.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Dictionary with balance sheet data
    """
    stock = yf.Ticker(ticker)
    balance_sheet = stock.balance_sheet

    if balance_sheet is None or balance_sheet.empty:
        raise ValueError(f"No balance sheet data available for {ticker}")

    return {
        "ticker": ticker,
        "data": balance_sheet.to_dict()
    }


@tool(
    "get_balance_sheet",
    description="""Retrieves the company's balance sheet showing assets, liabilities, and shareholders equity.
    Use this for fundamental analysis, financial health assessment, and valuation analysis.
    Returns detailed financial statement data including current assets, total debt, cash positions, etc.
    Automatically converts all financial values to the user's preferred currency (EUR, GBP, CHF, or USD).
    Essential for evaluating company solvency, liquidity ratios, and overall financial strength.
    Data is cached for 24 hours as balance sheets don't change frequently.

    Parameters:
    - ticker: Stock ticker symbol (e.g., "AAPL")
    - user_currency: Target currency (default: "USD"). Options: "EUR", "GBP", "CHF", "USD"

    Example: get_balance_sheet("AAPL", "EUR") for Apple's balance sheet in euros.
    Use for analyzing debt-to-equity ratios, working capital, and asset composition.""",
)
def get_balance_sheet(ticker: str, user_currency: str = "USD") -> Dict[str, Any] | str:
    """
    Fetch balance sheet data for fundamental financial analysis in user's preferred currency.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        user_currency: Target currency code (e.g., "EUR", "GBP", "CHF", "USD")

    Returns:
        Dictionary with balance sheet data or error message
    """
    logger.info(f"Getting balance sheet for ticker: {ticker} in {user_currency}")
    try:
        result = _fetch_balance_sheet_cached(ticker)
        cached_at = result.get('cached_at', '')
        logger.info(f"Retrieved balance sheet for {ticker} (cached: {bool(cached_at)})")

        # Convert financial values to user's currency if needed
        data = result['data'].copy()
        if user_currency != "USD":
            currency_service = get_currency_service()

            # Convert all numeric values (typically financial amounts are in USD)
            for date_col, values in data.items():
                if isinstance(values, dict):
                    converted_values = {}
                    for item_name, amount in values.items():
                        if isinstance(amount, (int, float)) and amount is not None:
                            converted_amount = currency_service.convert(amount, "USD", user_currency)
                            converted_values[item_name] = converted_amount
                        else:
                            converted_values[item_name] = amount
                    data[date_col] = converted_values

        # Return the data dict with metadata
        return {
            **data,
            '_metadata': {
                'ticker': ticker,
                'currency': user_currency,
                'cached_at': cached_at
            }
        }
    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.error(f"Error fetching balance sheet for {ticker}: {e}")
        return f"Unable to fetch balance sheet for {ticker}. This may not be available for all securities."
