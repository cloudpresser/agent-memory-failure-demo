/**
 * User management module.
 * Retrieves user information from the database.
 */

interface UserRow {
  id: string;
  name: string;
  type: string;
  email: string;
  createdAt: string;
}

// Simulated database records
const USERS: UserRow[] = [
  { id: "u001", name: "Alice Chen", type: "standard", email: "alice@example.com", createdAt: "2024-01-15" },
  { id: "u002", name: "Bob Martinez", type: "premium", email: "bob@example.com", createdAt: "2023-06-20" },
  { id: "u003", name: "Carol Davis", type: "VIP", email: "carol@example.com", createdAt: "2022-11-03" },
  { id: "u004", name: "Dan Wilson", type: "standard", email: "dan@example.com", createdAt: "2025-02-28" },
];

/**
 * Look up a user's membership type by their ID.
 * Returns the type string exactly as stored in the database.
 */
export function getUserType(userId: string): string {
  const user = USERS.find((u) => u.id === userId);
  if (!user) {
    throw new Error(`User not found: ${userId}`);
  }
  return user.type;
}

/**
 * Get full user record.
 */
export function getUser(userId: string): UserRow {
  const user = USERS.find((u) => u.id === userId);
  if (!user) {
    throw new Error(`User not found: ${userId}`);
  }
  return user;
}
