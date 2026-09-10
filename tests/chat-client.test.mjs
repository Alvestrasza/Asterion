import test from "node:test";
import assert from "node:assert/strict";
import { mergeChatMessages, hasChatHistoryGap, lastReceivedMessage } from "../lib/chat-client-state.ts";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";
import ts from "typescript";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { chatMessages } from "../lib/chat-messages.ts";

const message = (id, sequence, senderId = "peer") => ({ id, sequence: String(sequence), senderId, text: `text-${id}` });
test("chat history deduplicates page overlap, orders bigint cursors and retains at most 200 messages", () => {
  const previous = Array.from({ length: 150 }, (_, i) => message(`m${i}`, i + 1));
  const incoming = Array.from({ length: 150 }, (_, i) => message(`m${i + 100}`, i + 101));
  const result = mergeChatMessages(previous, incoming);
  assert.equal(result.length, 200); assert.equal(result[0].sequence, "51"); assert.equal(result.at(-1).sequence, "250");
  assert.equal(mergeChatMessages([], [message("b", "9007199254740993"), message("a", "9007199254740992")])[0].id, "a");
  assert.throws(() => mergeChatMessages([message("a", 1)], [message("a", 2)]), /message_conflict/);
  assert.throws(() => mergeChatMessages([], [message("a", "0")]), /invalid_message/);
});
test("read cursor ignores sent messages and chooses only the newest successfully decoded recipient message", () => {
  assert.equal(lastReceivedMessage([message("incoming", 1), message("sent", 3, "actor"), message("incoming-2", 2)], "actor").id, "incoming-2");
  assert.equal(lastReceivedMessage([message("sent", 3, "actor")], "actor"), undefined);
});
test("a new latest page separated from cached history resets the contiguous window for older pagination", () => {
  const old = Array.from({ length: 5 }, (_, index) => message(`old-${index}`, index + 1));
  const latest = Array.from({ length: 50 }, (_, index) => message(`new-${index}`, index + 100));
  assert.equal(hasChatHistoryGap(old, latest, true), true);
  assert.equal(hasChatHistoryGap(old, [message("overlap", 5), message("next", 6)], true), false);
  assert.equal(hasChatHistoryGap(old, latest, false), false);
  const contiguous = mergeChatMessages(hasChatHistoryGap(old, latest, true) ? [] : old, latest);
  assert.equal(contiguous[0].sequence, "100", "older request must start at the new window boundary, not old message 1");
});

