import test from "node:test";
import assert from "node:assert/strict";
import { identitySubject, mayBootstrapAdmin } from "../lib/identity-policy.ts";
import { matchesExpectedActor } from "../lib/actor-binding.ts";

const environment = {
  AUTH_KEYCLOAK_ID: "companion-web",
  ASTERION_BOOTSTRAP_ADMIN_SUB: "subject-owner",
  ASTERION_ADMIN_ROLE: "companion-admin"
};

const profile = {
  sub: "subject-owner",
  resource_access: { "companion-web": { roles: ["companion-admin"] } }
};

test("identity subjects are bounded opaque identifiers, not email or display data", () => {
  assert.equal(identitySubject({ sub: "Opaque-Subject/123" }), "Opaque-Subject/123");
  assert.equal(identitySubject({ sub: "x".repeat(255) }), "x".repeat(255));
  for (const value of [null, undefined, false, "subject-owner", {}, { sub: "" }, { sub: 123 },
    { sub: ["subject-owner"] }, { sub: "x".repeat(256) },
    { email: "subject-owner", preferred_username: "subject-owner", name: "subject-owner" }]) {
    assert.equal(identitySubject(value), null);
  }
});

test("bootstrap requires the exact configured subject and exact current client role", () => {
  assert.equal(mayBootstrapAdmin(profile, environment), true);
  assert.equal(mayBootstrapAdmin({ ...profile, sub: "Subject-owner" }, environment), false);
  assert.equal(mayBootstrapAdmin({ ...profile, sub: "subject-owner " }, environment), false);
  assert.equal(mayBootstrapAdmin({ ...profile, sub: "another-subject", email: "subject-owner" }, environment), false);
  assert.equal(mayBootstrapAdmin({ ...profile, resource_access: { "companion-web": { roles: ["Companion-admin"] } } }, environment), false);
  assert.equal(mayBootstrapAdmin({ ...profile, resource_access: { "other-client": { roles: ["companion-admin"] } } }, environment), false);
});

test("realm roles, groups and email cannot bootstrap an administrator", () => {
  for (const claims of [
    { realm_access: { roles: ["companion-admin"] } },
    { groups: ["companion-admin", "/companion-admin"] },
    { email: "subject-owner", email_verified: true, preferred_username: "companion-admin" },
    { resource_access: { "companion-web": { roles: "companion-admin" } } },
    { resource_access: { "companion-web": { roles: [true, 1, null] } } }
  ]) {
    assert.equal(mayBootstrapAdmin({ sub: "subject-owner", ...claims }, environment), false);
  }
});

test("missing bootstrap configuration fails closed, including a missing client scope", () => {
  for (const key of Object.keys(environment)) {
    assert.equal(mayBootstrapAdmin(profile, { ...environment, [key]: undefined }), false);
    assert.equal(mayBootstrapAdmin(profile, { ...environment, [key]: "" }), false);
  }
  const unscopedProfile = { sub: "subject-owner", resource_access: { "": { roles: ["companion-admin"] } } };
  assert.equal(mayBootstrapAdmin(unscopedProfile, { ...environment, AUTH_KEYCLOAK_ID: undefined }), false);
});

test("actor binding rejects missing headers and stale cross-account context", () => {
  assert.equal(matchesExpectedActor("actor-one", "actor-one"), true);
  for (const expected of [undefined, null, "", "actor-two", "Actor-one", "actor-one "]) {
    assert.equal(matchesExpectedActor(expected, "actor-one"), false);
  }
  assert.equal(matchesExpectedActor("", ""), false);
});
