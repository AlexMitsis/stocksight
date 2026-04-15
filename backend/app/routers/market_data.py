"""
Market data router for fetching stock prices and historical data.
"""

from fastapi import APIRouter, HTTPException
from datetime import date, datetime, timedelta
import yfinance as yf
from loguru import logger

router = APIRouter(prefix="/api/market-data", tags=["market-data"])


@router.get("/vwap/{ticker}")
async def get_vwap_for_date(ticker: str, date: str):
    """
    Get VWAP (Volume-Weighted Average Price) for a ticker on a specific date.

    Args:
        ticker: Stock ticker symbol (e.g., AAPL)
        date: Date in YYYY-MM-DD format (e.g., 2024-01-15)

    Returns:
        {
            "ticker": "AAPL",
            "date": "2024-01-15",
            "vwap": 185.50,
            "open": 184.00,
            "high": 186.20,
            "low": 183.80,
            "close": 185.30,
            "volume": 52000000,
            "method": "approximation"
            "note": "Non-trading day" (optional)
        }

    Raises:
        400: Invalid date format or future date
        404: No data available for ticker/date
    """
    logger.info(f"Fetching VWAP for {ticker} on {date}")

    try:
        # Parse and validate date
        target_date = datetime.strptime(date, "%Y-%m-%d").date()

        # Don't allow future dates
        today = datetime.now().date()
        if target_date > today:
            raise HTTPException(
                status_code=400,
                detail="Cannot fetch VWAP for future dates"
            )

        # Fetch historical data from yfinance
        # Get a few days of data to ensure we have the target date
        end_date = target_date + timedelta(days=2)
        start_date = target_date - timedelta(days=5)

        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)

        if hist.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No market data found for {ticker} on {date}"
            )

        # Find the exact date in the data
        # yfinance returns data with timezone-aware datetime index
        # We need to match by date only
        matching_rows = hist[hist.index.date == target_date]

        note = None
        if matching_rows.empty:
            # Target date might be a weekend/holiday
            # Return the most recent trading day before target date
            previous_data = hist[hist.index.date < target_date]
            if previous_data.empty:
                raise HTTPException(
                    status_code=404,
                    detail=f"No trading data available for {ticker} near {date}"
                )
            data_row = previous_data.iloc[-1]
            actual_date = data_row.name.date()
            note = "Non-trading day"
            logger.warning(f"{date} is not a trading day for {ticker}, using {actual_date}")
        else:
            data_row = matching_rows.iloc[0]
            actual_date = target_date

        # Calculate VWAP approximation: (High + Low + Close) / 3
        # This is a standard approximation when tick data isn't available
        high = float(data_row['High'])
        low = float(data_row['Low'])
        close = float(data_row['Close'])
        open_price = float(data_row['Open'])
        volume = int(data_row['Volume'])

        vwap = (high + low + close) / 3

        logger.info(f"VWAP for {ticker} on {actual_date}: ${vwap:.2f}")

        response = {
            "ticker": ticker.upper(),
            "date": str(actual_date),
            "vwap": round(vwap, 2),
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": volume,
            "method": "approximation",  # (High + Low + Close) / 3
        }

        if note:
            response["note"] = note

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date format. Use YYYY-MM-DD: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error fetching VWAP for {ticker} on {date}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market data: {str(e)}"
        )
