import test from "node:test";
import assert from "node:assert/strict";
import { createKeycloakAccessClient, keycloakAccessConfig, KeycloakAccessError } from "../lib/keycloak-access.ts";

const config = {
  issuer: "https://identity.example.invalid/auth/realms/example",
  clientId: "application-sync", clientSecret: "test-fixture-only", clientUuid: "application-client-uuid",
  memberRole: "application-member", adminRole: "application-admin"
};
const role = (name) => ({ id: `id-${name}`, name, clientRole: true, containerId: config.clientUuid, composite: false });

function provider({ assigned = [], inherited = [], enabled = true, failReadback = false, composite = false,
  adminOrigin = "https://identity.example.invalid" } = {}) {
  const calls = [];
  let direct = assigned.map(role);
  let mutated = false;
  const fetcher = async (input, init) => {
    const url = new URL(input);
    const path = url.pathname;
    const method = init.method ?? "GET";
    const headers = new Headers(init.headers);
    calls.push({ origin: url.origin, path, method, body: init.body ? String(init.body) : null });
    assert.equal(init.redirect, "error");
    assert.equal(init.cache, "no-store");
    assert.ok(init.signal instanceof AbortSignal);
    if (path.endsWith("/protocol/openid-connect/token")) {
      assert.equal(url.origin, "https://identity.example.invalid");
      assert.equal(headers.has("authorization"), false);
      assert.equal(method, "POST");
      const body = new URLSearchParams(init.body);
      assert.equal(body.get("grant_type"), "client_credentials");
      assert.equal(body.get("client_id"), config.clientId);
      return Response.json({ access_token: "fixture-bearer-token" });
    }
    assert.equal(url.origin, adminOrigin);
    assert.equal(headers.get("authorization"), "Bearer fixture-bearer-token");
    if (path === "/auth/admin/realms/example/users/test-subject") return Response.json({ id: "test-subject", enabled });
    if (path.includes("/clients/application-client-uuid/roles/")) {
      return Response.json({ ...role(decodeURIComponent(path.split("/").at(-1))), composite });
    }
    assert.ok(path.startsWith("/auth/admin/realms/example/users/test-subject/role-mappings/clients/application-client-uuid"));
    if (path.endsWith("/composite")) return Response.json(failReadback && mutated ? [] : [...direct, ...inherited.map(role)]);
    if (method === "DELETE") {
      const ids = new Set(JSON.parse(init.body).map((entry) => entry.id));
      direct = direct.filter((entry) => !ids.has(entry.id));
      mutated = true;
      return new Response(null, { status: 204 });
    }
    if (method === "POST") {
      for (const entry of JSON.parse(init.body)) if (!direct.some((existing) => existing.id === entry.id)) direct.push(entry);
      mutated = true;
      return new Response(null, { status: 204 });
    }
    return Response.json(direct);
  };
  return { fetcher, calls, assignments: () => direct.map((entry) => entry.name) };
}

test("client credentials are server-side and only configured owned roles are added", async () => {
  const remote = provider({ assigned: ["other-application-role"] });
  const result = await createKeycloakAccessClient(config, remote.fetcher).reconcile("test-subject", "admin");
  assert.deepEqual(result, { enabled: true, role: "admin" });
  assert.deepEqual(remote.assignments().sort(), [config.memberRole, config.adminRole, "other-application-role"].sort());
  const writes = remote.calls.filter((call) => call.method === "POST" && !call.path.endsWith("/token"));
  assert.equal(writes.length, 1);
  assert.deepEqual(JSON.parse(writes[0].body).map((entry) => entry.name).sort(), [config.memberRole, config.adminRole].sort());
  assert.ok(remote.calls.every((call) => !/groups|\/role-mappings\/realm|\/clients\/$/.test(call.path)));
});

test("a separate admin origin routes all role operations without changing the token issuer", async () => {
  const adminOrigin = "https://identity-admin.example.invalid";
  const remote = provider({ adminOrigin, assigned: ["unrelated-role"] });
  const client = createKeycloakAccessClient({ ...config, adminOrigin }, remote.fetcher);
  assert.deepEqual(await client.reconcile("test-subject", "admin"), { enabled: true, role: "admin" });
  assert.deepEqual(await client.reconcile("test-subject", "member"), { enabled: true, role: "member" });
  assert.deepEqual(remote.assignments().sort(), [config.memberRole, "unrelated-role"].sort());
  assert.ok(remote.calls.some(call => call.method === "DELETE" && call.origin === adminOrigin));
  assert.ok(remote.calls.filter(call => !call.path.endsWith("/token"))
    .every(call => call.origin === adminOrigin && !call.body?.includes(config.clientSecret)));
});

test("admin origin configuration rejects ambiguous destinations before network access", () => {
  for (const adminOrigin of ["", "http://admin.example.invalid", "https://admin.example.invalid/",
    "https://admin.example.invalid/admin", "https://admin.example.invalid?token=value",
    "https://user:password@admin.example.invalid", "https://admin.example.invalid#fragment",
    " https://admin.example.invalid", "https://admin.example.invalid:443", "https://127.0.0.1",
    "https://[::1]", "https://admin.example.invalid\\path"]) {
    assert.throws(() => createKeycloakAccessClient({ ...config, adminOrigin }), KeycloakAccessError, adminOrigin);
  }
});

