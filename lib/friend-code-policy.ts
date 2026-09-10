/** Codes identify an invitation destination; they are not authentication secrets. */
export const FRIEND_CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";
export const FRIEND_CODE_PATTERN = /^[0-9A-HJKMNP-TV-Z]{5}-[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{5}$/;

export function normalizeFriendCode(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!/^[A-Za-z0-9-]+$/.test(trimmed)) return null;
  const canonical = trimmed.toUpperCase();
  return FRIEND_CODE_PATTERN.test(canonical) ? canonical : null;
}
