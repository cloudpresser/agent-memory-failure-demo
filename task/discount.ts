/**
 * Discount calculation engine.
 * Applies pricing rules based on user membership tier.
 */

import { DISCOUNT_RATES, FEATURES } from "./config";

/**
 * Calculate the discounted price for a given user type.
 *
 * Discount rules:
 *   - "premium" members get 10% off
 *   - "VIP" members get 20% off
 *   - All other user types pay full price
 *
 * @param price - The original item price
 * @param userType - The membership tier string
 * @returns The final price after any applicable discount
 */
export function calculateDiscount(price: number, userType: string): number {
  if (!FEATURES.discountsEnabled) {
    return price;
  }

  if (price <= 0) {
    return 0;
  }

  if (userType === "premium") {
    return price * (1 - DISCOUNT_RATES.premium);
  }

  if (userType === "VIP") {
    return price * (1 - DISCOUNT_RATES.VIP);
  }

  return price;
}

/**
 * Check whether a user type is eligible for any discount.
 */
export function isDiscountEligible(userType: string): boolean {
  return userType === "premium" || userType === "VIP";
}
