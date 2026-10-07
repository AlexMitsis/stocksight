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
 * Format a number as currency (e.g. €1,234.56, CHF 1,234.56).
 * With showSign, positive values get a leading "+".
 */
export function formatCurrency(
  amount: string | number | null | undefined,
  currency: string = 'USD',
  showSign: boolean = false
): string {
  const numValue = toNumber(amount);
  const formatted = new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(numValue);
  return showSign && numValue >= 0 ? `+${formatted}` : formatted;
}

/**
 * Format a quantity, removing trailing zeros
 */
export function formatQuantity(quantity: string | number | null | undefined): string {
  const numValue = toNumber(quantity);
  return numValue.toFixed(6).replace(/\.?0+$/, '');
}
