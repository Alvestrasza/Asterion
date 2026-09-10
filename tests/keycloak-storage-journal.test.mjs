import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import ts from 'typescript';
import { KeycloakStorageError } from '../lib/keycloak-storage.ts';

const source = await readFile(new URL('../lib/keycloak-storage-journal.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
const issuer = 'https://identity.example.invalid/realms/friends';
const FRIEND = 'starfriends_friend_code', RECOVERY = 'starfriends_chat_recovery';
const first = '1'.repeat(64), second = '2'.repeat(64), codeHash = 'a'.repeat(64);
function fixture() {
  const rows = new Map(), accesses = new Map([['a', { issuer, subject: 'subject-a' }], ['b', { issuer, subject: 'subject-b' }]]);
  const key = row => JSON.stringify([row.issuer, row.subject, row.attribute]);
  let queue = Promise.resolve(), active = false, writeCalls = 0;
  const tx = { identityStorageWrite: {
    findUnique: async ({ where }) => rows.get(key(where.issuer_subject_attribute)) ?? null,
    createMany: async ({ data, skipDuplicates }) => {
      assert.equal(skipDuplicates, true); assert.equal(data.length, 1); writeCalls++;
      const row = data[0];
      if (rows.has(key(row)) || (row.friendCodeHash != null && [...rows.values()].some(old => old.friendCodeHash === row.friendCodeHash))) return { count: 0 };
      rows.set(key(row), { ...row, confirmed: false }); return { count: 1 };
    },
    updateMany: async ({ where, data }) => {
      assert.deepEqual(Object.keys(data), ['confirmed']); assert.equal(data.confirmed, true);
      let count = 0;
      for (const row of rows.values()) if (Object.entries(where).every(([field, value]) => row[field] === value)) { Object.assign(row, data); count++; }
      return { count };
    }
  } };
  const db = { $transaction(fn) {
    // Model assertAccess's per-actor transaction lock deterministically; no network is mocked inside.
    const run = queue.then(async () => {
      active = true; const before = structuredClone(rows);
      try { return await fn(tx); } catch (error) { rows.clear(); for (const [id, row] of before) rows.set(id, row); throw error; }
      finally { active = false; }
    });
    queue = run.catch(() => {}); return run;
  } };
  const module = { exports: {} };
  vm.runInNewContext(compiled, { module, exports: module.exports,
    require(name) {
      if (name === '@/lib/db') return { prisma: db };
      if (name === '@/lib/access-service') return { assertAccess: async (_, id) => {
        assert.equal(active, true); if (!accesses.has(id)) throw new Error('access_denied'); return { ...accesses.get(id) };
      } };
      if (name === './keycloak-storage.ts') return { KeycloakStorageError };
      throw new Error(name);
    }
  });
  const binding = { issuer, subject: 'subject-a' };
  return { journal: module.exports.createStorageJournal('a', binding, db), other: () => module.exports.createStorageJournal('b', { issuer, subject: 'subject-b' }, db),
    rows, accesses, binding, create: module.exports.createStorageJournal, db, writes: () => writeCalls };
}

test('one concurrent reservation owns the write; same and different candidates cannot obtain a second PUT permit', async () => {
  const f = fixture();
  const results = await Promise.all(Array.from({ length: 8 }, (_, index) => f.journal.reserve('subject-a', FRIEND, index % 2 ? second : first, codeHash)));
  assert.equal(results.filter(result => result.owned).length, 1);
  for (const result of results) { assert.equal(result.write.digest, first); assert.equal(result.write.confirmed, false); }
  assert.equal(f.rows.size, 1);
  await f.journal.confirm('subject-a', FRIEND, first);
  const later = await f.journal.reserve('subject-a', FRIEND, second, codeHash);
  assert.equal(later.owned, false); assert.equal(later.write.digest, first); assert.equal(later.write.confirmed, true);
});

test('recovery reservation is blocked until the same actor friend-code write is confirmed', async () => {
  const f = fixture();
  await assert.rejects(f.journal.reserve('subject-a', RECOVERY, second), /storage_conflict/);
  await f.journal.reserve('subject-a', FRIEND, first, codeHash);
  await assert.rejects(f.journal.reserve('subject-a', RECOVERY, second), /storage_conflict/);
  assert.equal(f.rows.size, 1);
  await f.journal.confirm('subject-a', FRIEND, first);
  assert.equal((await f.journal.reserve('subject-a', RECOVERY, second)).owned, true);
  assert.equal(f.rows.size, 2);
});

test('confirmation accepts only exact existing digest and never rewrites a reservation', async () => {
  const f = fixture();
  assert.equal(await f.journal.get('subject-a', FRIEND), null);
  await assert.rejects(f.journal.confirm('subject-a', FRIEND, first), /storage_conflict/);
  await f.journal.reserve('subject-a', FRIEND, first, codeHash);
  await assert.rejects(f.journal.confirm('subject-a', FRIEND, second), /storage_conflict/);
  assert.equal((await f.journal.get('subject-a', FRIEND)).confirmed, false);
  await f.journal.confirm('subject-a', FRIEND, first); await f.journal.confirm('subject-a', FRIEND, first);
  assert.equal((await f.journal.get('subject-a', FRIEND)).confirmed, true);
});

test('revoked, rebound and subject-substitution callers cannot read, reserve or confirm journal metadata', async () => {
  for (const mutate of [f => f.accesses.delete('a'), f => { f.accesses.get('a').subject = 'other'; }, f => { f.accesses.get('a').issuer = 'other'; }]) {
    const f = fixture(); await f.journal.reserve('subject-a', FRIEND, first, codeHash); mutate(f);
    for (const work of [() => f.journal.get('subject-a', FRIEND), () => f.journal.reserve('subject-a', FRIEND, first, codeHash), () => f.journal.confirm('subject-a', FRIEND, first)])
      await assert.rejects(work(), /access_denied|storage_identity_invalid/);
  }
  const f = fixture();
  await assert.rejects(f.journal.get('subject-b', FRIEND), /storage_identity_invalid/);
  f.binding.subject = 'subject-b';
  await assert.rejects(f.journal.reserve('subject-b', FRIEND, first, codeHash), /storage_identity_invalid/);
  assert.equal(f.rows.size, 0);
});

test('hash uniqueness and old-account tombstones prevent ownership transfer or replacement', async () => {
  const f = fixture(); await f.journal.reserve('subject-a', FRIEND, first, codeHash);
  await assert.rejects(f.other().reserve('subject-b', FRIEND, second, codeHash), /storage_conflict/);
  assert.equal(f.rows.size, 1);
  f.accesses.set('replacement', { issuer, subject: 'subject-a' });
  const replacement = f.create('replacement', { issuer, subject: 'subject-a' }, f.db);
  for (const work of [() => replacement.get('subject-a', FRIEND), () => replacement.reserve('subject-a', FRIEND, second, codeHash), () => replacement.confirm('subject-a', FRIEND, first)])
    await assert.rejects(work(), /storage_identity_invalid/);
  assert.equal([...f.rows.values()][0].userId, 'a');
});

test('journal accepts only metadata fields and rejects invalid attributes or digests', async () => {
  const f = fixture();
  for (const work of [() => f.journal.reserve('subject-a', 'unknown', first, codeHash),
    () => f.journal.reserve('subject-a', FRIEND, 'private key', codeHash),
    () => f.journal.reserve('subject-a', FRIEND, first),
    () => f.journal.reserve('subject-a', RECOVERY, first, codeHash),
    () => f.journal.confirm('subject-a', FRIEND, 'ciphertext')]) await assert.rejects(work(), /storage_response_invalid/);
  assert.equal(f.rows.size, 0); assert.equal(f.writes(), 0);
  await f.journal.reserve('subject-a', FRIEND, first, codeHash);
  const row = [...f.rows.values()][0];
  assert.deepEqual(Object.keys(row).sort(), ['attribute', 'confirmed', 'digest', 'friendCodeHash', 'issuer', 'subject', 'userId']);
  assert.deepEqual(Object.keys(await f.journal.get('subject-a', FRIEND)).sort(), ['confirmed', 'digest']);
});

test('journal migration deliberately retains account-deletion tombstones and metadata constraints', async () => {
  const sql = await readFile(new URL('../prisma/migrations/20260908220000_add_identity_storage_journal/migration.sql', import.meta.url), 'utf8');
  assert.doesNotMatch(sql, /REFERENCES|FOREIGN KEY/i);
  assert.match(sql, /PRIMARY KEY \("issuer", "subject", "attribute"\)/);
  assert.match(sql, /CREATE UNIQUE INDEX.*friendCodeHash/);
  assert.match(sql, /IdentityStorageWrite_digest_check/);
});
