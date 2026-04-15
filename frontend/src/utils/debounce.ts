/**
 * Debounce utility for delaying function execution
 *
 * Creates a debounced version of a function that delays its execution
 * until after a specified wait time has elapsed since the last call.
 *
 * @param func - The function to debounce
 * @param wait - The number of milliseconds to delay
 * @returns A debounced version of the function with a cancel method
 *
 * @example
 * const debouncedSearch = debounce((query: string) => {
 *   console.log('Searching for:', query);
 * }, 500);
 *
 * // These calls will be debounced - only the last one will execute
 * debouncedSearch('a');
 * debouncedSearch('ap');
 * debouncedSearch('app');  // Only this one executes after 500ms
 *
 * // Cancel pending execution
 * debouncedSearch.cancel();
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): T & { cancel: () => void } {
  let timeout: NodeJS.Timeout | null = null;

  const debounced = function(this: any, ...args: any[]) {
    const later = () => {
      timeout = null;
      func.apply(this, args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  } as T & { cancel: () => void };

  debounced.cancel = () => {
    if (timeout) {
      clearTimeout(timeout);
      timeout = null;
    }
  };

  return debounced;
}