const require = createRequire(import.meta.url);
const settle = async () => { for (let n = 0; n < 15; n++) await new Promise(resolve => setImmediate(resolve)); };
const identity = { version: 1, fingerprint: "own-pin", encryptionKey: "own-public", signingKey: "own-signing" };
const peerIdentity = { version: 1, fingerprint: "peer-pin", encryptionKey: "peer-public", signingKey: "peer-signing" };
const registration = { identity, backup: { iv: "backup-iv", ciphertext: "encrypted-backup" }, proof: "proof" };
const keys = { actorId: "actor", identity, encryptionKey: {}, signingKey: {} };
function elements(tree) {
  if (Array.isArray(tree)) return tree.flatMap(elements);
  if (!tree || typeof tree !== "object") return [];
  return [tree, ...elements(tree.props?.children)];
}
function elementText(node) {
  if (Array.isArray(node)) return node.map(elementText).join("");
  if (typeof node === "string" || typeof node === "number") return String(node);
  return node?.props ? elementText(node.props.children) : "";
}
async function ui(options = {}) {
  const source = await readFile(new URL("../app/friends/messenger.tsx", import.meta.url), "utf8");
  const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 } }).outputText;
  let stateIndex = 0, refIndex = 0, effectsStarted = false, cleanup;
  const states = [], refs = [], effects = [], calls = [], writes = [];
  let creates = 0, encryptions = 0, decryptions = 0, restores = 0;
  const window = new EventTarget(); window.confirm = () => true;
  const document = Object.assign(new EventTarget(), { visibilityState: "visible" });
  const envelope = { id: "same-uuid", friendshipId: "friendship", senderId: "actor", recipientId: "peer", ciphertext: "encrypted-message" };
  const mocks = {
    react: { ...React,
      useState: initial => { const index = stateIndex++; if (!(index in states)) states[index] = initial; return [states[index], value => { states[index] = typeof value === "function" ? value(states[index]) : value; }]; },
      useRef: initial => { const index = refIndex++; refs[index] ??= { current: initial }; return refs[index]; },
      useId: () => "test-id", useEffect: fn => { if (!effectsStarted) effects.push(fn); }
    },
    "@/lib/chat-messages": { chatMessages }, "./messenger.module.css": { default: {} },
    "@/lib/chat-client-state": { mergeChatMessages, hasChatHistoryGap, lastReceivedMessage },
    "@/lib/chat-crypto": {
      createChatIdentity: async () => { creates++; return { keys, registration, recoveryCode: "private-code" }; },
      restoreChatIdentity: async (_actor, restoredRegistration, code) => {
        restores++; if (code.trim() !== "private-code" && code.trim() !== "winner-code") throw new Error("invalid_recovery");
        return { ...keys, identity: restoredRegistration.identity };
      },
      verifyRegistration: async () => true, identityFingerprint: async () => peerIdentity.fingerprint,
      conversationSafetyCode: async () => "compare-this-code",
      encryptMessage: async () => { encryptions++; return envelope; },
      decryptMessage: async () => { decryptions++; return "private draft"; }
    },
    "@/lib/chat-vault": { loadChatKeys: async () => options.storedKeys ? keys : undefined,
      saveChatKeys: async value => writes.push(value), getPeerPin: async () => options.pin,
      savePeerPin: async () => {} }
  };
  const module = { exports: {} };
  vm.runInNewContext(output, { exports: module.exports, module, window, document, AbortController, setTimeout, clearTimeout,
    setInterval: () => 1, clearInterval: () => {},
    fetch: async (url, init) => {
      assert.equal(init.headers["X-Asterion-Actor"], "actor"); assert.equal(init.cache, "no-store");
      const command = JSON.parse(init.body); calls.push(command);
      if (options.request) { const response = await options.request(command, calls); if (response) return response; }
      if (command.action === "identity") return Response.json({ identity: options.existing ? registration : null, recoveryMode: options.mode ?? "keycloak" });
      if (command.action === "register" || command.action === "recover") return Response.json({ identity: registration, recoveryCode: "private-code" });
      if (command.action === "open") return Response.json({ peerId: "peer", identity: options.peer ? peerIdentity : null, messages: [], hasMore: false });
      if (command.action === "send") return Response.json({ message: { ...command.envelope, sequence: "1" } });
      return Response.json({ ok: true });
    }, require: name => name in mocks ? mocks[name] : require(name)
  });
  function render() { stateIndex = 0; refIndex = 0; return module.exports.Messenger({ actorId: "actor", friendshipId: "friendship", friendName: "MoonFox", locale: "en", onClose: () => {} }); }
  render(); effectsStarted = true; for (const effect of effects) cleanup = effect(); await settle();
  return { render, calls, writes, window, cleanup: () => cleanup(), get creates() { return creates; }, get encryptions() { return encryptions; }, get decryptions() { return decryptions; }, get restores() { return restores; },
    button: label => elements(render()).find(node => node.type === "button" && elementText(node) === label),
    input: predicate => elements(render()).find(node => predicate(node)),
    text: () => renderToStaticMarkup(render()) };
}

test("phase 1 setup requires explicit activation but never asks the user to copy a generated code", async () => {
  const h = await ui();
  assert.equal(h.calls.some(call => call.action === "register"), false);
  assert.match(h.text(), /Privileged operators/);
  assert.equal(h.input(node => node.type === "input" && node.props.type === "checkbox"), undefined);
  h.button("Enable chat with account recovery").props.onClick(); await settle();
  assert.equal(h.creates, 1); assert.equal(h.restores, 1);
  assert.equal(h.calls.filter(call => call.action === "register").length, 1);
  assert.equal(h.writes.length, 1); assert.doesNotMatch(h.text(), /private-code/);
  assert.equal(h.calls.find(call => call.action === "register").recoveryCode, "private-code"); h.cleanup();
});

test("a new browser automatically recovers an existing phase 1 identity without replacement keys", async () => {
  const h = await ui({ existing: true, peer: true });
  assert.equal(h.creates, 0); assert.equal(h.restores, 1); assert.equal(h.writes.length, 1);
  assert.equal(h.calls.filter(call => call.action === "recover").length, 1);
  assert.equal(h.calls.some(call => call.action === "register"), false);
  assert.equal(h.input(node => node.type === "input" && node.props.type === "password"), undefined);
  assert.ok(h.button("Send")); h.cleanup();
});

test("registration retry retains exactly the first generated envelope and canonical concurrent winner is restored", async () => {
  let registered = 0;
  const winner = { ...registration, identity: { ...identity, fingerprint: "concurrent-winner" } };
  const h = await ui({ request: command => {
    if (command.action === "register") {
      if (++registered === 1) throw new Error("response_lost_after_commit");
      return Response.json({ identity: winner, recoveryCode: "winner-code" });
    }
  } });
  h.button("Enable chat with account recovery").props.onClick(); await settle();
  assert.ok(h.button("Retry chat activation")); assert.equal(h.creates, 1);
  h.button("Retry chat activation").props.onClick(); await settle();
  assert.equal(h.creates, 1); assert.equal(h.restores, 1);
  const attempts = h.calls.filter(call => call.action === "register");
  assert.deepEqual(attempts[0], attempts[1]);
  assert.equal(h.writes[0].identity.fingerprint, "concurrent-winner"); h.cleanup();
});

