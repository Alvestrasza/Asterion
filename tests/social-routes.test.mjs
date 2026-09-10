import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import ts from 'typescript';
import { z } from 'zod';
import { hasSameOrigin, readBoundedJson } from '../lib/http.ts';
import { matchesExpectedActor } from '../lib/actor-binding.ts';
import { COMPANION_KINDS } from '../lib/companions.ts';
import { AccessPolicyError } from '../lib/access-policy.ts';
import { normalizeFriendCode } from '../lib/friend-code-policy.ts';
async function fixture(file) {
  const calls = [];
  class PetRequestError extends Error { constructor(code, status) { super(code); this.status = status; } }
  let actor = { id: 'a', internalTestMode: false };
  const source = await readFile(new URL(file, import.meta.url), 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(compiled, { exports: module.exports, module, Response,
    require(name) {
      if (name === 'zod') return { z };
      if (name === '@/lib/current-actor') return { getCurrentActor: async () => actor };
      if (name === '@/lib/http') return { readBoundedJson, hasSameOrigin: request => hasSameOrigin(request, {}) };
      if (name === '@/lib/actor-binding') return { matchesExpectedActor };
      if (name === '@/lib/access-policy') return { AccessPolicyError };
      if (name === '@/lib/friend-code-policy') return { normalizeFriendCode };
      if (name === '@/lib/companions') return { COMPANION_KINDS };
      if (name === '@/lib/social-service') return { socialCommand: async (...args) => { calls.push(args); return { ok: true }; } };
      if (name === '@/lib/pet-service') return {
        PetRequestError,
        getPetSnapshot: async () => { throw new PetRequestError('companion_selection_required', 409); },
        chooseFirstPet: async (...args) => { calls.push(args); return { id: 'one' }; }
      };
      throw new Error(name);
    }
  });
  const request = (body, origin = 'https://app.example.invalid', expectedActor = 'a') => new Request('https://app.example.invalid/api', {
    method: 'POST', headers: { Origin: origin, 'Content-Type': 'application/json', 'X-Asterion-Actor': expectedActor }, body: JSON.stringify(body)
  });
  return { post: module.exports.POST, get: module.exports.GET, request, calls, actor: value => { actor = value; } };
}

test('pet read before first selection returns a non-cacheable conflict, not an internal error', async () => {
  const f = await fixture('../app/api/pet/route.ts');
  const response = await f.get(new Request('https://app.example.invalid/api/pet', { headers: { 'X-Asterion-Actor': 'a' } }));
  assert.equal(response.status, 409);
  assert.match(response.headers.get('Cache-Control'), /no-store/);
  assert.equal((await response.json()).error, 'companion_selection_required');
});
for (const [file, command] of [['../app/api/friends/route.ts', { action: 'search', query: 'BBBBB-BBB-BBBBB' }], ['../app/api/pet/adopt/route.ts', { kind: 'rabbit' }]]) {
  test(`${file}: origin, authentication, session binding and bounded input precede service calls`, async () => {
    const f = await fixture(file);
    assert.equal((await f.post(f.request(command, 'https://foreign.example.invalid'))).status, 403);
    f.actor(null); assert.equal((await f.post(f.request(command))).status, 401);
    f.actor({ id: 'b', internalTestMode: false }); assert.equal((await f.post(f.request(command))).status, 409);
    f.actor({ id: 'a', internalTestMode: false });
    assert.equal((await f.post(f.request({ ...command, ownerId: 'victim' }))).status, 400);
    assert.equal((await f.post(f.request({ action: 'search', query: 'x'.repeat(3000) }))).status, 400);
    assert.equal(f.calls.length, 0);
    const response = await f.post(f.request(command));
    assert.equal(response.status, 200); assert.match(response.headers.get('Cache-Control'), /no-store/);
    assert.equal(f.calls[0][0], 'a');
  });
}
test('shared internal test account cannot use social APIs', async () => {
  const f = await fixture('../app/api/friends/route.ts');
  f.actor({ id: 'a', internalTestMode: true });
  assert.equal((await f.post(f.request({ action: 'list' }))).status, 401);
  assert.equal(f.calls.length, 0);
});

test('friend APIs reject names, emails and ID-based invitations before invoking service', async () => {
  const f = await fixture('../app/api/friends/route.ts');
  for (const command of [
    { action: 'search', query: 'player_b' },
    { action: 'search', query: 'b@example.invalid' },
    { action: 'request', targetId: 'b' },
    { action: 'request', friendCode: 'BBBBB-BBB-BBBBB', targetId: 'b' },
    { action: 'request', friendCode: 'player_b' }
  ]) assert.equal((await f.post(f.request(command))).status, 400);
  assert.equal(f.calls.length, 0);
  assert.equal((await f.post(f.request({ action: 'request', friendCode: ' bbbbb-bbb-bbbbb ' }))).status, 200);
});
