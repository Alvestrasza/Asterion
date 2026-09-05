import test from "node:test";
import assert from "node:assert/strict";
import { isKeycloakConfigured } from "../lib/auth-config.ts";

test("the login entry point requires the complete Keycloak configuration", () => {
  const configured = {
    AUTH_KEYCLOAK_ID: "example-client",
    AUTH_KEYCLOAK_SECRET: "example-only",
    AUTH_KEYCLOAK_ISSUER: "https://identity.example.invalid/realms/example"
  };
  assert.equal(isKeycloakConfigured(configured), true);
  assert.equal(isKeycloakConfigured({}), false);
  for (const key of Object.keys(configured)) {
    assert.equal(isKeycloakConfigured({ ...configured, [key]: undefined }), false);
    assert.equal(isKeycloakConfigured({ ...configured, [key]: "  " }), false);
  }
});
