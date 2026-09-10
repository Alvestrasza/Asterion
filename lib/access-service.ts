import type { Prisma, UserAccess } from "@prisma/client";
import { prisma } from "@/lib/db";
import {
  ACCESS_CHECK_MAX_AGE_MS, ACCESS_REFRESH_AFTER_MS, AccessPolicyError,
  accessCheckIsFresh, assertIdentity, canAutomaticallyAdmit, effectiveRoleAfterChange, isAccessRole,
  nextCareBudget, retryDelayMs, roleAtLeast, selectSyncCandidates, shouldBlockForDrift, type AccessRole
} from "@/lib/access-policy";
import { createKeycloakAccessClient, keycloakAccessConfig, KeycloakAccessError } from "@/lib/keycloak-access";

export { AccessPolicyError } from "@/lib/access-policy";

const LOCK_NAMESPACE = 1_093_863_250;
const BOOTSTRAP_ID = "first-administrator-v1";

async function lockUser(tx: Prisma.TransactionClient, userId: string) {
  // Hash collisions only serialize unrelated users; they never grant access.
  await tx.$executeRaw`SELECT pg_advisory_xact_lock(${LOCK_NAMESPACE}::integer, hashtext(${userId}))`;
}

async function lockAdministration(tx: Prisma.TransactionClient) {
  await tx.$executeRaw`SELECT pg_advisory_xact_lock(${LOCK_NAMESPACE + 1}::integer, 0)`;
}

function configuredIssuer(): string {
  const issuer = process.env.AUTH_KEYCLOAK_ISSUER?.trim();
  if (!issuer) throw new AccessPolicyError("identity_not_configured");
  return issuer;
}

export function accessIsEffective(access: UserAccess | null, required: AccessRole = "member", now = new Date()): boolean {
  return Boolean(access && access.issuer === configuredIssuer() && access.syncStatus !== "blocked" &&
    roleAtLeast(access.effectiveRole, required) && accessCheckIsFresh(access.checkedAt, now));
}

/** Call inside every protected mutation transaction, before touching user data. */
export async function assertAccess(tx: Prisma.TransactionClient, userId: string, required: AccessRole = "member") {
  await lockUser(tx, userId);
  // Also lock the row: SERIALIZABLE care transactions must fail/retry if their
  // snapshot predates a revocation that committed while the advisory lock waited.
  await tx.$executeRaw`SELECT "userId" FROM "UserAccess" WHERE "userId" = ${userId} FOR UPDATE`;
  const access = await tx.userAccess.findUnique({ where: { userId } });
  if (!accessIsEffective(access, required)) throw new AccessPolicyError("access_denied");
  return access!;
}

/** Caller already holds assertAccess's transaction locks; consume after replay detection. */
export async function consumeCareBudget(tx: Prisma.TransactionClient, userId: string, now = new Date()): Promise<boolean> {
  const access = await tx.userAccess.findUnique({ where: { userId } });
  if (!access) throw new AccessPolicyError("access_denied");
  const budget = nextCareBudget(access.careWindowStartedAt, access.careWindowCount, now);
  if (!budget.allowed) return false;
  await tx.userAccess.update({ where: { userId }, data: {
    careWindowStartedAt: budget.startedAt, careWindowCount: budget.count
  } });
  return true;
}

export async function getUserAccess(userId: string) {
  return prisma.userAccess.findUnique({ where: { userId } });
}

/** Only call with the user ID from a verified, issuer-bound database session. */
export async function admitAuthenticatedUser(userId: string) {
  const access = await getUserAccess(userId);
  if (!access || !canAutomaticallyAdmit(access)) return access;
  // Recheck eligibility and identity under the same locks as administrator decisions.
  return registerIdentity(userId, access.issuer, access.subject);
}

export async function listUserAccess(limit = 100) {
  return prisma.userAccess.findMany({
    where: { issuer: configuredIssuer() },
    include: { user: { select: { id: true, name: true, email: true } } },
    orderBy: { createdAt: "desc" },
    take: Math.max(1, Math.min(100, Math.floor(limit)))
  });
}

