/**
 * Request middleware.
 * Handles authentication, logging, and request enrichment.
 */

import { getUser } from "./user";

interface Request {
  userId: string;
  path: string;
  headers: Record<string, string>;
}

interface EnrichedRequest extends Request {
  user: {
    id: string;
    name: string;
    type: string;
  };
  authenticated: boolean;
}

/**
 * Authentication middleware.
 * Validates the user exists, attaches user info to the request,
 * and logs the access for audit purposes.
 */
export function authMiddleware(req: Request): EnrichedRequest {
  const user = getUser(req.userId);

  // Log access for audit trail
  console.log(
    `[AUTH] userId=${user.id} name=${user.name} type=${user.type} path=${req.path}`
  );

  return {
    ...req,
    user: {
      id: user.id,
      name: user.name,
      type: user.type,
    },
    authenticated: true,
  };
}

/**
 * Rate limiting check (stub).
 */
export function rateLimitMiddleware(req: Request): boolean {
  // Simplified: always allow
  return true;
}

/**
 * Request logging middleware.
 */
export function loggingMiddleware(req: Request): void {
  console.log(`[REQUEST] ${req.path} userId=${req.userId}`);
}