test("environment configuration carries the separate admin origin without replacing the issuer", () => {
  const result = keycloakAccessConfig({
    AUTH_KEYCLOAK_ISSUER: config.issuer,
    ASTERION_KEYCLOAK_ADMIN_ORIGIN: "https://identity-admin.example.invalid",
    ASTERION_KEYCLOAK_ADMIN_CLIENT_ID: config.clientId,
    ASTERION_KEYCLOAK_ADMIN_CLIENT_SECRET: config.clientSecret,
    ASTERION_KEYCLOAK_CLIENT_UUID: config.clientUuid,
    ASTERION_MEMBER_ROLE: config.memberRole, ASTERION_ADMIN_ROLE: config.adminRole
  });
  assert.equal(result.adminOrigin, "https://identity-admin.example.invalid");
  assert.equal(result.issuer, config.issuer);
});

test("failed or redirected private admin requests never fall back to the public issuer", async () => {
  for (const status of [302, 404]) {
    const calls = [];
    const client = createKeycloakAccessClient({ ...config, adminOrigin: "https://identity-admin.example.invalid" },
      async (input, init) => {
        calls.push(String(input));
        assert.equal(init.redirect, "error");
        if (calls.length === 1) return Response.json({ access_token: "fixture-token" });
        return new Response("private provider details", { status, headers: { Location: "https://unexpected.example.invalid" } });
      });
    await assert.rejects(client.read("test-subject"), error => error instanceof KeycloakAccessError &&
      error.code === (status === 404 ? "sync_resource_missing" : "sync_unavailable"));
    assert.deepEqual(calls, [
      "https://identity.example.invalid/auth/realms/example/protocol/openid-connect/token",
      "https://identity-admin.example.invalid/auth/admin/realms/example/users/test-subject"
    ]);
  }
});

test("role reconciliation is idempotent and demotion preserves unrelated mappings", async () => {
  const remote = provider({ assigned: [config.memberRole, config.adminRole, "unrelated-role"] });
  const client = createKeycloakAccessClient(config, remote.fetcher);
  assert.deepEqual(await client.reconcile("test-subject", "member"), { enabled: true, role: "member" });
  assert.deepEqual(await client.reconcile("test-subject", "member"), { enabled: true, role: "member" });
  assert.equal(remote.calls.filter((call) => call.method === "DELETE").length, 1);
  assert.deepEqual(remote.assignments().sort(), [config.memberRole, "unrelated-role"].sort());
});

test("an inherited owned role cannot be silently treated as revoked", async () => {
  const remote = provider({ assigned: [config.memberRole], inherited: [config.adminRole] });
  await assert.rejects(createKeycloakAccessClient(config, remote.fetcher).reconcile("test-subject", "none"),
    (error) => error instanceof KeycloakAccessError && error.code === "sync_mapping_conflict");
  assert.deepEqual(remote.assignments(), []);
});

test("a grant requires effective-role readback and disabled users are never enabled", async () => {
  const noReadback = provider({ failReadback: true });
  await assert.rejects(createKeycloakAccessClient(config, noReadback.fetcher).reconcile("test-subject", "member"),
    (error) => error.code === "sync_mapping_conflict");
  const disabled = provider({ enabled: false });
  assert.deepEqual(await createKeycloakAccessClient(config, disabled.fetcher).reconcile("test-subject", "admin"), { enabled: false, role: "none" });
  assert.equal(disabled.calls.filter((call) => call.method === "PUT" || call.method === "DELETE" || (call.method === "POST" && !call.path.endsWith("/token"))).length, 0);
});

test("owned role definitions must not introduce composite privileges", async () => {
  const remote = provider({ composite: true });
  await assert.rejects(createKeycloakAccessClient(config, remote.fetcher).reconcile("test-subject", "admin"),
    (error) => error.code === "sync_role_configuration_invalid");
  assert.equal(remote.calls.filter((call) => call.method === "POST" && !call.path.endsWith("/token")).length, 0);
});

test("provider errors are sanitized and do not leak response bodies or credentials", async () => {
  for (const [status, code] of [[401, "sync_permission_denied"], [403, "sync_permission_denied"], [404, "sync_resource_missing"], [429, "sync_rate_limited"], [500, "sync_unavailable"]]) {
    await assert.rejects(createKeycloakAccessClient(config, async () => new Response("sensitive upstream body", { status })).read("test-subject"),
      (error) => error.code === code && error.message === code);
  }
  await assert.rejects(createKeycloakAccessClient(config, async () => { throw new Error("secret diagnostic"); }).read("test-subject"),
    (error) => error.code === "sync_unavailable" && !error.message.includes("secret"));
});

test("malformed and oversized provider bodies fail closed", async () => {
  for (const body of ["not JSON", JSON.stringify({ access_token: "x".repeat(140_000) }), JSON.stringify({ access_token: 123 })]) {
    await assert.rejects(createKeycloakAccessClient(config, async () => new Response(body)).read("test-subject"),
      (error) => error.code === "sync_response_invalid");
  }
});

test("configuration rejects HTTP, redirects in issuer metadata, and identical owned roles", () => {
  for (const issuer of ["http://identity.example.invalid/realms/example", `${config.issuer}/`, `${config.issuer}?secret=value`, "https://user:password@identity.example.invalid/realms/example", "https://identity.example.invalid/realms/a%2fb"]) {
    assert.throws(() => createKeycloakAccessClient({ ...config, issuer }), KeycloakAccessError);
  }
  assert.throws(() => createKeycloakAccessClient({ ...config, memberRole: config.adminRole }), KeycloakAccessError);
  assert.throws(() => keycloakAccessConfig({}), KeycloakAccessError);
});
