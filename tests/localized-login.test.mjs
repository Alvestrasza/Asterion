import test from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { dirname } from "node:path";
import { pathToFileURL } from "node:url";
import Keycloak from "next-auth/providers/keycloak";
import { keycloakLoginParameters } from "../lib/i18n.ts";

const require = createRequire(import.meta.url);
const core = await import(pathToFileURL(require.resolve("@auth/core", { paths: [dirname(require.resolve("next-auth"))] })));

test("localized login and registration preserve Auth.js state, nonce, PKCE and the callback", async () => {
  for (const locale of ["de", "en", "fr", "es"]) for (const registration of [false, true]) {
    const query = new URLSearchParams(keycloakLoginParameters(locale, registration));
    const result = await core.Auth(new Request(`https://companions.test/api/auth/signin/keycloak?${query}`, {
      method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ callbackUrl: `https://companions.test/${locale}/care` })
    }), {
      basePath: "/api/auth", secret: "isolated-protocol-fixture-not-a-production-secret", trustHost: true,
      skipCSRFCheck: core.skipCSRFCheck, raw: core.raw,
      providers: [Keycloak({ clientId: "preview-web", clientSecret: "fixture-secret", issuer: "https://identity.test/realms/preview",
        authorization: { url: "https://identity.test/realms/preview/protocol/openid-connect/auth", params: { scope: "openid profile email", prompt: "login" } },
        token: "https://identity.test/token", userinfo: "https://identity.test/userinfo", checks: ["pkce", "state", "nonce"] })]
    });
    const url = new URL(result.redirect);
    assert.equal(url.origin, "https://identity.test");
    assert.equal(url.searchParams.get("ui_locales"), locale);
    assert.equal(url.searchParams.get("prompt"), registration ? "create" : "login");
    assert.equal(url.searchParams.get("redirect_uri"), "https://companions.test/api/auth/callback/keycloak");
    assert.equal(url.searchParams.get("code_challenge_method"), "S256");
    for (const parameter of ["state", "nonce", "code_challenge"]) assert.ok(url.searchParams.get(parameter)?.length > 20);
    assert.ok(result.cookies.some(cookie => cookie.name.endsWith("callback-url") && cookie.value.endsWith(`/${locale}/care`)));
  }
});
