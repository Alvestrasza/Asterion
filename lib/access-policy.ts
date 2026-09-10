export const ACCESS_ROLES = ["none", "member", "admin"] as const;
export type AccessRole = (typeof ACCESS_ROLES)[number];
export const ACCESS_CHECK_MAX_AGE_MS = 300_000;
export const ACCESS_REFRESH_AFTER_MS = 60_000;
export const CARE_WINDOW_MS = 60_000;
export const CARE_WINDOW_LIMIT = 30;

export class AccessPolicyError extends Error {
  readonly code: string;

  constructor(code: string) {
    super(code);
    this.name = "AccessPolicyError";
    this.code = code;
  }
}

export function isAccessRole(value: unknown): value is AccessRole {
  return value === "none" || value === "member" || value === "admin";
}

export function roleAtLeast(role: AccessRole, required: AccessRole): boolean {
  return ACCESS_ROLES.indexOf(role) >= ACCESS_ROLES.indexOf(required);
}

// A requested grant never takes effect before remote readback. Demotions do.
export function effectiveRoleAfterChange(current: AccessRole, desired: AccessRole): AccessRole {
  return roleAtLeast(current, desired) ? desired : current;
}

export function accessCheckIsFresh(checkedAt: Date | null, now = new Date()): boolean {
  if (!checkedAt) return false;
  const elapsed = now.getTime() - checkedAt.getTime();
  return elapsed >= 0 && elapsed < ACCESS_CHECK_MAX_AGE_MS;
}

export function retryDelayMs(attempt: number): number {
  return Math.min(300_000, 5_000 * 2 ** Math.min(6, Math.max(0, Math.floor(attempt) - 1)));
}

export function assertIdentity(issuer: string, subject: string): void {
  let parsed: URL;
  try {
    parsed = new URL(issuer);
  } catch {
    throw new AccessPolicyError("invalid_identity");
  }
  if (parsed.protocol !== "https:" || parsed.username || parsed.password || parsed.search || parsed.hash ||
      issuer.length > 512 || !subject || subject.length > 255 || /[\u0000-\u0020\u007f]/.test(subject)) {
    throw new AccessPolicyError("invalid_identity");
  }
}

export type AccessRecord = {
  desiredRole: AccessRole;
  effectiveRole: AccessRole;
  revision: number;
  syncedRevision: number;
  syncStatus: "pending" | "applied" | "failed" | "blocked";
};

/** Revision one is the untouched legacy identity, never an administrator's denial. */
export function canAutomaticallyAdmit(record: AccessRecord): boolean {
  return record.revision === 1 && record.syncedRevision === 1 && record.syncStatus === "applied" &&
    record.desiredRole === "none" && record.effectiveRole === "none";
}

// Drift is a new decision for an administrator, never an automatic regrant.
export function shouldBlockForDrift(record: AccessRecord, remote: AccessRole, enabled: boolean): boolean {
  if (!enabled) return true;
  return record.revision === record.syncedRevision && remote !== record.desiredRole;
}

export function selectSyncCandidates(pending: string[], refresh: string[], limit: number): string[] {
  const selected = new Set<string>();
  // Alternating work classes prevents a stream of new grants from starving leases.
  for (let index = 0; index < Math.max(pending.length, refresh.length) && selected.size < limit; index += 1) {
    if (pending[index]) selected.add(pending[index]);
    if (selected.size < limit && refresh[index]) selected.add(refresh[index]);
  }
  return [...selected].slice(0, limit);
}

export function nextCareBudget(startedAt: Date | null, count: number, now: Date) {
  if (!Number.isFinite(now.getTime()) || !Number.isSafeInteger(count) || count < 0) {
    throw new AccessPolicyError("invalid_care_budget");
  }
  if (!startedAt || now.getTime() - startedAt.getTime() >= CARE_WINDOW_MS) {
    return { allowed: true, startedAt: now, count: 1 };
  }
  // A clock moving backwards never opens a second budget window.
  if (!Number.isFinite(startedAt.getTime()) || count >= CARE_WINDOW_LIMIT) {
    return { allowed: false, startedAt, count };
  }
  return { allowed: true, startedAt, count: count + 1 };
}
