import test from "node:test";
import assert from "node:assert/strict";
import { hasSameOrigin, readBoundedJson } from "../lib/http.ts";
import { canonicalOrigin, isPublicDeployment, publicRuntimeErrors } from "../lib/deployment-config.ts";

const publicEnvironment = () => ({
  ASTERION_DEPLOYMENT_MODE: "public",
  ASTERION_INTERNAL_TEST_MODE: "false",
  AUTH_URL: "https://companions.test",
  AUTH_SECRET: "unit-test-fixture-is-not-a-real-secret-value",
  AUTH_KEYCLOAK_ID: "companion-web",
  AUTH_KEYCLOAK_SECRET: "test-oidc-fixture",
  AUTH_KEYCLOAK_ISSUER: "https://identity.test/realms/test-fixture",
  ASTERION_KEYCLOAK_ADMIN_ORIGIN: "https://identity-admin.test",
  ASTERION_KEYCLOAK_ADMIN_CLIENT_ID: "companion-sync",
  ASTERION_KEYCLOAK_ADMIN_CLIENT_SECRET: "test-sync-fixture",
  ASTERION_KEYCLOAK_CLIENT_UUID: "client-fixture-id",
  ASTERION_MEMBER_ROLE: "companion-member",
  ASTERION_ADMIN_ROLE: "companion-admin",
  ASTERION_ACCESS_SYNC_SECRET: "unit-test-fixture-for-local-worker-only"
});

test("public runtime requires an exact HTTPS admin origin separately from the issuer", () => {
  for (const value of [undefined, "", "http://identity-admin.test", "https://identity-admin.test/",
    "https://identity-admin.test/admin", "https://user:password@identity-admin.test",
    "https://identity-admin.test?secret=value", "https://identity-admin.test#fragment",
    "https://127.0.0.1", "https://[::1]", "https://identity-admin.test:443"]) {
    const errors = publicRuntimeErrors({ ...publicEnvironment(), ASTERION_KEYCLOAK_ADMIN_ORIGIN: value });
    assert.ok(errors.includes("invalid_keycloak_admin_origin"));
    assert.doesNotMatch(errors.join(" "), /password|secret=value/);
  }
  assert.deepEqual(publicRuntimeErrors(publicEnvironment()), []);
});

function originRequest(origin, headers = {}) {
  return new Request("http://127.0.0.1:3012/api/pet/actions", {
    method: "POST",
    headers: { ...(origin === undefined ? {} : { Origin: origin }), ...headers }
  });
}

function jsonRequest(body, contentType = "application/json") {
  return new Request("https://companions.test/api/pet/actions", {
    method: "POST", headers: { "Content-Type": contentType }, body
  });
}

test("public writes accept only the canonical HTTPS origin, independently of forwarding claims", () => {
  const environment = publicEnvironment();
  assert.equal(hasSameOrigin(originRequest("https://companions.test"), environment), true);
  assert.equal(hasSameOrigin(originRequest("https://companions.test", {
    Host: "untrusted.test", "X-Forwarded-Host": "untrusted.test", "X-Forwarded-Proto": "http"
  }), environment), true);

  for (const origin of ["http://companions.test", "https://companions.test:8443", "https://alternate.test",
    "https://companions.test.attacker.test", "http://127.0.0.1:3012"]) {
    assert.equal(hasSameOrigin(originRequest(origin, {
      Host: "companions.test", "X-Forwarded-Host": "companions.test", "X-Forwarded-Proto": "https",
      Forwarded: "host=companions.test;proto=https"
    }), environment), false, origin);
  }
  const differentPort = { ...environment, AUTH_URL: "https://companions.test:8443" };
  assert.equal(hasSameOrigin(originRequest("https://companions.test:8443"), differentPort), true);
  assert.equal(hasSameOrigin(originRequest("https://companions.test"), differentPort), false);
});

test("missing, opaque, credentialed and malformed origins fail closed", () => {
  for (const origin of [undefined, "", "null", "data:text/plain,hello", "file:///tmp/example",
    "not-an-origin", "https://user:password@companions.test", "https://companions.test/path",
    "https://companions.test?query=true", "https://companions.test#fragment",
    "https://companions.test, https://attacker.test"]) {
    assert.equal(hasSameOrigin(originRequest(origin), publicEnvironment()), false, String(origin));
  }
  assert.equal(hasSameOrigin(originRequest("https://companions.test"), {
    ...publicEnvironment(), AUTH_URL: undefined
  }), false);
});

test("the explicit internal proxy profile preserves the port 8088 origin without enabling public trust", () => {
  const request = new Request("http://127.0.0.1:3011/api/pet/actions", {
    method: "POST", headers: {
      Origin: "http://internal.test:8088", Host: "127.0.0.1:3011", "X-Forwarded-Host": "internal.test:8088"
    }
  });
  assert.equal(hasSameOrigin(request, { ASTERION_INTERNAL_TEST_MODE: "true" }), true);
  assert.equal(hasSameOrigin(request, { ASTERION_INTERNAL_TEST_MODE: "false" }), false);
  assert.equal(hasSameOrigin(request, publicEnvironment()), false);
  const multiplePeers = new Request(request, {
    headers: { Origin: "http://internal.test:8088", Host: "127.0.0.1:3011", "X-Forwarded-Host": "internal.test:8088, attacker.test" }
  });
  assert.equal(hasSameOrigin(multiplePeers, { ASTERION_INTERNAL_TEST_MODE: "true" }), false);
});

