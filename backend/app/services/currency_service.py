"""
Currency service for real-time and historical exchange rate conversion with caching.

This service fetches exchange rates from a free API and caches them for 1 hour
to minimize API calls and improve performance. Historical rates are fetched
from yfinance and cached in-memory using LRU cache.
"""

from typing import Dict, Optional, Union
from functools import lru_cache
from datetime import date, datetime, timedelta
import httpx
import yfinance as yf
from loguru import logger


def _normalize_date(d: Union[date, datetime]) -> date:
    """
    Normalize a date or datetime to a date object.

    This ensures consistent LRU cache keys and prevents datetime vs date mismatches.

    Args:
        d: A date or datetime object

    Returns:
        A date object (extracts date from datetime if needed)
    """
    if isinstance(d, datetime):
        return d.date()
    return d


class CurrencyService:
    """
    Service for currency conversion with automatic caching.

    Supports EUR, GBP, CHF, and USD with fallback to USD if conversion fails.
    Exchange rates are cached for 1 hour to reduce API calls.
    """

    # Free API endpoint for exchange rates (base: USD)
    BASE_URL = "https://api.exchangerate-api.com/v4/latest/USD"

    # Supported currencies
    SUPPORTED_CURRENCIES = ["EUR", "GBP", "CHF", "USD"]

    # Currency symbols for formatting
    CURRENCY_SYMBOLS = {
        "EUR": "€",
        "GBP": "£",
        "CHF": "CHF",
        "USD": "$"
    }

    def __init__(self):
        """Initialize the currency service with cache."""
        self._cache: Optional[Dict[str, float]] = None
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl = timedelta(hours=1)
        logger.info("CurrencyService initialized with 1-hour cache TTL")

    def get_exchange_rates(self) -> Dict[str, float]:
        """
        Fetch latest exchange rates with 1-hour caching.

        Returns exchange rates with USD as base currency.
        If API call fails, returns last cached rates or raises exception.

        Returns:
            Dictionary of currency codes to exchange rates (e.g., {"EUR": 0.92, "GBP": 0.79})

        Raises:
            httpx.HTTPError: If API call fails and no cache available
        """
        # Check cache validity
        if self._cache is not None and self._cache_timestamp is not None:
            cache_age = datetime.now() - self._cache_timestamp
            if cache_age < self._cache_ttl:
                logger.debug(f"Using cached exchange rates (age: {cache_age.total_seconds():.0f}s)")
                return self._cache

        # Fetch fresh rates
        try:
            logger.info("Fetching fresh exchange rates from API")
            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.BASE_URL)
                response.raise_for_status()
                data = response.json()

                rates = data.get("rates", {})

                # Validate we have the currencies we need
                for currency in self.SUPPORTED_CURRENCIES:
                    if currency not in rates and currency != "USD":
                        logger.warning(f"Currency {currency} not in API response")

                # Cache the results
                self._cache = rates
                self._cache_timestamp = datetime.now()

                logger.info(f"Fetched exchange rates for {len(rates)} currencies")
                return rates

        except Exception as e:
            logger.error(f"Error fetching exchange rates: {e}")

            # Fall back to cache if available
            if self._cache is not None:
                logger.warning("Using stale cached rates due to API error")
                return self._cache

            # No cache available, re-raise
            raise

    def convert(
        self,
        amount: float,
        from_currency: str,
        to_currency: str
    ) -> float:
        """
        Convert amount between currencies.

        All conversions go through USD as the base currency:
        1. Convert from_currency to USD (if not already USD)
        2. Convert USD to to_currency (if not USD)

        Args:
            amount: Amount to convert
            from_currency: Source currency code (e.g., "USD")
            to_currency: Target currency code (e.g., "EUR")

        Returns:
            Converted amount rounded to 2 decimal places

        Example:
            >>> service = CurrencyService()
            >>> service.convert(100.0, "USD", "EUR")
            92.15
        """
        # Validate currencies
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency not in self.SUPPORTED_CURRENCIES:
            logger.warning(f"Unsupported from_currency: {from_currency}, falling back to USD")
            from_currency = "USD"

        if to_currency not in self.SUPPORTED_CURRENCIES:
            logger.warning(f"Unsupported to_currency: {to_currency}, falling back to USD")
            to_currency = "USD"

        # No conversion needed
        if from_currency == to_currency:
            return round(amount, 2)

        try:
            rates = self.get_exchange_rates()

            # Convert to USD first (if not already USD)
            amount_usd = amount
            if from_currency != "USD":
                rate_from = rates.get(from_currency)
                if rate_from is None:
                    logger.error(f"No exchange rate for {from_currency}, falling back to USD")
                    return round(amount, 2)
                amount_usd = amount / rate_from

            # Convert from USD to target currency (if not USD)
            if to_currency != "USD":
                rate_to = rates.get(to_currency)
                if rate_to is None:
                    logger.error(f"No exchange rate for {to_currency}, falling back to USD")
                    return round(amount_usd, 2)
                amount_usd = amount_usd * rate_to

            result = round(amount_usd, 2)
            logger.debug(f"Converted {amount} {from_currency} to {result} {to_currency}")
            return result

        except Exception as e:
            logger.error(f"Error during currency conversion: {e}, returning original amount")
            return round(amount, 2)

    def format_currency(self, amount: float, currency: str) -> str:
        """
        Format amount with appropriate currency symbol.

        Args:
            amount: Amount to format
            currency: Currency code (e.g., "EUR", "USD")

        Returns:
            Formatted string with currency symbol (e.g., "€100.50", "$100.50")

        Example:
            >>> service.format_currency(100.50, "EUR")
            '€100.50'
            >>> service.format_currency(100.50, "USD")
            '$100.50'
        """
        currency = currency.upper()
        symbol = self.CURRENCY_SYMBOLS.get(currency, currency)

        # Format with thousands separator
        formatted_amount = f"{amount:,.2f}"

        # EUR and CHF typically have symbol before
        # GBP and USD have symbol before (GBP: £, USD: $)
        return f"{symbol}{formatted_amount}"

    def is_supported(self, currency: str) -> bool:
        """
        Check if a currency is supported.

        Args:
            currency: Currency code to check

        Returns:
            True if currency is supported, False otherwise
        """
        return currency.upper() in self.SUPPORTED_CURRENCIES

    def get_historical_rate(
        self,
        from_currency: str,
        to_currency: str,
        at_date: Union[date, datetime]
    ) -> float:
        """
        Get exchange rate for a specific historical date using yfinance.

        Uses currency pairs like EURUSD=X to fetch historical forex data.
        Results are cached in-memory using LRU cache for performance.

        Args:
            from_currency: Source currency code (e.g., "EUR")
            to_currency: Target currency code (e.g., "USD")
            at_date: Historical date to get rate for (date or datetime)

        Returns:
            Exchange rate for the given date. Falls back to current rate
            if historical rate cannot be fetched (with error logged).

        Example:
            >>> service = CurrencyService()
            >>> service.get_historical_rate("EUR", "USD", date(2024, 1, 15))
            1.0872
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        # Normalize to date (in case datetime is passed)
        normalized_date = _normalize_date(at_date)

        # No conversion needed
        if from_currency == to_currency:
            return 1.0

        # Use the cached helper function
        rate = _fetch_historical_rate_cached(from_currency, to_currency, normalized_date)

        if rate is not None:
            return rate

        # Fallback to current rate with error log
        logger.error(
            f"Failed to get historical exchange rate for {from_currency}/{to_currency} "
            f"on {normalized_date}. Using current rate as fallback."
        )
        return self._get_current_rate(from_currency, to_currency)

    def _get_current_rate(self, from_currency: str, to_currency: str) -> float:
        """
        Get current exchange rate between two currencies.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code

        Returns:
            Current exchange rate
        """
        if from_currency == to_currency:
            return 1.0

        try:
            rates = self.get_exchange_rates()

            # Convert through USD
            # from_currency -> USD -> to_currency
            rate_from = rates.get(from_currency, 1.0) if from_currency != "USD" else 1.0
            rate_to = rates.get(to_currency, 1.0) if to_currency != "USD" else 1.0

            if from_currency == "USD":
                return rate_to
            elif to_currency == "USD":
                return 1.0 / rate_from
            else:
                # Cross rate: from_currency -> USD -> to_currency
                return rate_to / rate_from

        except Exception as e:
            logger.error(f"Error getting current rate: {e}")
            return 1.0

    def convert_at_date(
        self,
        amount: float,
        from_currency: str,
        to_currency: str,
        at_date: Union[date, datetime]
    ) -> float:
        """
        Convert amount using historical exchange rate for a specific date.

        Args:
            amount: Amount to convert
            from_currency: Source currency code (e.g., "EUR")
            to_currency: Target currency code (e.g., "USD")
            at_date: Historical date to use for exchange rate (date or datetime)

        Returns:
            Converted amount rounded to 2 decimal places

        Example:
            >>> service = CurrencyService()
            >>> service.convert_at_date(1000.0, "EUR", "USD", date(2024, 1, 15))
            1087.20
        """
        from_currency = from_currency.upper()
        to_currency = to_currency.upper()

        if from_currency == to_currency:
            return round(amount, 2)

        rate = self.get_historical_rate(from_currency, to_currency, at_date)
        return round(amount * rate, 2)


@lru_cache(maxsize=500)
def _fetch_historical_rate_cached(
    from_currency: str,
    to_currency: str,
    at_date: date
) -> Optional[float]:
    """
    Fetch historical exchange rate from yfinance with LRU caching.

    This is a module-level function to enable lru_cache decorator.
    Cache stores up to 500 date/pair combinations.

    Handles forex pair naming conventions by trying both direct and inverse pairs.
    For example, USDEUR=X may not exist, but EURUSD=X does - we fetch that and invert.

    Args:
        from_currency: Source currency code
        to_currency: Target currency code
        at_date: Date to fetch rate for

    Returns:
        Exchange rate or None if fetch failed
    """
    # Fetch a 5-day window to handle weekends/holidays
    start = at_date
    end = at_date + timedelta(days=5)

    # Try direct pair first (e.g., EURUSD=X for EUR to USD)
    direct_pair = f"{from_currency}{to_currency}=X"
    rate = _try_fetch_forex_pair(direct_pair, start, end)

    if rate is not None:
        logger.debug(f"Historical rate {from_currency}/{to_currency} on {at_date}: {rate:.6f} (direct)")
        return rate

    # Try inverse pair and invert the rate (e.g., use EURUSD=X for USD to EUR)
    inverse_pair = f"{to_currency}{from_currency}=X"
    inverse_rate = _try_fetch_forex_pair(inverse_pair, start, end)

    if inverse_rate is not None and inverse_rate != 0:
        rate = 1.0 / inverse_rate
        logger.debug(f"Historical rate {from_currency}/{to_currency} on {at_date}: {rate:.6f} (inverted from {inverse_pair})")
        return rate

    logger.warning(f"No historical data for {from_currency}/{to_currency} on {at_date} (tried {direct_pair} and {inverse_pair})")
    return None


def _try_fetch_forex_pair(pair: str, start: date, end: date) -> Optional[float]:
    """
    Try to fetch a forex pair from yfinance.

    Args:
        pair: Forex pair symbol (e.g., "EURUSD=X")
        start: Start date
        end: End date

    Returns:
        Close price or None if not available
    """
    try:
        ticker = yf.Ticker(pair)
        hist = ticker.history(start=start, end=end)

        if not hist.empty:
            return float(hist["Close"].iloc[0])

    except Exception as e:
        logger.debug(f"Failed to fetch {pair}: {e}")

    return None


# Global singleton instance
_currency_service: Optional[CurrencyService] = None


def get_currency_service() -> CurrencyService:
    """
    Get or create the global CurrencyService instance.

    Returns:
        Singleton instance of CurrencyService
    """
    global _currency_service
    if _currency_service is None:
        _currency_service = CurrencyService()
    return _currency_service
