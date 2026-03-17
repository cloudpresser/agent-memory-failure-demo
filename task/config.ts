/**
 * Application configuration.
 * Discount rates and feature flags for the checkout system.
 */

export const DISCOUNT_RATES: Record<string, number> = {
  standard: 0,
  premium: 0.1,   // 10% off
  VIP: 0.2,       // 20% off
};

export const TAX_RATE = 0.08;

export const FEATURES = {
  discountsEnabled: true,
  taxEnabled: true,
  loyaltyPointsEnabled: false,
  maxDiscountPercent: 0.3,
};

export const CACHE_TTL_MS = 60_000; // 1 minute

/**
 * Validate that a discount rate is within acceptable bounds.
 */
export function isValidDiscountRate(rate: number): boolean {
  return rate >= 0 && rate <= FEATURES.maxDiscountPercent;
}
