/** Asterion navigation and authorization regressions. Version: 1.1.0 | License: UNLICENSED | Updated: 2026-10-05 */
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
import { achievementCopy, achievementViews } from "../lib/achievements.ts";
import { companionProfile } from "../lib/companions.ts";
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
    "@/lib/achievements": { achievementCopy },
    "@/lib/companions": { companionProfile },
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
      assert.equal(html.includes(`href="/${locale}/achievements"`), !!actor);
      assert.equal(html.includes(getAccessMessages(locale).logout), !!actor && !actor.internalTestMode);
      assert.doesNotMatch(html, /href="\/(care|achievements|friends|admin|login)"/);
      if (actor && !actor.internalTestMode) assert.match(html, /aria-current="page"/);
    }
  }
});

test("achievements navigation preserves the current page when changing language", async () => {
  for (const locale of i18n.LOCALES) {
    const { SiteHeader } = await component("../app/site-header.tsx", {
      "./language-selector": { LanguageSelector: ({ returnTo }) => {
        assert.equal(returnTo, "/achievements");
        assert.equal(i18n.languageReturnPath(returnTo), "/achievements");
        return null;
      } }
    });
    const html = renderToStaticMarkup(React.createElement(SiteHeader, { locale, currentPath: "/achievements", actor: { id: "member", name: "Member", isAdmin: false, internalTestMode: false } }));
    assert.match(html, new RegExp(`<a[^>]+href="/${locale}/achievements"[^>]+aria-current="page">${achievementCopy(locale).nav}</a>`));
  }
});

test("private achievements page gates reads, keeps onboarding and shows only the actor's active companion", async () => {
  const { AchievementCollection } = await component("../app/achievement-collection.tsx");
  for (const locale of i18n.LOCALES) {
    for (const mode of ["anonymous", "new", "member-a", "member-b", "internal"]) {
      const actor = mode === "anonymous" ? null : { id: mode, name: mode, isAdmin: false, internalTestMode: mode === "internal" };
      const kind = mode === "member-b" ? "cat" : "asterion";
      let petChecks = 0, snapshots = 0;
      const { default: Page, metadata, dynamic } = await component("../app/achievements/page.tsx", {
        "@/lib/current-actor": { getCurrentActor: async () => actor },
        "@/lib/request-locale": { getRequestLocale: async () => locale },
        "next/navigation": { redirect: path => { throw new Error(`redirect:${path}`); } },
        "@/lib/pet-service": {
          hasPet: async id => { assert.equal(id, actor.id); petChecks++; return mode !== "new"; },
          getPetSnapshot: async (id, language) => {
            assert.equal(id, actor.id); assert.equal(language, locale); snapshots++;
            return { kind, achievements: achievementViews(locale, mode === "member-a" ? [{ achievementId: "v1.first-care", progress: 1, earnedAt: new Date("2026-10-01T12:00:00Z") }] : []) };
          }
        },
        "../site-header": { SiteHeader: props => { assert.equal(props.currentPath, "/achievements"); assert.equal(props.actor, actor); return null; } },
        "../achievement-collection": { AchievementCollection }, "../achievements.css": {}
      });
      assert.equal(dynamic, "force-dynamic");
      assert.equal(metadata.robots.index, false);
      if (mode === "anonymous" || mode === "new") {
        await assert.rejects(Page(), new RegExp(`redirect:/${locale}/${mode === "anonymous" ? "access" : "care"}`));
        assert.equal(snapshots, 0);
        assert.equal(petChecks, mode === "anonymous" ? 0 : 1);
      } else {
        const html = renderToStaticMarkup(await Page());
        assert.equal(petChecks, 1); assert.equal(snapshots, 1);
        assert.ok(html.includes(companionProfile(kind).name));
        assert.ok(!html.includes(companionProfile(kind === "cat" ? "asterion" : "cat").name));
        assert.ok(html.includes(achievementCopy(locale).heading));
        assert.match(html, new RegExp(`href="/${locale}/care"`));
        assert.equal((html.match(/<h1/g) ?? []).length, 1);
        assert.equal((html.match(/data-earned="true"/g) ?? []).length, mode === "member-a" ? 1 : 0);
        assert.equal(html.includes("Alle Tester auf diesem Dienst teilen momentan denselben Spielstand"), mode === "internal");
      }
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