test("bounded JSON accepts valid UTF-8 exactly at the byte limit", async () => {
  const body = JSON.stringify({ message: "Sternenfreund ✦" });
  const limit = new TextEncoder().encode(body).length;
  assert.deepEqual(await readBoundedJson(jsonRequest(body, "application/json; charset=utf-8"), limit), { message: "Sternenfreund ✦" });
  await assert.rejects(readBoundedJson(jsonRequest(body), limit - 1), /body_too_large/);
});

test("bounded JSON rejects missing bodies, malformed JSON and invalid UTF-8", async () => {
  await assert.rejects(readBoundedJson(jsonRequest(undefined)), /invalid_json/);
  for (const body of ["", "{", '{"action":undefined}', '{"action":"feed",}']) {
    await assert.rejects(readBoundedJson(jsonRequest(body)));
  }
  const invalidUtf8 = new Uint8Array([0x22, 0xc3, 0x28, 0x22]);
  await assert.rejects(readBoundedJson(jsonRequest(invalidUtf8)), TypeError);
});

test("the JSON media type must be exact rather than a prefix such as application/jsonp", async () => {
  assert.deepEqual(await readBoundedJson(jsonRequest("{}", "APPLICATION/JSON")), {});
  for (const mediaType of ["text/plain", "application/x-www-form-urlencoded", "application/jsonp", "application/json-invalid"]) {
    await assert.rejects(readBoundedJson(jsonRequest("{}", mediaType)), /invalid_json/, mediaType);
  }
});

test("oversized chunked bodies are cancelled and cannot bypass the limit using Content-Length", async () => {
  let cancelled = false;
  const stream = new ReadableStream({
    pull(controller) { controller.enqueue(new Uint8Array(8).fill(32)); },
    cancel() { cancelled = true; }
  });
  const request = new Request("https://companions.test/api/pet/actions", {
    method: "POST", headers: { "Content-Type": "application/json", "Content-Length": "1" },
    body: stream, duplex: "half"
  });
  await assert.rejects(readBoundedJson(request, 16), /body_too_large/);
  assert.equal(cancelled, true);
  assert.equal(request.body.locked, false);
});

test("public runtime accepts complete settings but rejects shared mode, missing secrets and short auth keys", () => {
  assert.equal(isPublicDeployment(publicEnvironment()), true);
  assert.equal(isPublicDeployment({ ASTERION_DEPLOYMENT_MODE: "internal" }), false);
  assert.deepEqual(publicRuntimeErrors(publicEnvironment()), []);
  for (const flag of [undefined, "", "true", "False"]) {
    assert.ok(publicRuntimeErrors({ ...publicEnvironment(), ASTERION_INTERNAL_TEST_MODE: flag }).includes("internal_mode_must_be_false"));
  }
  for (const key of ["AUTH_SECRET", "AUTH_KEYCLOAK_ID", "AUTH_KEYCLOAK_SECRET", "AUTH_KEYCLOAK_ISSUER",
    "ASTERION_KEYCLOAK_ADMIN_CLIENT_ID", "ASTERION_KEYCLOAK_ADMIN_CLIENT_SECRET", "ASTERION_KEYCLOAK_CLIENT_UUID",
    "ASTERION_MEMBER_ROLE", "ASTERION_ADMIN_ROLE", "ASTERION_ACCESS_SYNC_SECRET"]) {
    assert.ok(publicRuntimeErrors({ ...publicEnvironment(), [key]: "   " }).includes(`${key}_required`), key);
  }
  assert.ok(publicRuntimeErrors({ ...publicEnvironment(), AUTH_SECRET: "x".repeat(31) }).includes("auth_secret_too_short"));
  assert.ok(publicRuntimeErrors({ ...publicEnvironment(), ASTERION_ADMIN_ROLE: "companion-member" }).includes("roles_must_be_distinct"));
});

test("canonical origins reject paths and credentials, and issuer configuration must name an HTTPS realm", () => {
  assert.equal(canonicalOrigin(publicEnvironment()), "https://companions.test");
  for (const value of [undefined, "http://companions.test", "https://companions.test/path", "https://user:pass@companions.test",
    "https://companions.test?query=true", "https://companions.test#fragment"]) {
    assert.equal(canonicalOrigin({ AUTH_URL: value }), null);
    assert.ok(publicRuntimeErrors({ ...publicEnvironment(), AUTH_URL: value }).includes("canonical_https_origin_required"));
  }
  for (const issuer of ["http://identity.test/realms/test", "https://identity.test", "https://identity.test/realms/",
    "https://identity.test/realms/test/", "https://user:pass@identity.test/realms/test",
    "https://identity.test/realms/test?query=true", "https://identity.test/realms/test#fragment"]) {
    assert.ok(publicRuntimeErrors({ ...publicEnvironment(), AUTH_KEYCLOAK_ISSUER: issuer }).includes("invalid_oidc_issuer"), issuer);
  }
});
