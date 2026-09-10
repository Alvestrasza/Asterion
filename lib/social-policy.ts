export const ONLINE_WINDOW_MS = 90_000;
export const REQUEST_COOLDOWN_MS = 7 * 86_400_000;

export function normalizeUsername(value: string): string | null {
  const name = value.trim().toLowerCase();
  return /^[a-z0-9][a-z0-9_.-]{2,31}$/.test(name) ? name : null;
}

/** Fall back for old records and for names changed by an older release after rollback. */
export function displayUsername(profile: { username: string | null; usernameDisplay?: string | null } | null | undefined): string | null {
  if (!profile?.username) return null;
  return profile.usernameDisplay && normalizeUsername(profile.usernameDisplay) === profile.username
    ? profile.usernameDisplay : profile.username;
}

export function isOnline(lastSeen: Date | null, now: Date): boolean {
  const age = lastSeen ? now.getTime() - lastSeen.getTime() : Infinity;
  return age >= 0 && age < ONLINE_WINDOW_MS;
}

export type FriendRow = { leftId: string; rightId: string; requestedBy: string; status: string; leftBlocked: boolean; rightBlocked: boolean };
export function mayAccept(row: FriendRow, actorId: string): boolean {
  return [row.leftId, row.rightId].includes(actorId) && row.requestedBy !== actorId &&
    row.status === "pending" && !row.leftBlocked && !row.rightBlocked;
}

export function maySeePresence(row: FriendRow, actorId: string): boolean {
  return [row.leftId, row.rightId].includes(actorId) && row.status === "accepted" && !row.leftBlocked && !row.rightBlocked;
}