test("legacy recovery remains manual and registration requires separate explicit migration consent", async () => {
  const h = await ui({ existing: true, mode: "legacy", peer: true });
  assert.match(h.text(), /Unlock existing chat/); assert.equal(h.creates, 0);
  assert.equal(h.calls.some(call => call.action === "recover"), false);
  h.input(node => node.type === "input" && node.props.type === "password").props.onChange({ target: { value: " private-code " } });
  h.input(node => node.type === "form").props.onSubmit({ preventDefault() {} }); await settle();
  assert.equal(h.calls.some(call => call.action === "register"), false);
  assert.match(h.text(), /Account recovery is not enabled/);
  h.input(node => node.type === "input" && node.props.type === "password").props.onChange({ target: { value: " private-code " } });
  h.input(node => node.type === "input" && node.props.type === "checkbox").props.onChange({ target: { checked: true } });
  h.input(node => node.type === "form").props.onSubmit({ preventDefault() {} }); await settle();
  assert.equal(h.calls.filter(call => call.action === "register").length, 1);
  assert.equal(h.calls.find(call => call.action === "register").registration.identity.fingerprint, "own-pin");
  assert.equal(h.calls.find(call => call.action === "register").recoveryCode, "private-code");
  assert.doesNotMatch(h.text(), /Account recovery is not enabled/); h.cleanup();
});

test("unavailable recovery cannot create or recover keys, but already saved local keys still work", async () => {
  for (const existing of [false, true]) {
    const h = await ui({ existing, mode: "unavailable" });
    assert.match(h.text(), /Account recovery is currently unavailable/);
    assert.equal(h.creates, 0); assert.equal(h.calls.some(call => ["recover", "register"].includes(call.action)), false); h.cleanup();
  }
  const local = await ui({ existing: true, mode: "unavailable", storedKeys: true, peer: true });
  assert.ok(local.button("Send")); assert.match(local.text(), /saved chat keys/);
  assert.equal(local.calls.some(call => call.action === "recover"), false); local.cleanup();
});

test("stale recovery results cannot persist keys after logout or a rejected actor binding", async () => {
  let release;
  const h = await ui({ existing: true, request: command => {
    if (command.action === "recover") return new Promise(resolve => { release = resolve; });
  } });
  h.window.dispatchEvent(new Event("asterion-session-ended"));
  release(Response.json({ identity: registration, recoveryCode: "private-code" })); await settle();
  assert.equal(h.writes.length, 0); assert.equal(h.restores, 0); assert.match(h.text(), /no longer available/); h.cleanup();
  const switched = await ui({ request: () => Response.json({ error: "session_changed" }, { status: 409 }) });
  assert.equal(switched.creates, 0); assert.equal(switched.writes.length, 0); assert.match(switched.text(), /no longer available/); switched.cleanup();
});

test("uncertain sends retain the encrypted envelope for an identical manual retry", async () => {
  let sends = 0;
  const h = await ui({ existing: true, storedKeys: true, peer: true, request: command => {
    if (command.action === "send" && ++sends === 1) throw new Error("network_lost_after_commit");
  } });
  h.input(node => node.type === "textarea" && !node.props.readOnly).props.onChange({ target: { value: "private draft" } });
  h.input(node => node.type === "form" && !!node.props.className === false && elements(node).some(child => child.type === "textarea")).props.onSubmit({ preventDefault() {} }); await settle();
  assert.equal(h.encryptions, 1); assert.match(h.text(), /private draft/); assert.ok(h.button("Retry encrypted message"));
  h.input(node => node.type === "form" && elements(node).some(child => child.type === "textarea")).props.onSubmit({ preventDefault() {} }); await settle();
  const sent = h.calls.filter(call => call.action === "send");
  assert.equal(sent.length, 2); assert.deepEqual(sent[0], sent[1]); assert.equal(h.encryptions, 1);
  assert.equal(JSON.stringify(sent).includes("private draft"), false); h.cleanup();
});

test("changed peer pins fail closed before any message decryption", async () => {
  const h = await ui({ existing: true, storedKeys: true, peer: true, pin: { fingerprint: "different-pin", verified: true } });
  assert.match(h.text(), /chat key does not match/); assert.equal(h.decryptions, 0); assert.equal(h.button("Send"), undefined); h.cleanup();
});

test("logout clears decrypted text and drafts immediately", async () => {
  const h = await ui({ existing: true, storedKeys: true, peer: true });
  h.input(node => node.type === "textarea" && !node.props.readOnly).props.onChange({ target: { value: "private draft" } });
  h.window.dispatchEvent(new Event("asterion-session-ended"));
  assert.doesNotMatch(h.text(), /private draft/); assert.match(h.text(), /no longer available/); h.cleanup();
});
