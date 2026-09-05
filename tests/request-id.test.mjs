import test from "node:test";
import assert from "node:assert/strict";
import { createRequestId } from "../lib/request-id.ts";

test("request IDs use the native UUID method when available", () => {
  const source = { randomUUID() { assert.equal(this, source); return "native-uuid"; } };
  assert.equal(createRequestId(source), "native-uuid");
});

test("internal HTTP browsers get an RFC UUID from cryptographic random bytes", () => {
  let calls = 0;
  const source = { getRandomValues(bytes) {
    assert.equal(this, source);
    assert.equal(bytes.length, 16);
    bytes.fill(calls++ === 0 ? 255 : 0);
    return bytes;
  } };
  assert.equal(createRequestId(source), "ffffffff-ffff-4fff-bfff-ffffffffffff");
  assert.equal(createRequestId(source), "00000000-0000-4000-8000-000000000000");
  assert.equal(calls, 2);
});

test("missing secure randomness fails closed instead of using predictable IDs", () => {
  assert.throws(() => createRequestId({}), /Secure randomness is unavailable/);
  assert.throws(() => createRequestId(null), /Secure randomness is unavailable/);
});

test("the fallback accepts real Web Crypto and returns a version-four UUID", () => {
  const id = createRequestId({ getRandomValues: (bytes) => globalThis.crypto.getRandomValues(bytes) });
  assert.match(id, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
});
