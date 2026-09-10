import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import * as i18n from "../lib/i18n.ts";
import { getSocialMessages } from "../lib/social-messages.ts";
import { getDockMessages } from "../lib/dock-messages.ts";
import { getMessages } from "../lib/messages.ts";
import { getAccessMessages } from "../lib/access-messages.ts";
import { createDockPolling } from "../lib/dock-polling.ts";

const require = createRequire(import.meta.url);
async function component(file, extra = {}) {
  const source = await readFile(new URL(file, import.meta.url), "utf8");
  const output = ts.transpileModule(source, { compilerOptions: { jsx: ts.JsxEmit.ReactJSX, module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  const mocks = {
    "next/link": { default: ({ prefetch, ...props }) => React.createElement("a", props) },
    "@/lib/i18n": i18n, "@/lib/social-messages": { getSocialMessages }, "@/lib/dock-messages": { getDockMessages },
    "@/lib/dock-polling": { createDockPolling }, "@/lib/messages": { getMessages }, "@/lib/access-messages": { getAccessMessages },
    "./friends-dock.module.css": { default: {} }, "./messenger": { Messenger: () => { throw new Error("No SSR conversation may open"); } },
    "./language-selector": { LanguageSelector: () => null }, "./actions": { logout: async () => {} },
    "./presence": { Presence: ({ actorId }) => React.createElement("span", { "data-presence": actorId }) },
    "./friends/friends-dock": { FriendsDock: ({ actorId }) => React.createElement("aside", { "data-dock": actorId }) }, ...extra
  };
  vm.runInNewContext(output, { exports: module.exports, module, require: name => name in mocks ? mocks[name] : require(name) });
  return module.exports;
}

test("server-rendered dock starts collapsed with a named accessible toggle and localized management link", async () => {
  const { FriendsDock } = await component("../app/friends/friends-dock.tsx");
  for (const locale of i18n.LOCALES) {
    const html = renderToStaticMarkup(React.createElement(FriendsDock, { actorId: "player-a", locale }));
    assert.match(html, /aria-expanded="false"/);
    assert.match(html, /hidden=""/);
    assert.match(html, /aria-controls="([^"]+)"/);
    assert.ok(html.includes(getDockMessages(locale).expand));
    assert.ok(html.includes(`href="/${locale}/friends"`));
    assert.ok(html.includes(`lang="${locale}"`));
  }
});

test("all shared signed-in headers bind a single dock and presence worker to the actor; guests and internal mode do not", async () => {
  const { SiteHeader } = await component("../app/site-header.tsx");
  for (const currentPath of ["/", "/care", "/friends", "/admin"]) {
    for (const actor of [null, { id: "player-a", name: "Player", isAdmin: true, internalTestMode: false }, { id: "shared", name: "Internal", isAdmin: false, internalTestMode: true }]) {
      const html = renderToStaticMarkup(React.createElement(SiteHeader, { locale: "en", currentPath, actor }));
      const publicActor = actor && !actor.internalTestMode;
      assert.equal((html.match(/data-dock=/g) ?? []).length, publicActor ? 1 : 0);
      assert.equal((html.match(/data-presence=/g) ?? []).length, publicActor ? 1 : 0);
      if (publicActor) assert.match(html, /data-dock="player-a"/);
    }
  }
});
