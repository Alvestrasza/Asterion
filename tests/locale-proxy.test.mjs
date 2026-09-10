import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";
import ts from "typescript";
import * as i18n from "../lib/i18n.ts";
const require = createRequire(import.meta.url);
const next = require("next/server");
const source = await readFile(new URL("../proxy.ts", import.meta.url), "utf8");
const module = { exports: {} };
vm.runInNewContext(ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText, {
  module, exports: module.exports, Headers, process: { env: { NODE_ENV: "production" } },
  require: name => name === "next/server" ? next : i18n
});
const { proxy } = module.exports;

test("locale proxy negotiates redirects without losing queries or caching user preferences", () => {
  const response = proxy(new next.NextRequest("https://companions.test/login?error=AccessDenied", { headers: { "Accept-Language": "fr", Cookie: "asterion-locale=es" } }));
  assert.equal(response.status, 307);
  assert.equal(response.headers.get("location"), "https://companions.test/es/login?error=AccessDenied");
  assert.equal(response.headers.get("Cache-Control"), "private, no-store");
});

test("localized pages overwrite spoofed locale headers without an internal or external rewrite", () => {
  for (const language of i18n.LOCALES) {
    const response = proxy(new next.NextRequest(`http://127.0.0.1:3188/${language}/login`, { headers: { "x-asterion-locale": "invalid", Cookie: "asterion-locale=en" } }));
    assert.equal(response.headers.get("x-middleware-request-x-asterion-locale"), language);
    assert.equal(response.headers.get("x-middleware-rewrite"), null);
    assert.equal(response.headers.get("location"), null);
    assert.ok(response.headers.get("set-cookie").includes(`asterion-locale=${language}`));
  }
});

test("unprefixed server-action POSTs are not redirected and localized API paths are never rewritten", () => {
  for (const path of ["/login", "/de/api/internal/access-sync", "/en/api/friends"]) {
    const response = proxy(new next.NextRequest(`https://companions.test${path}`, { method: "POST" }));
    assert.equal(response.headers.get("location"), null);
    assert.equal(response.headers.get("x-middleware-rewrite"), null);
  }
});
