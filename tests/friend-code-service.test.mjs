import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import vm from 'node:vm';
import ts from 'typescript';
import { KeycloakStorageError } from '../lib/keycloak-storage.ts';

const compiled = ts.transpileModule(await readFile(new URL('../lib/friend-code-service.ts', import.meta.url), 'utf8'), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS }
}).outputText;
const issuer = 'https://identity.example.invalid/realms/test';
const code = '01234-ABC-56789';
const hash = createHash('sha256').update(code, 'utf8').digest('hex');
function fixture() {
  const access = new Map([['a', { issuer, subject: 'subject-a' }], ['b', { issuer, subject: 'subject-b' }]]);
  const profiles = new Map(), calls = [];
  let inTransaction = false, afterNetwork, retries = 0;
  class KnownError extends Error { constructor(code) { super(code); this.code = code; } }
  const tx = { socialProfile: {
    findUnique: async ({ where }) => profiles.get(where.userId) ?? null,
    upsert: async ({ where, create, update }) => {
      if (retries > 0) { retries--; throw new KnownError('P2034'); }
      const next = { ...(profiles.get(where.userId) ?? create), ...update };
      if ([...profiles.values()].some(row => row.userId !== where.userId && row.friendCodeHash === next.friendCodeHash)) throw new KnownError('P2002');
      profiles.set(where.userId, next); return next;
    }
  } };
  const db = { async $transaction(fn, options) {
    if (options) assert.equal(options.isolationLevel, 'Serializable');
    inTransaction = true; try { return await fn(tx); } finally { inTransaction = false; }
  } };
  const module = { exports: {} };
  vm.runInNewContext(compiled, { module, exports: module.exports, Error, fetch,
    require(name) {
      if (name === 'node:crypto') return { createHash };
      if (name === '@prisma/client') return { Prisma: { TransactionIsolationLevel: { Serializable: 'Serializable' }, PrismaClientKnownRequestError: KnownError } };
      if (name === '@/lib/db') return { prisma: db };
      if (name === './keycloak-storage-journal.ts') return { createStorageJournal: () => ({}) };
      if (name === '@/lib/access-service') return { assertAccess: async (_, id) => {
        assert.equal(inTransaction, true);
        if (!access.has(id)) throw new Error('access_denied');
        return { ...access.get(id) };
      } };
      if (name === './keycloak-storage.ts') return { KeycloakStorageError, keycloakStorageConfig: () => ({ issuer }), createKeycloakStorageClient: () => ({
        ensureFriendCode: async subject => { assert.equal(inTransaction, false); calls.push(subject); afterNetwork?.(); return code; }
      }) };
      throw new Error(name);
    }
  });
  return { run: module.exports.ensureFriendCode, profiles, access, calls, afterNetwork: fn => { afterNetwork = fn; }, failSerialization: count => { retries = count; } };
}

test('friend-code service verifies account binding and persists only canonical lookup hash', async () => {
  const f = fixture();
  assert.equal(await f.run('a'), code);
  assert.deepEqual(f.calls, ['subject-a']);
  assert.equal(f.profiles.get('a').friendCodeHash, hash);
  assert.equal(JSON.stringify([...f.profiles.values()]).includes(code), false);
  assert.equal(await f.run('a'), code);
  assert.equal(f.profiles.size, 1);
});

test('friend-code service rejects wrong issuer and denied account before external provisioning', async () => {
  const f = fixture();
  f.access.get('a').issuer = 'https://other.example.invalid/realms/test';
  await assert.rejects(f.run('a'), /storage_identity_invalid/);
  f.access.delete('b');
  await assert.rejects(f.run('b'), /access_denied/);
  assert.equal(f.calls.length, 0); assert.equal(f.profiles.size, 0);
});

test('friend-code service rechecks revocation and subject changes after external provisioning', async () => {
  for (const mutation of [f => f.access.delete('a'), f => { f.access.get('a').subject = 'replacement'; }, f => { f.access.get('a').issuer = 'replacement'; }]) {
    const f = fixture(); f.afterNetwork(() => mutation(f));
    await assert.rejects(f.run('a'), /access_denied|storage_identity_invalid/);
    assert.equal(f.profiles.size, 0);
  }
});

test('immutable hash mismatch and another account using same code never replace either mapping', async () => {
  const f = fixture();
  f.profiles.set('a', { userId: 'a', friendCodeHash: 'previous' });
  await assert.rejects(f.run('a'), /storage_conflict/);
  assert.equal(f.profiles.get('a').friendCodeHash, 'previous');
  f.profiles.set('a', { userId: 'a', friendCodeHash: hash });
  await assert.rejects(f.run('b'), /P2002/);
  assert.equal(f.profiles.get('a').friendCodeHash, hash);
  assert.equal(f.profiles.has('b'), false);
});

test('serialization conflicts retry only local mirroring and remain bounded', async () => {
  const f = fixture(); f.failSerialization(3);
  assert.equal(await f.run('a'), code); assert.equal(f.calls.length, 1);
  const exhausted = fixture(); exhausted.failSerialization(4);
  await assert.rejects(exhausted.run('a'), /P2034/);
  assert.equal(exhausted.calls.length, 1); assert.equal(exhausted.profiles.size, 0);
});
