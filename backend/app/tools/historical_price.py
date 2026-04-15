"""
Historical stock price retrieval tool with multi-currency support.
"""

from langchain.tools import tool
from loguru import logger
from typing import Dict, Any
import yfinance as yf
from app.core.cache import cache
from app.services.currency_service import get_currency_service


@cache(ttl=3600, include_timestamp=True)  # 1 hour cache
def _fetch_historical_price_cached(ticker: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Internal cached function to fetch historical price data.

    Args:
        ticker: Stock ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Dictionary with historical data
    """
    stock = yf.Ticker(ticker)
    history = stock.history(start=start_date, end=end_date)

    if history.empty:
        raise ValueError(f"No historical data found for {ticker} between {start_date} and {end_date}")

    return {
        "ticker": ticker,
        "start_date": start_date,
        "end_date": end_date,
        "data_points": len(history),
        "data": history.to_dict()
    }


@tool(
    "get_historical_stock_price",
    description="""Retrieves historical daily stock prices over a specified date range.
    Use this for trend analysis, volatility assessment, performance comparisons, and identifying patterns.
    Dates should be in YYYY-MM-DD format. Returns a dictionary with dates and corresponding OHLCV data.
    Automatically converts prices to the user's preferred currency (EUR, GBP, CHF, or USD).
    Historical data is cached for 1 hour since past prices don't change.

    Parameters:
    - ticker: Stock ticker symbol (e.g., "TSLA")
    - start_date: Start date in YYYY-MM-DD format
    - end_date: End date in YYYY-MM-DD format
    - user_currency: Target currency (default: "USD"). Options: "EUR", "GBP", "CHF", "USD"

    Example: get_historical_stock_price("TSLA", "2024-01-01", "2024-12-01", "EUR") for YTD Tesla in euros.
    Useful for calculating returns, analyzing price movements, and identifying support/resistance levels.""",
)
def get_historical_stock_price(ticker: str, start_date: str, end_date: str, user_currency: str = "USD") -> Dict[str, Any] | str:
    """
    Fetch historical stock price data for technical and trend analysis in user's preferred currency.

    Args:
        ticker: Stock ticker symbol (e.g., "TSLA")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        user_currency: Target currency code (e.g., "EUR", "GBP", "CHF", "USD")

    Returns:
        Dictionary with historical OHLCV data or error message
    """
    logger.info(f"Getting historical stock price for {ticker} from {start_date} to {end_date} in {user_currency}")
    try:
        result = _fetch_historical_price_cached(ticker, start_date, end_date)
        cached_at = result.get('cached_at', '')
        logger.info(f"Retrieved {result['data_points']} historical data points for {ticker} (cached: {bool(cached_at)})")

        # Convert price data to user's currency if needed
        data = result['data'].copy()
        if user_currency != "USD":
            currency_service = get_currency_service()

            # Convert OHLCV columns
            price_columns = ['Open', 'High', 'Low', 'Close']
            for col in price_columns:
                if col in data:
                    # Convert each date's price
                    converted_prices = {}
                    for date_str, price_usd in data[col].items():
                        if price_usd is not None:
                            converted_price = currency_service.convert(price_usd, "USD", user_currency)
                            converted_prices[date_str] = converted_price
                        else:
                            converted_prices[date_str] = None
                    data[col] = converted_prices

        # Return the data with metadata
        return {
            **data,
            '_metadata': {
                'ticker': ticker,
                'start_date': start_date,
                'end_date': end_date,
                'data_points': result['data_points'],
                'currency': user_currency,
                'cached_at': cached_at
            }
        }
    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.error(f"Error fetching historical data for {ticker}: {e}")
        return f"Unable to fetch historical data for {ticker}. Please check the ticker and date format (YYYY-MM-DD)."