export async function registerIdentity(userId: string, issuer: string, subject: string, bootstrapAllowed = false) {
  assertIdentity(issuer, subject);
  if (issuer !== configuredIssuer()) throw new AccessPolicyError("identity_mismatch");
  return prisma.$transaction(async (tx) => {
    await lockAdministration(tx);
    await lockUser(tx, userId);
    let access = await tx.userAccess.findUnique({ where: { userId } });
    const identityOwner = await tx.userAccess.findUnique({ where: { issuer_subject: { issuer, subject } } });
    if ((access && (access.issuer !== issuer || access.subject !== subject)) || (identityOwner && identityOwner.userId !== userId)) {
      throw new AccessPolicyError("identity_mismatch");
    }
    if (!access) {
      access = await tx.userAccess.create({
        data: { userId, issuer, subject, desiredRole: "none", effectiveRole: "none", syncedRevision: 1, syncStatus: "applied", checkedAt: new Date() }
      });
    }
    if (bootstrapAllowed && !await tx.accessBootstrap.findUnique({ where: { id: BOOTSTRAP_ID } })) {
      // Caller has already verified the configured exact subject and fresh client admin claim.
      if (await tx.userAccess.count({ where: { desiredRole: "admin" } }) > 0) throw new AccessPolicyError("bootstrap_unavailable");
      await tx.accessBootstrap.create({ data: { id: BOOTSTRAP_ID, userId } });
      access = await tx.userAccess.update({
        where: { userId },
        data: { desiredRole: "admin", effectiveRole: "admin", revision: { increment: 1 }, syncedRevision: access.revision + 1,
          syncStatus: "applied", checkedAt: new Date(), errorCode: null }
      });
      await audit(tx, userId, access, "bootstrap", "applied");
    }
    if (canAutomaticallyAdmit(access)) {
      // Successful OIDC admission grants basic membership immediately. The durable
      // worker mirrors that decision to Keycloak; admin promotions still await readback.
      access = await tx.userAccess.update({ where: { userId }, data: {
        desiredRole: "member", effectiveRole: "member", revision: { increment: 1 },
        syncStatus: "pending", attempts: 0, retryAt: new Date(), checkedAt: new Date(), errorCode: null
      } });
      await audit(tx, userId, access, "automatic_membership", "pending_sync");
    }
    return access;
  }, { maxWait: 5_000, timeout: 15_000 });
}

async function audit(tx: Prisma.TransactionClient, actorId: string | null, access: UserAccess, action: string, outcome: string) {
  await tx.accessAudit.create({ data: {
    actorId, targetId: access.userId, action, desiredRole: access.desiredRole,
    effectiveRole: access.effectiveRole, revision: access.revision, outcome
  } });
}

export async function setDesiredRole(actorId: string, targetId: string, desiredRole: AccessRole) {
  if (!isAccessRole(desiredRole)) throw new AccessPolicyError("invalid_role");
  return prisma.$transaction(async (tx) => {
    await lockAdministration(tx);
    // Stable ordering prevents two administrators editing each other from deadlocking.
    for (const userId of [...new Set([actorId, targetId])].sort()) await lockUser(tx, userId);
    const actor = await tx.userAccess.findUnique({ where: { userId: actorId } });
    if (!accessIsEffective(actor, "admin")) throw new AccessPolicyError("admin_required");
    const target = await tx.userAccess.findUnique({ where: { userId: targetId } });
    if (!target || target.issuer !== configuredIssuer()) throw new AccessPolicyError("target_unavailable");
    if (target.effectiveRole === "admin" && desiredRole !== "admin") {
      const otherAdministrators = await tx.userAccess.count({ where: {
        userId: { not: targetId }, issuer: target.issuer, desiredRole: "admin", effectiveRole: "admin",
        syncStatus: { not: "blocked" }, checkedAt: { gt: new Date(Date.now() - ACCESS_CHECK_MAX_AGE_MS), lte: new Date() }
      } });
      if (otherAdministrators === 0) throw new AccessPolicyError("last_administrator");
    }
    const effectiveRole = effectiveRoleAfterChange(target.effectiveRole, desiredRole);
    const updated = await tx.userAccess.update({
      where: { userId: targetId },
      data: { desiredRole, effectiveRole, revision: { increment: 1 }, syncStatus: "pending", attempts: 0, retryAt: new Date(), errorCode: null }
    });
    if (effectiveRole !== target.effectiveRole || desiredRole === "none") {
      await tx.session.deleteMany({ where: { userId: targetId } });
    }
    await audit(tx, actorId, updated, "set_desired_role", "pending");
    return updated;
  }, { maxWait: 5_000, timeout: 15_000 });
}

async function block(tx: Prisma.TransactionClient, access: UserAccess, code: string) {
  const updated = await tx.userAccess.update({ where: { userId: access.userId }, data: {
    effectiveRole: "none", syncStatus: "blocked", checkedAt: new Date(), retryAt: null, errorCode: code
  } });
  await tx.session.deleteMany({ where: { userId: access.userId } });
  await audit(tx, null, updated, "synchronize", code);
  return "blocked" as const;
}

