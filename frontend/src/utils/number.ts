/**
 * Utility functions for handling numeric values from API (Decimal types come as strings)
 */

/**
 * Safely convert a value to a number, handling strings from Decimal types
 */
export function toNumber(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  return typeof value === 'number' ? value : parseFloat(value) || 0;
}

/**
 * Format a number as currency with proper symbol placement
 */
export function formatCurrency(
  amount: string | number | null | undefined,
  currency: string = 'USD'
): string {
  const numValue = toNumber(amount);
  const formatted = numValue.toFixed(2);

  const symbols: Record<string, string> = {
    EUR: '€',
    GBP: '£',
    USD: '$',
    CHF: 'CHF ',
  };

  const symbol = symbols[currency] || '$';

  // CHF goes before the number, others vary by locale
  if (currency === 'CHF') {
    return `${symbol}${formatted}`;
  } else if (currency === 'EUR') {
    return `€${formatted}`;
  } else {
    return `${symbol}${formatted}`;
  }
}

/**
 * Format a quantity, removing trailing zeros
 */
export function formatQuantity(quantity: string | number | null | undefined): string {
  const numValue = toNumber(quantity);
  return numValue.toFixed(6).replace(/\.?0+$/, '');
}
