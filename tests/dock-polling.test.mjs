import test from "node:test";
import assert from "node:assert/strict";
import { createDockPolling } from "../lib/dock-polling.ts";
import { getDockMessages } from "../lib/dock-messages.ts";

const settle = async () => { for (let n = 0; n < 5; n++) await new Promise(resolve => setImmediate(resolve)); };
const friend = { id: "friendship-1", username: "MoonFox", status: "accepted", online: true, level: 12 };
test("native fetch is called unbound rather than with the options object as receiver", async () => {
  const h = harness(async function () { assert.equal(this, undefined); return Response.json({ friends: [friend] }); });
  h.polling.setVisible(true); await settle();
  assert.equal(h.published.at(-1).friends.length, 1); assert.equal(h.errors, 0); h.polling.dispose();
});
function harness(request, withInbox = false) {
  const published = [], counts = [];
  let ended = 0, errors = 0;
  const polling = createDockPolling({ actorId: "player-A", request,
    publish: (friends, transient) => published.push({ friends, transient }),
    ...(withInbox ? { unread: value => counts.push(value) } : {}),
    unavailable: () => errors++, sessionEnded: () => ended++ });
  return { polling, published, counts, get ended() { return ended; }, get errors() { return errors; } };
}

test("dock refresh binds to actor and never exposes presence for unconfirmed requests", async () => {
  const requests = [];
  const h = harness(async (url, init) => {
    requests.push({ url, init });
    return Response.json({ friends: [friend, { ...friend, id: "incoming", status: "incoming" }] });
  });
  await h.polling.refresh();
  assert.equal(requests.length, 0, "hidden initial document must not request data");
  h.polling.setVisible(true); await settle();
  assert.equal(requests.length, 1);
  assert.equal(requests[0].url, "/api/friends");
  assert.equal(requests[0].init.cache, "no-store");
  assert.equal(requests[0].init.credentials, "same-origin");
  assert.equal(requests[0].init.headers["X-Asterion-Actor"], "player-A");
  assert.deepEqual(JSON.parse(requests[0].init.body), { action: "list" });
  assert.deepEqual(h.published.at(-1).friends, [friend, { ...friend, id: "incoming", status: "incoming", online: null, level: null }]);
  h.polling.dispose();
});

test("dock aborts hidden work and never restores data from a late previous request", async () => {
  const pending = [];
  const h = harness((_, init) => new Promise(resolve => pending.push({ resolve, init })));
  h.polling.setVisible(true);
  await h.polling.refresh();
  assert.equal(pending.length, 1, "requests must not overlap");
  h.polling.setVisible(false);
  assert.equal(pending[0].init.signal.aborted, true);
  assert.deepEqual(h.published.at(-1), { friends: [], transient: true });
  h.polling.setVisible(true);
  assert.equal(pending.length, 2);
  pending[1].resolve(Response.json({ friends: [{ ...friend, username: "CurrentFox" }] })); await settle();
  pending[0].resolve(Response.json({ friends: [friend] })); await settle();
  assert.equal(h.published.at(-1).friends[0].username, "CurrentFox");
  h.polling.dispose();
});

for (const status of [401, 403, 409]) test(`dock clears and permanently stops on session denial ${status}`, async () => {
  let calls = 0;
  const h = harness(async () => { calls++; return Response.json({ error: "session_changed" }, { status }); });
  h.polling.setVisible(true); await settle();
  assert.equal(h.ended, 1);
  assert.deepEqual(h.published.at(-1).friends, []);
  h.polling.setVisible(false); h.polling.setVisible(true); await h.polling.refresh();
  assert.equal(calls, 1);
  h.polling.dispose();
});

test("network failure clears stale friends and logout cancels subsequent polling", async () => {
  let calls = 0;
  const h = harness(async () => { if (++calls === 1) return Response.json({ friends: [friend] }); throw new Error("offline"); });
  h.polling.setVisible(true); await settle();
  await h.polling.refresh();
  assert.deepEqual(h.published.at(-1).friends, []);
  assert.equal(h.errors, 1);
  assert.equal(h.published.at(-1).transient, true, "temporary outages must not discard an open chat draft");
  h.polling.endSession(); await h.polling.refresh();
  assert.equal(calls, 2);
  assert.equal(h.ended, 1);
  h.polling.dispose();
});

test("unread badges accept only valid counts belonging to currently accepted friendships", async () => {
  const h = harness(async (url, init) => {
    assert.equal(init.headers["X-Asterion-Actor"], "player-A");
    assert.equal(init.cache, "no-store");
    if (url === "/api/friends") return Response.json({ friends: [friend, { ...friend, id: "pending", status: "incoming" }] });
    assert.deepEqual(JSON.parse(init.body), { action: "inbox" });
    return Response.json({ unread: [{ friendshipId: friend.id, count: 5 }, { friendshipId: "pending", count: 2 }, { friendshipId: "unknown", count: 7 }] });
  }, true);
  h.polling.setVisible(true); await settle();
  assert.deepEqual({ ...h.counts.at(-1) }, { [friend.id]: 5 });
  h.polling.setVisible(false);
  assert.deepEqual(h.counts.at(-1), {});
  h.polling.dispose();
});

test("inbox session mismatch also closes the session and clears the friends list", async () => {
  const h = harness(async url => url === "/api/friends" ? Response.json({ friends: [friend] }) : Response.json({}, { status: 409 }), true);
  h.polling.setVisible(true); await settle();
  assert.equal(h.ended, 1);
  assert.deepEqual(h.published.at(-1).friends, []);
  h.polling.dispose();
});

test("dock messages cover the four supported locales", () => {
  const keys = Object.keys(getDockMessages("en")).sort();
  for (const locale of ["de", "en", "fr", "es"]) {
    const messages = getDockMessages(locale);
    assert.deepEqual(Object.keys(messages).sort(), keys);
    assert.ok(Object.values(messages).every(value => typeof value === "string" && value.trim()));
  }
});
