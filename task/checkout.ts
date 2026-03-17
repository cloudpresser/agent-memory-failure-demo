/**
 * Checkout flow orchestrator.
 * Coordinates user lookup, discount calculation, and order creation.
 */

import { getUserType } from "./user";
import { calculateDiscount } from "./discount";
import { getCachedUserType, setCachedUserType } from "./cache";
import { normalizeString, formatCurrency, generateOrderId } from "./utils";

/**
 * Process a checkout for the given user and price.
 *
 * Flow:
 *   1. Look up user type (from cache or database)
 *   2. Normalize the user type string for consistent handling
 *   3. Calculate applicable discount
 *   4. Generate order record
 */
export function checkout(userId: string, price: number) {
  // Step 1: Get user type, using cache when available
  let rawUserType = getCachedUserType(userId);
  if (!rawUserType) {
    rawUserType = getUserType(userId);
    setCachedUserType(userId, rawUserType);
  }

  // Step 2: Normalize for consistent comparison
  const userType = normalizeString(rawUserType);

  // Step 3: Calculate discount
  const finalPrice = calculateDiscount(price, userType);
  const discountApplied = finalPrice < price;

  // Step 4: Build order
  const orderId = generateOrderId();

  return {
    orderId,
    userId,
    userType,
    original: formatCurrency(price),
    final: formatCurrency(finalPrice),
    discountApplied,
  };
}
