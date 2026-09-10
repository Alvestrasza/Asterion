import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import ts from 'typescript';
import { z } from 'zod';
import { hasSameOrigin, readBoundedJson } from '../lib/http.ts';
import { matchesExpectedActor } from '../lib/actor-binding.ts';
import { AccessPolicyError } from '../lib/access-policy.ts';

const source = await readFile(new URL('../app/api/chat/route.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
function fixture() {
  let actor = { id: 'a', internalTestMode: false }, result = { ok: true };
  const calls = [], module = { exports: {} };
  vm.runInNewContext(compiled, { exports: module.exports, module, Response, BigInt,
    require(name) {
      if (name === 'zod') return { z };
      if (name === '@/lib/current-actor') return { getCurrentActor: async () => actor };
      if (name === '@/lib/http') return { readBoundedJson, hasSameOrigin: request => hasSameOrigin(request, {}) };
      if (name === '@/lib/actor-binding') return { matchesExpectedActor };
      if (name === '@/lib/access-policy') return { AccessPolicyError };
      if (name === '@/lib/chat-recovery-service') return { recoveringChatCommand: async (...args) => { calls.push(args); return result; } };
      throw new Error(name);
    }
  });
  return { post: module.exports.POST, calls, actor: value => { actor = value; }, result: value => { result = value; },
    request: (body, origin = 'https://app.example.invalid', expected = 'a') => new Request('https://app.example.invalid/api/chat', {
      method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json', 'X-Asterion-Actor': expected }, body: JSON.stringify(body)
    }) };
}
test('chat API guards origin, account-switch binding, public-only authentication and non-cacheable responses', async () => {
  const f = fixture();
  assert.equal((await f.post(f.request({ action: 'identity' }, 'https://evil.example.invalid'))).status, 403);
  f.actor(null); assert.equal((await f.post(f.request({ action: 'identity' }))).status, 401);
  f.actor({ id: 'a', internalTestMode: true }); assert.equal((await f.post(f.request({ action: 'identity' }))).status, 401);
  f.actor({ id: 'b', internalTestMode: false }); assert.equal((await f.post(f.request({ action: 'identity' }))).status, 409);
  assert.equal(f.calls.length, 0);
  f.actor({ id: 'a', internalTestMode: false });
  const reply = await f.post(f.request({ action: 'identity' }));
  assert.equal(reply.status, 200); assert.match(reply.headers.get('Cache-Control'), /private, no-store/);
  assert.equal(f.calls[0][0], 'a');
  f.result({ error: 'rate_limited' }); assert.equal((await f.post(f.request({ action: 'inbox' }))).status, 429);
});
test('chat API rejects unknown fields, plaintext messages, invalid cursors and oversized body before service', async () => {
  const f = fixture();
  for (const body of [
    { action: 'identity', userId: 'victim' }, { action: 'send', plaintext: 'must not reach storage' },
    { action: 'recover', userId: 'victim' }, { action: 'recovery-check' },
    { action: 'open', friendshipId: 'pair', before: '-1' }, { action: 'open', friendshipId: 'pair', before: '9223372036854775808' },
    { action: 'read', friendshipId: 'pair', messageId: 'not-a-uuid' }, { action: 'register', registration: 'x'.repeat(25000) }
  ]) assert.equal((await f.post(f.request(body))).status, 400);
  assert.equal(f.calls.length, 0);
});
test('chat API accepts exactly the versioned opaque envelope and rejects oversized or padded encodings', async () => {
  const f = fixture();
  const envelope = { version: 1, id: '6d2c2d32-14a9-443f-a2ca-a8e44b11b893', friendshipId: 'pair', senderId: 'a', recipientId: 'b',
    senderFingerprint: 'a'.repeat(43), recipientFingerprint: 'b'.repeat(43), iv: 'a'.repeat(16), ciphertext: 'a'.repeat(24),
    senderKey: 'a'.repeat(512), recipientKey: 'b'.repeat(512), signature: 'a'.repeat(86) };
  assert.equal((await f.post(f.request({ action: 'send', envelope }))).status, 200);
  assert.equal((await f.post(f.request({ action: 'send', envelope: { ...envelope, ciphertext: 'a'.repeat(10689) } }))).status, 400);
  assert.equal((await f.post(f.request({ action: 'send', envelope: { ...envelope, signature: 'a'.repeat(85) + '=' } }))).status, 400);
  assert.equal((await f.post(f.request({ action: 'send', envelope: { ...envelope, text: 'plaintext' } }))).status, 400);
  assert.equal(f.calls.length, 1);
});
