import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";
import ts from "typescript";
import * as policy from "../lib/access-policy.ts";
import { KeycloakAccessError } from "../lib/keycloak-access.ts";

// Execute the actual service; doubles replace only PostgreSQL and the remote identity API.
// This verifies state-machine behavior, not PostgreSQL locking or migration acceptance.
const source = await readFile(new URL("../lib/access-service.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
const issuer = "https://identity.example.invalid/realms/example";

function fixture() {
  let records = new Map();
  let markers = new Map();
  let sessions = [];
  let events = [];
  const remote = new Map();
  const remoteCalls = [];
  const sqlCalls = [];
  let providerError;
  function matches(row, where = {}) {
    return Object.entries(where).every(([key, value]) => {
      if (key === "OR") return value.some((branch) => matches(row, branch));
      if (value && typeof value === "object" && !(value instanceof Date)) {
        return Object.entries(value).every(([operator, expected]) => {
          if (operator === "not") return row[key] !== expected;
          if (operator === "in") return expected.includes(row[key]);
          if (operator === "gt") return row[key] !== null && row[key] > expected;
          if (operator === "lte") return row[key] !== null && row[key] <= expected;
          throw new Error(`Unsupported test-store predicate ${operator}`);
        });
      }
      return row[key] === value;
    });
  }
  const store = {
    async $executeRaw(parts, ...values) { sqlCalls.push({ text: parts.join("?"), values }); return 1; },
    userAccess: {
      async findUnique({ where }) {
        const row = where.userId ? records.get(where.userId)
          : [...records.values()].find((entry) => entry.issuer === where.issuer_subject.issuer && entry.subject === where.issuer_subject.subject);
        return row ? structuredClone(row) : null;
      },
      async findMany({ where, take }) { return [...records.values()].filter((row) => matches(row, where)).slice(0, take).map((row) => structuredClone(row)); },
      async count({ where }) { return [...records.values()].filter((row) => matches(row, where)).length; },
      async create({ data }) {
        if (records.has(data.userId)) throw new Error("Unique user violation");
        const row = { revision: 1, syncedRevision: 0, syncStatus: "pending", desiredRole: "none", effectiveRole: "none",
          attempts: 0, retryAt: null, checkedAt: null, errorCode: null, careWindowStartedAt: null, careWindowCount: 0,
          createdAt: new Date(), updatedAt: new Date(), ...data };
        records.set(data.userId, row);
        return structuredClone(row);
      },
      async update({ where, data }) {
        const row = records.get(where.userId);
        assert.ok(row);
        for (const [key, value] of Object.entries(data)) row[key] = value && typeof value === "object" && "increment" in value ? row[key] + value.increment : value;
        row.updatedAt = new Date();
        return structuredClone(row);
      }
    },
    accessBootstrap: {
      async findUnique({ where }) { return markers.get(where.id) ?? null; },
      async create({ data }) { assert.equal(markers.has(data.id), false); markers.set(data.id, data); return data; }
    },
    session: { async deleteMany({ where }) { sessions = sessions.filter((entry) => entry.userId !== where.userId); } },
    accessAudit: { async create({ data }) { events.push(data); return data; } }
  };
  let transactionTail = Promise.resolve();
  const database = {
    ...store,
    $transaction(operation) {
      const run = transactionTail.then(async () => {
        const before = structuredClone({ records, markers, sessions, events });
        try { return await operation(store); } catch (error) {
          ({ records, markers, sessions, events } = before);
          throw error;
        }
      });
      transactionTail = run.catch(() => {});
      return run;
    }
  };
  const keycloak = {
    KeycloakAccessError,
    keycloakAccessConfig: () => ({}),
    createKeycloakAccessClient: () => ({
      async read(subject) {
        remoteCalls.push({ method: "read", subject });
        if (providerError) throw providerError;
        return remote.get(subject) ?? { enabled: true, role: "none" };
      },
      async reconcile(subject, role) {
        remoteCalls.push({ method: "reconcile", subject, role });
        if (providerError) throw providerError;
        const status = remote.get(subject) ?? { enabled: true, role: "none" };
        if (!status.enabled) return status;
        remote.set(subject, { enabled: true, role });
        return remote.get(subject);
      }
    })
  };
  const module = { exports: {} };
  vm.runInNewContext(compiled, {
    exports: module.exports, module, Date, Set, Math, Promise,
    process: { env: { AUTH_KEYCLOAK_ISSUER: issuer } },
    require(name) {
      if (name === "@/lib/db") return { prisma: database };
      if (name === "@/lib/access-policy") return policy;
      if (name === "@/lib/keycloak-access") return keycloak;
      throw new Error(`Unexpected service dependency ${name}`);
    }
  });
  return {
    service: module.exports, store, remote, remoteCalls, sqlCalls,
    records: () => records, events: () => events, sessions: () => sessions,
    addSession(userId) { sessions.push({ userId }); },
    failProvider(code) { providerError = code ? new KeycloakAccessError(code) : undefined; },
    async bootstrap() {
      await module.exports.registerIdentity("administrator", issuer, "admin-subject", true);
      remote.set("admin-subject", { enabled: true, role: "admin" });
    }
  };
}

test("identity admission immediately grants membership; admin bootstrap remains one-time and identity-bound", async () => {
  const f = fixture();
  const member = await f.service.registerIdentity("member", issuer, "member-subject");
  assert.equal(member.effectiveRole, "member");
  assert.equal(member.desiredRole, "member");
  assert.equal(member.syncStatus, "pending");
  assert.equal(f.service.accessIsEffective(member), true);
  assert.equal(f.service.accessIsEffective(member, "admin"), false);
  await f.bootstrap();
  assert.equal((await f.service.getUserAccess("administrator")).effectiveRole, "admin");
  await f.service.registerIdentity("another-admin", issuer, "another-subject", true);
  assert.equal((await f.service.getUserAccess("another-admin")).effectiveRole, "member");
  await assert.rejects(f.service.registerIdentity("member", issuer, "different-subject"), (error) => error.code === "identity_mismatch");
  await assert.rejects(f.service.registerIdentity("new-user", issuer, "member-subject"), (error) => error.code === "identity_mismatch");
  f.records().delete("administrator");
  await f.service.registerIdentity("replacement", issuer, "replacement-subject", true);
  assert.equal((await f.service.getUserAccess("replacement")).effectiveRole, "member");
});

test("existing untouched identities are admitted once, but revocations and blocks survive another login", async () => {
  const f = fixture();
  await f.bootstrap();
  await f.store.userAccess.create({ data: { userId: "legacy", issuer, subject: "legacy-subject",
    desiredRole: "none", effectiveRole: "none", syncedRevision: 1, syncStatus: "applied" } });
  await f.service.admitAuthenticatedUser("legacy");
  const admitted = await f.service.getUserAccess("legacy");
  assert.equal(admitted.effectiveRole, "member");
  await f.service.admitAuthenticatedUser("legacy");
  assert.equal((await f.service.getUserAccess("legacy")).revision, admitted.revision);
  await f.service.syncAccessBatch();
  assert.equal(f.remote.get("legacy-subject").role, "member");
  await f.service.setDesiredRole("administrator", "legacy", "none");
  await f.service.registerIdentity("legacy", issuer, "legacy-subject");
  assert.equal((await f.service.admitAuthenticatedUser("legacy")).effectiveRole, "none");
  const row = f.records().get("legacy");
  Object.assign(row, { revision: 1, syncedRevision: 1, syncStatus: "blocked" });
  assert.equal((await f.service.registerIdentity("legacy", issuer, "legacy-subject")).effectiveRole, "none");
  assert.equal(await f.service.admitAuthenticatedUser("missing"), null);
});

test("advisory locks explicitly narrow Prisma INT8 parameters to the PostgreSQL two-INT4 overload", async () => {
  const f = fixture();
  await f.bootstrap();
  await f.service.assertAccess(f.store, "administrator", "admin");
  const statements = f.sqlCalls.filter((call) => call.text.includes("pg_advisory_xact_lock"));
  assert.ok(statements.some((call) => call.text === "SELECT pg_advisory_xact_lock(?::integer, 0)"));
  assert.ok(statements.some((call) => call.text === "SELECT pg_advisory_xact_lock(?::integer, hashtext(?))"));
  for (const call of statements) {
    assert.match(call.text, /pg_advisory_xact_lock\(\?::integer,/);
    assert.ok(Number.isSafeInteger(call.values[0]));
    assert.ok(call.values[0] >= -2_147_483_648 && call.values[0] <= 2_147_483_647);
  }
});

test("a normal member cannot self-promote and the last administrator cannot be demoted", async () => {
  const f = fixture();
  await f.bootstrap();
  await f.service.registerIdentity("member", issuer, "member-subject");
  await assert.rejects(f.service.setDesiredRole("member", "member", "admin"), (error) => error.code === "admin_required");
  await assert.rejects(f.service.setDesiredRole("administrator", "administrator", "none"), (error) => error.code === "last_administrator");
  assert.equal((await f.service.getUserAccess("administrator")).desiredRole, "admin");
});

test("durable admin promotions coalesce to the latest role and remain ineffective until readback", async () => {
  const f = fixture();
  await f.bootstrap();
  await f.service.registerIdentity("member", issuer, "member-subject");
  await f.service.setDesiredRole("administrator", "member", "member");
  await f.service.setDesiredRole("administrator", "member", "admin");
  assert.equal((await f.service.getUserAccess("member")).effectiveRole, "member");
  await f.service.syncAccessBatch();
  const access = await f.service.getUserAccess("member");
  assert.equal(access.effectiveRole, "admin");
  assert.equal(access.syncedRevision, access.revision);
  assert.equal(f.remoteCalls.filter((call) => call.method === "reconcile").length, 1);
  assert.equal(f.remoteCalls[0].role, "admin");
  await f.service.syncAccessBatch();
  assert.equal(f.remoteCalls.length, 1);
});

test("revocation immediately deletes sessions even while Keycloak is unavailable", async () => {
  const f = fixture();
  await f.bootstrap();
  await f.service.registerIdentity("member", issuer, "member-subject");
  await f.service.setDesiredRole("administrator", "member", "member");
  await f.service.syncAccessBatch();
  f.addSession("member");
  f.failProvider("sync_unavailable");
  await f.service.setDesiredRole("administrator", "member", "none");
  assert.equal((await f.service.getUserAccess("member")).effectiveRole, "none");
  assert.equal(f.sessions().length, 0);
  await f.service.syncAccessBatch();
  const failed = await f.service.getUserAccess("member");
  assert.equal(failed.syncStatus, "failed");
  assert.equal(failed.errorCode, "sync_unavailable");
  assert.equal(failed.effectiveRole, "none");
  assert.ok(failed.retryAt > new Date());
});

test("external mapping removal suspends access and cannot be automatically regranted", async () => {
  const f = fixture();
  await f.bootstrap();
  await f.service.registerIdentity("member", issuer, "member-subject");
  await f.service.setDesiredRole("administrator", "member", "member");
  await f.service.syncAccessBatch();
  f.records().get("member").checkedAt = new Date(Date.now() - 65_000);
  f.remote.set("member-subject", { enabled: true, role: "none" });
  f.addSession("member");
  await f.service.syncAccessBatch();
  const blocked = await f.service.getUserAccess("member");
  assert.equal(blocked.syncStatus, "blocked");
  assert.equal(blocked.effectiveRole, "none");
  assert.equal(f.sessions().length, 0);
  const writes = f.remoteCalls.filter((call) => call.method === "reconcile").length;
  await f.service.syncAccessBatch();
  assert.equal(f.remoteCalls.filter((call) => call.method === "reconcile").length, writes);
  await f.service.setDesiredRole("administrator", "member", "member");
  await f.service.syncAccessBatch();
  assert.equal((await f.service.getUserAccess("member")).effectiveRole, "member");
});

test("expired leases deny protected transactions and audit metadata excludes private content", async () => {
  const f = fixture();
  await f.bootstrap();
  await f.service.assertAccess(f.store, "administrator", "admin");
  f.records().get("administrator").checkedAt = new Date(Date.now() - 300_000);
  await assert.rejects(f.service.assertAccess(f.store, "administrator", "admin"), (error) => error.code === "access_denied");
  assert.deepEqual(Object.keys(f.events()[0]).sort(), ["actorId", "targetId", "action", "desiredRole", "effectiveRole", "revision", "outcome"].sort());
});

test("provider outages do not renew an existing lease and disabled users lose sessions", async () => {
  const f = fixture();
  await f.bootstrap();
  const previousCheck = new Date(Date.now() - 65_000);
  f.records().get("administrator").checkedAt = previousCheck;
  f.failProvider("sync_timeout");
  await f.service.syncAccessBatch();
  const failed = await f.service.getUserAccess("administrator");
  assert.equal(failed.checkedAt.getTime(), previousCheck.getTime());
  assert.equal(failed.syncStatus, "failed");
  f.failProvider(null);
  f.records().get("administrator").retryAt = new Date(0);
  f.remote.set("admin-subject", { enabled: false, role: "none" });
  f.addSession("administrator");
  await f.service.syncAccessBatch();
  assert.equal((await f.service.getUserAccess("administrator")).effectiveRole, "none");
  assert.equal((await f.service.getUserAccess("administrator")).errorCode, "remote_account_disabled");
  assert.equal(f.sessions().length, 0);
});

test("late upstream grants to no-access accounts are detected without restoring local access", async () => {
  const f = fixture();
  await f.service.registerIdentity("unapproved", issuer, "unapproved-subject");
  Object.assign(f.records().get("unapproved"), { desiredRole: "none", effectiveRole: "none", revision: 3, syncedRevision: 3, syncStatus: "applied", retryAt: null });
  f.records().get("unapproved").checkedAt = new Date(Date.now() - 305_000);
  f.remote.set("unapproved-subject", { enabled: true, role: "member" });
  await f.service.syncAccessBatch();
  assert.equal((await f.service.getUserAccess("unapproved")).syncStatus, "blocked");
  assert.equal((await f.service.getUserAccess("unapproved")).effectiveRole, "none");
  assert.equal(f.remoteCalls.some((call) => call.method === "reconcile"), false);
});

test("the durable per-user care counter denies command thirty-one independently of pet resets", async () => {
  const f = fixture();
  await f.bootstrap();
  const now = new Date();
  // No Pet or PetEvent repository exists in this fixture: consuming/resetting a
  // companion cannot erase the identity-owned rate counter being exercised.
  for (let index = 0; index < 30; index += 1) {
    assert.equal(await f.service.consumeCareBudget(f.store, "administrator", now), true);
  }
  assert.equal((await f.service.getUserAccess("administrator")).careWindowCount, 30);
  assert.equal(await f.service.consumeCareBudget(f.store, "administrator", now), false);
  assert.equal(await f.service.consumeCareBudget(f.store, "administrator", new Date(now.getTime() - 1)), false);
  assert.equal(await f.service.consumeCareBudget(f.store, "administrator", new Date(now.getTime() + 60_000)), true);
  assert.equal((await f.service.getUserAccess("administrator")).careWindowCount, 1);
  await assert.rejects(f.service.consumeCareBudget(f.store, "missing-user", now), (error) => error.code === "access_denied");
});
