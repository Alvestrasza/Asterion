import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { getMessages } from "../lib/messages.ts";
import { getSocialMessages } from "../lib/social-messages.ts";
import { getAccessMessages } from "../lib/access-messages.ts";
import * as i18n from "../lib/i18n.ts";
import { displayUsername } from "../lib/social-policy.ts";

const require = createRequire(import.meta.url);
async function component(file, extra = {}) {
  const source = await readFile(new URL(file, import.meta.url), "utf8");
  const output = ts.transpileModule(source, { compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  const mocks = {
    "next/link": { default: ({ prefetch, ...props }) => React.createElement("a", props) },
    "next/navigation": { useRouter: () => ({ refresh() {} }) },
    "@/lib/messages": { getMessages }, "@/lib/social-messages": { getSocialMessages },
    "@/lib/access-messages": { getAccessMessages }, "@/lib/i18n": i18n,
    "@/lib/social-policy": { displayUsername },
    "./language-selector": { LanguageSelector: ({ locale }) => React.createElement("select", { "aria-label": "Language", defaultValue: locale }, React.createElement("option", { value: locale }, locale)) },
    "./actions": { logout: async () => {} },
    "./friends/friends-dock": { FriendsDock: () => null },
    "./presence": { Presence: () => null }, ...extra
  };
  vm.runInNewContext(output, { exports: module.exports, module, process: { env: { AUTH_KEYCLOAK_ISSUER: "https://identity.example.test/realms/companions" } }, require: name => name in mocks ? mocks[name] : require(name) });
  return module.exports;
}

test("admin account cards display the player name separately with a localized missing-name fallback", async () => {
  const { Administration } = await component("../app/admin/administration.tsx");
  for (const locale of i18n.LOCALES) {
    const accounts = ["MoonFox", null].map((username, index) => ({ userId: `user-${index}`, name: `Account ${index}`, username, desiredRole: "member", effectiveRole: "member", syncStatus: "applied", errorCode: null, checkedAt: null }));
    const html = renderToStaticMarkup(React.createElement(Administration, { locale, actorId: "admin", accounts }));
    assert.match(html, /MoonFox/);
    assert.ok(html.includes(getAccessMessages(locale).playerName));
    assert.ok(html.includes(getAccessMessages(locale).noPlayerName));
  }
});

test("shared navigation localizes routes and distinguishes anonymous, member, admin and internal users", async () => {
  const { SiteHeader } = await component("../app/site-header.tsx");
  for (const locale of i18n.LOCALES) {
    for (const actor of [null, { id: "member", name: "Member", isAdmin: false, internalTestMode: false }, { id: "admin", name: "Admin", isAdmin: true, internalTestMode: false }, { id: "internal", name: "Internal", isAdmin: false, internalTestMode: true }]) {
      const html = renderToStaticMarkup(React.createElement(SiteHeader, { locale, currentPath: "/friends", actor }));
      assert.equal(html.includes(`href="/${locale}/login"`), actor === null);
      assert.equal(html.includes(`href="/${locale}/admin"`), !!actor?.isAdmin && !actor.internalTestMode);
      assert.equal(html.includes(`href="/${locale}/friends"`), !!actor && !actor.internalTestMode);
      assert.equal(html.includes(getAccessMessages(locale).logout), !!actor && !actor.internalTestMode);
      assert.doesNotMatch(html, /href="\/(care|friends|admin|login)"/);
      if (actor && !actor.internalTestMode) assert.match(html, /aria-current="page"/);
    }
  }
});

test("admin page loads only player-name fields after authorization and preserves display case", async () => {
  for (const mode of ["anonymous", "member", "admin"]) {
    let reads = 0, authorized = false;
    const actor = mode === "anonymous" ? null : { id: mode, name: mode, isAdmin: mode === "admin", internalTestMode: false };
    const { default: Page } = await component("../app/admin/page.tsx", {
      "@/lib/current-actor": { getCurrentActor: async () => actor },
      "@/lib/request-locale": { getRequestLocale: async () => "fr" },
      "@/lib/access-policy": { accessCheckIsFresh: () => true },
      "@/lib/access-service": { assertAccess: async (_, id, role) => { assert.equal(id, "admin"); assert.equal(role, "admin"); authorized = true; } },
      "next/navigation": { redirect: path => { throw new Error(`redirect:${path}`); } },
      "../site-header": { SiteHeader: () => null },
      "./administration": { Administration: ({ accounts }) => React.createElement("p", null, accounts[0].username) },
      "@/lib/db": { prisma: { $transaction: async fn => fn({ userAccess: { findMany: async query => {
        assert.equal(authorized, true);
        assert.deepEqual(Object.keys(query.select.user.select.socialProfile.select), ["username", "usernameDisplay"]);
        reads++;
        return [{ userId: "player", user: { name: "Account", socialProfile: { username: "moonfox", usernameDisplay: "MoonFox" } }, checkedAt: null, desiredRole: "member", effectiveRole: "member", syncStatus: "applied", errorCode: null }];
      } } }) } }
    });
    if (mode !== "admin") {
      await assert.rejects(Page(), new RegExp(`redirect:/fr/${mode === "anonymous" ? "login" : "care"}`));
      assert.equal(reads, 0);
    } else {
      assert.match(renderToStaticMarkup(await Page()), /MoonFox/);
      assert.equal(reads, 1);
    }
  }
});

test("obsolete public test notice is removed without dropping the shared internal-user warning", async () => {
  for (const locale of i18n.LOCALES) assert.equal("boundary" in getAccessMessages(locale), false);
  const care = await readFile(new URL("../app/asterion-client.tsx", import.meta.url), "utf8");
  assert.match(care, /Alle Tester auf diesem Dienst teilen momentan denselben Spielstand/);
  assert.match(care, /localStorage.removeItem\(queueKey\)/);
});
