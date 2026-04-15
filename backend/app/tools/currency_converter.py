"""
Currency conversion tool for explicit currency conversions.

This tool allows agents to convert amounts between supported currencies
on-demand when users explicitly request currency conversions.
"""

from langchain.tools import tool
from loguru import logger
from app.services.currency_service import get_currency_service


@tool(
    "convert_currency",
    description="""Converts an amount from one currency to another using real-time exchange rates.
    Use this when users explicitly ask to convert between currencies or want to compare values across currencies.

    Supported currencies: EUR, GBP, CHF, USD

    Parameters:
    - amount: The numeric amount to convert (e.g., 100, 1000.50)
    - from_currency: Source currency code (e.g., "USD", "EUR")
    - to_currency: Target currency code (e.g., "EUR", "GBP")

    Examples:
    - convert_currency(100, "USD", "EUR") - Convert $100 to euros
    - convert_currency(50, "GBP", "CHF") - Convert £50 to Swiss francs
    - convert_currency(1000, "EUR", "USD") - Convert €1000 to dollars

    Returns formatted amount with appropriate currency symbol.
    Exchange rates are cached for 1 hour.""",
)
def convert_currency(amount: float, from_currency: str, to_currency: str) -> str:
    """
    Convert an amount between two currencies.

    Args:
        amount: Amount to convert
        from_currency: Source currency code (e.g., "USD")
        to_currency: Target currency code (e.g., "EUR")

    Returns:
        Formatted conversion result string or error message
    """
    logger.info(f"Converting {amount} {from_currency} to {to_currency}")

    try:
        currency_service = get_currency_service()

        # Validate currencies
        if not currency_service.is_supported(from_currency):
            return f"Unsupported source currency: {from_currency}. Supported currencies: EUR, GBP, CHF, USD"

        if not currency_service.is_supported(to_currency):
            return f"Unsupported target currency: {to_currency}. Supported currencies: EUR, GBP, CHF, USD"

        # Convert
        converted_amount = currency_service.convert(amount, from_currency, to_currency)

        # Format both amounts with symbols
        from_formatted = currency_service.format_currency(amount, from_currency)
        to_formatted = currency_service.format_currency(converted_amount, to_currency)

        result = f"{from_formatted} = {to_formatted}"
        logger.info(f"Conversion result: {result}")
        return result

    except Exception as e:
        logger.error(f"Error converting {amount} {from_currency} to {to_currency}: {e}")
        return f"Unable to convert currency. Please check the currency codes and try again."


@tool(
    "get_exchange_rate",
    description="""Gets the current exchange rate between two currencies.
    Use this when users want to know the exchange rate without converting a specific amount.

    Supported currencies: EUR, GBP, CHF, USD

    Parameters:
    - from_currency: Source currency code (e.g., "USD", "EUR")
    - to_currency: Target currency code (e.g., "EUR", "GBP")

    Examples:
    - get_exchange_rate("USD", "EUR") - Get USD to EUR exchange rate
    - get_exchange_rate("GBP", "CHF") - Get GBP to CHF exchange rate

    Returns the exchange rate (1 from_currency = X to_currency).
    Exchange rates are cached for 1 hour.""",
)
def get_exchange_rate(from_currency: str, to_currency: str) -> str:
    """
    Get the exchange rate between two currencies.

    Args:
        from_currency: Source currency code (e.g., "USD")
        to_currency: Target currency code (e.g., "EUR")

    Returns:
        Formatted exchange rate string or error message
    """
    logger.info(f"Getting exchange rate from {from_currency} to {to_currency}")

    try:
        currency_service = get_currency_service()

        # Validate currencies
        if not currency_service.is_supported(from_currency):
            return f"Unsupported source currency: {from_currency}. Supported currencies: EUR, GBP, CHF, USD"

        if not currency_service.is_supported(to_currency):
            return f"Unsupported target currency: {to_currency}. Supported currencies: EUR, GBP, CHF, USD"

        # Get rate by converting 1 unit
        rate = currency_service.convert(1.0, from_currency, to_currency)

        # Format symbols
        from_symbol = currency_service.CURRENCY_SYMBOLS.get(from_currency, from_currency)
        to_symbol = currency_service.CURRENCY_SYMBOLS.get(to_currency, to_currency)

        result = f"1 {from_symbol} = {rate:.4f} {to_symbol}"
        logger.info(f"Exchange rate: {result}")
        return result

    except Exception as e:
        logger.error(f"Error getting exchange rate {from_currency} to {to_currency}: {e}")
        return f"Unable to get exchange rate. Please check the currency codes and try again."
