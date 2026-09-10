import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";
import ts from "typescript";

async function presenceHarness() {
  const source = await readFile(new URL("../app/presence.tsx", import.meta.url), "utf8");
  const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  const document = Object.assign(new EventTarget(), { visibilityState: "visible" });
  const window = new EventTarget();
  const calls = [];
  let cleanup, tick;
  vm.runInNewContext(output, { exports: module.exports, module, document, window, AbortController, Date,
    fetch: async (url, init) => { calls.push({ url, init }); return { status: 200 }; },
    setInterval: fn => { tick = fn; return 1; }, clearInterval: () => {},
    require: name => { assert.equal(name, "react"); return { useEffect: fn => { cleanup = fn(); } }; }
  });
  module.exports.Presence({ actorId: "player-a" });
  await new Promise(resolve => setImmediate(resolve));
  return { calls, document, window, tick: () => tick(), cleanup: () => cleanup() };
}

for (const mode of ["same-tab", "other-tab"]) test(`public presence stops and aborts on ${mode} logout`, async () => {
  const h = await presenceHarness();
  assert.equal(h.calls.length, 1);
  assert.equal(h.calls[0].init.headers["X-Asterion-Actor"], "player-a");
  assert.equal(h.calls[0].init.cache, "no-store");
  const ended = mode === "same-tab" ? new Event("asterion-session-ended") : Object.assign(new Event("storage"), { key: "asterion.session-ended" });
  h.window.dispatchEvent(ended);
  assert.equal(h.calls[0].init.signal.aborted, true);
  h.tick(); await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.calls.length, 1);
  h.cleanup();
});

test("public presence does not poll while hidden and cleanup aborts its actor-bound controller", async () => {
  const h = await presenceHarness();
  h.document.visibilityState = "hidden";
  h.tick(); await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.calls.length, 1);
  h.document.visibilityState = "visible";
  h.tick(); await new Promise(resolve => setImmediate(resolve));
  assert.equal(h.calls.length, 2);
  h.cleanup();
  assert.equal(h.calls[0].init.signal.aborted, true);
});
