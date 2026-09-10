import test from "node:test";
import assert from "node:assert/strict";
import {
  ACCESS_ROLES, AccessPolicyError, accessCheckIsFresh, assertIdentity,
  effectiveRoleAfterChange, isAccessRole, nextCareBudget, retryDelayMs, roleAtLeast, selectSyncCandidates, shouldBlockForDrift
} from "../lib/access-policy.ts";

test("only the three application roles exist and admin includes care access", () => {
  assert.deepEqual(ACCESS_ROLES, ["none", "member", "admin"]);
  assert.equal(isAccessRole("diary-reader"), false);
  assert.equal(isAccessRole("realm-admin"), false);
  assert.equal(roleAtLeast("admin", "member"), true);
  assert.equal(roleAtLeast("member", "admin"), false);
  assert.equal(roleAtLeast("none", "member"), false);
});

test("care budgets permit thirty commands, renew at sixty seconds, and resist backward clocks", () => {
  const start = new Date(100_000);
  assert.deepEqual(nextCareBudget(null, 0, start), { allowed: true, startedAt: start, count: 1 });
  assert.deepEqual(nextCareBudget(start, 29, new Date(159_999)), { allowed: true, startedAt: start, count: 30 });
  assert.equal(nextCareBudget(start, 30, new Date(159_999)).allowed, false);
  assert.equal(nextCareBudget(start, 30, new Date(99_999)).allowed, false);
  assert.deepEqual(nextCareBudget(start, 30, new Date(160_000)), { allowed: true, startedAt: new Date(160_000), count: 1 });
  assert.throws(() => nextCareBudget(start, -1, start), AccessPolicyError);
});

test("pending grants cannot starve active authorization lease refreshes", () => {
  assert.deepEqual(selectSyncCandidates(["p1", "p2", "p3", "p4"], ["r1", "r2", "r3", "r4"], 4), ["p1", "r1", "p2", "r2"]);
  assert.deepEqual(selectSyncCandidates(["p1", "p2", "p3"], [], 3), ["p1", "p2", "p3"]);
  assert.deepEqual(selectSyncCandidates([], ["r1", "r2", "r3"], 2), ["r1", "r2"]);
  assert.deepEqual(selectSyncCandidates(["same", "p2"], ["same", "r2"], 4), ["same", "p2", "r2"]);
});

test("grants remain ineffective until synchronization and revocations apply immediately", () => {
  assert.equal(effectiveRoleAfterChange("none", "member"), "none");
  assert.equal(effectiveRoleAfterChange("member", "admin"), "member");
  assert.equal(effectiveRoleAfterChange("admin", "member"), "member");
  assert.equal(effectiveRoleAfterChange("admin", "none"), "none");
});

test("remote authorization expires at five minutes and future timestamps fail closed", () => {
  const now = new Date(400_000);
  assert.equal(accessCheckIsFresh(new Date(100_001), now), true);
  assert.equal(accessCheckIsFresh(new Date(100_000), now), false);
  assert.equal(accessCheckIsFresh(new Date(400_001), now), false);
  assert.equal(accessCheckIsFresh(null, now), false);
});

test("applied mapping drift blocks rather than automatically restoring removed rights", () => {
  const applied = { desiredRole: "admin", effectiveRole: "admin", revision: 2, syncedRevision: 2, syncStatus: "applied" };
  assert.equal(shouldBlockForDrift(applied, "member", true), true);
  assert.equal(shouldBlockForDrift(applied, "admin", true), false);
  assert.equal(shouldBlockForDrift(applied, "admin", false), true);
  assert.equal(shouldBlockForDrift({ ...applied, revision: 3, syncStatus: "pending" }, "member", true), false);
});

test("retry backoff is bounded and identities reject unsafe metadata", () => {
  assert.equal(retryDelayMs(1), 5_000);
  assert.equal(retryDelayMs(2), 10_000);
  assert.equal(retryDelayMs(99), 300_000);
  assert.doesNotThrow(() => assertIdentity("https://identity.example.invalid/realms/example", "subject-123"));
  for (const issuer of ["http://identity.example.invalid/realms/example", "https://a:b@identity.example.invalid", "https://identity.example.invalid?secret=value"]) {
    assert.throws(() => assertIdentity(issuer, "subject-123"), AccessPolicyError);
  }
  assert.throws(() => assertIdentity("https://identity.example.invalid", ""), AccessPolicyError);
});
