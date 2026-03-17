# Bug Report: VIP Discount Not Applied

**Reported by:** QA Team
**Severity:** High
**Date:** 2026-03-17

## Description

VIP users are not receiving their 20% discount during checkout.
User `u003` (Carol Davis) is a VIP member but consistently pays full price.

## Steps to Reproduce

1. Process checkout for user `u003` with any item
2. Expected: 20% discount applied (e.g., $150 item → $120)
3. Actual: full price charged ($150 item → $150)

## Notes

- Premium discounts (user `u002`) work correctly — 10% is applied.
- Standard users (user `u001`) correctly pay full price.
- The issue is specific to VIP-tier users.
- Cache has been cleared and issue persists, so it's not a stale cache problem.
- Config values for discount rates have been verified as correct.

## Request

Please investigate the codebase and application logs to find the root cause.
Once identified, trace the exact data flow for user `u003` purchasing a $150 item:
list every function call in the chain and the exact string values at each step.
