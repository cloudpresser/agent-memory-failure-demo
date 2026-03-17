/**
 * Simple in-memory cache for user type lookups.
 * Reduces database calls for frequently accessed user records.
 */

import { CACHE_TTL_MS } from "./config";

interface CacheEntry {
  value: string;
  timestamp: number;
}

const cache = new Map<string, CacheEntry>();

/**
 * Get a cached user type, or null if not cached / expired.
 */
export function getCachedUserType(userId: string): string | null {
  const entry = cache.get(userId);
  if (!entry) {
    return null;
  }

  const age = Date.now() - entry.timestamp;
  if (age > CACHE_TTL_MS) {
    cache.delete(userId);
    return null;
  }

  return entry.value;
}

/**
 * Store a user type in the cache.
 * The cached value is stored exactly as provided — no transformation.
 */
export function setCachedUserType(userId: string, userType: string): void {
  cache.set(userId, {
    value: userType,
    timestamp: Date.now(),
  });
}

/**
 * Clear all cached entries.
 */
export function clearCache(): void {
  cache.clear();
}

/**
 * Get cache stats for monitoring.
 */
export function getCacheStats(): { size: number; ttlMs: number } {
  return { size: cache.size, ttlMs: CACHE_TTL_MS };
}
