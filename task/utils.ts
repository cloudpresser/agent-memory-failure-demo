/**
 * General-purpose utility functions.
 * String formatting, sanitization, and helper methods used across the app.
 */

/**
 * Normalize user-facing strings for consistent comparison.
 * Handles edge cases like extra whitespace from form inputs
 * and mixed case from legacy database records.
 */
export function normalizeString(value: string): string {
  return value.trim().toLowerCase();
}

/**
 * Format a number as USD currency string.
 */
export function formatCurrency(amount: number): string {
  return `$${amount.toFixed(2)}`;
}

/**
 * Generate a unique order identifier.
 */
export function generateOrderId(): string {
  return `ORD-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

/**
 * Validate that a string is non-empty after trimming.
 */
export function isNonEmpty(value: string | null | undefined): boolean {
  return value != null && value.trim().length > 0;
}

/**
 * Truncate a string to a max length, appending "..." if truncated.
 */
export function truncate(value: string, maxLength: number): string {
  if (value.length <= maxLength) return value;
  return value.slice(0, maxLength - 3) + "...";
}