async function synchronizeUser(userId: string) {
  return prisma.$transaction(async (tx) => {
    await lockUser(tx, userId);
    // Read only after acquiring the cross-node lock. Never execute a stale queued revision.
    const access = await tx.userAccess.findUnique({ where: { userId } });
    if (!access || access.syncStatus === "blocked") return "skipped" as const;
    if (access.issuer !== configuredIssuer()) return block(tx, access, "identity_mismatch");
    if (access.retryAt && access.retryAt > new Date()) return "skipped" as const;
    if (access.syncStatus === "applied" && access.checkedAt && Date.now() - access.checkedAt.getTime() < ACCESS_REFRESH_AFTER_MS) return "skipped" as const;
    try {
      const client = createKeycloakAccessClient(keycloakAccessConfig());
      const hasPendingDecision = access.revision !== access.syncedRevision;
      const remote = hasPendingDecision ? await client.reconcile(access.subject, access.desiredRole) : await client.read(access.subject);
      if (shouldBlockForDrift(access, remote.role, remote.enabled)) {
        return block(tx, access, remote.enabled ? "remote_mapping_drift" : "remote_account_disabled");
      }
      if (remote.role !== access.desiredRole) return block(tx, access, "sync_mapping_conflict");
      const updated = await tx.userAccess.update({ where: { userId }, data: {
        effectiveRole: access.desiredRole, syncedRevision: access.revision, syncStatus: "applied",
        attempts: 0, retryAt: null, checkedAt: new Date(), errorCode: null
      } });
      // Periodic successful lease refreshes do not create unbounded audit noise.
      if (hasPendingDecision || access.syncStatus !== "applied") await audit(tx, null, updated, "synchronize", "applied");
      return "applied" as const;
    } catch (error) {
      if (!(error instanceof KeycloakAccessError)) throw error;
      if (["sync_identity_invalid", "sync_mapping_conflict", "sync_role_configuration_invalid", "sync_resource_missing"].includes(error.code)) {
        return block(tx, access, error.code);
      }
      const attempts = Math.min(1_000_000, access.attempts + 1);
      const updated = await tx.userAccess.update({ where: { userId }, data: {
        syncStatus: "failed", attempts, retryAt: new Date(Date.now() + retryDelayMs(attempts)), errorCode: error.code
      } });
      // checkedAt is deliberately not refreshed. A stopped worker or provider outage expires access.
      if (access.errorCode !== error.code || access.syncStatus !== "failed") await audit(tx, null, updated, "synchronize", error.code);
      return "failed" as const;
    }
  }, { maxWait: 5_000, timeout: 20_000 });
}

export async function syncAccessBatch(limit = 20) {
  const take = Math.max(1, Math.min(20, Math.floor(limit)));
  const now = new Date();
  const pending = await prisma.userAccess.findMany({
    where: { syncStatus: { in: ["pending", "failed"] }, OR: [{ retryAt: null }, { retryAt: { lte: now } }] },
    select: { userId: true }, orderBy: [{ retryAt: "asc" }, { updatedAt: "asc" }], take
  });
  const refresh = await prisma.userAccess.findMany({
    where: { syncStatus: "applied", effectiveRole: { not: "none" }, OR: [{ checkedAt: null }, { checkedAt: { lte: new Date(now.getTime() - ACCESS_REFRESH_AFTER_MS) } }] },
    select: { userId: true }, orderBy: { checkedAt: "asc" }, take
  });
  const candidates = selectSyncCandidates(pending.map((entry) => entry.userId), refresh.map((entry) => entry.userId), take);
  if (candidates.length < take) {
    // No-access accounts cannot use the app, but occasional reconciliation still
    // detects late upstream writes after an HTTP timeout and out-of-band grants.
    const denied = await prisma.userAccess.findMany({
      where: { syncStatus: "applied", effectiveRole: "none", OR: [{ checkedAt: null }, { checkedAt: { lte: new Date(now.getTime() - ACCESS_CHECK_MAX_AGE_MS) } }] },
      select: { userId: true }, orderBy: { checkedAt: "asc" }, take: take - candidates.length
    });
    for (const entry of denied) if (!candidates.includes(entry.userId)) candidates.push(entry.userId);
  }
  const counts = { applied: 0, failed: 0, blocked: 0, skipped: 0 };
  // Four independent per-user locks bound resource use; no shared transaction is parallelized.
  for (let index = 0; index < candidates.length; index += 4) {
    const results = await Promise.all(candidates.slice(index, index + 4).map(synchronizeUser));
    for (const outcome of results) counts[outcome] += 1;
  }
  return counts;
}
