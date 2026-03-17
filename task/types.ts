/**
 * Shared type definitions for the checkout system.
 * These types enforce consistency across modules.
 */

export type UserType = "standard" | "premium" | "VIP";

export interface DiscountRule {
  userType: UserType;
  percentage: number;
  minPurchase?: number;
}

export interface CheckoutResult {
  orderId: string;
  userId: string;
  userType: string;
  original: string;
  final: string;
  discountApplied: boolean;
}

export interface UserRecord {
  id: string;
  name: string;
  type: UserType;
  createdAt: string;
}
