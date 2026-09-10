import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import ts from 'typescript';
import * as cryptography from '../lib/chat-crypto.ts';
import { KeycloakStorageError } from '../lib/keycloak-storage.ts';

const compiled = ts.transpileModule(await readFile(new URL('../lib/chat-recovery-service.ts', import.meta.url), 'utf8'), {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS }
}).outputText;
const issuer = 'https://identity.example.invalid/realms/test';
function fixture({ configured = true } = {}) {
  const local = new Map(), remote = new Map(), calls = [], denied = new Set();
  let dbFail = false, providerFailure = false, afterRead;
  const tx = { chatIdentity: { findUnique: async ({ where }) => local.has(where.userId) ? { registration: local.get(where.userId) } : null } };
  const db = { $transaction: fn => fn(tx) };
  const authorize = async (_, id) => { if (denied.has(id)) throw new Error('access_denied'); return { issuer, subject: `subject-${id}` }; };
  const commands = async (id, command) => {
    await authorize(null, id); calls.push({ id, action: command.action });
    if (['identity', 'recovery-check'].includes(command.action)) return { identity: local.get(id) ?? null };
    if (command.action === 'register') {
      if (dbFail) { dbFail = false; throw new Error('database_unavailable'); }
      if (local.has(id) && local.get(id).identity.fingerprint !== command.registration.identity.fingerprint) return { error: 'identity_exists' };
      local.set(id, command.registration); return { identity: command.registration };
    }
    return { passthrough: command.action };
  };
  const client = {
    async readRecovery(subject) { if (providerFailure) throw new KeycloakStorageError('storage_unavailable'); const row = remote.get(subject) ?? null; afterRead?.(); return row; },
    async createRecovery(subject, candidate) {
      if (providerFailure) throw new KeycloakStorageError('storage_unavailable');
      if (remote.has(subject)) throw new KeycloakStorageError('storage_conflict');
      const row = { ...candidate, subject }; remote.set(subject, row); return row;
    }
  };
  const module = { exports: {} };
  vm.runInNewContext(compiled, { module, exports: module.exports, Error, fetch,
    require(name) {
      if (name === '@/lib/db') return { prisma: db };
      if (name === './keycloak-storage-journal.ts') return { createStorageJournal: () => ({}) };
      if (name === '@/lib/access-service') return { assertAccess: authorize };
      if (name === './chat-service.ts') return { chatCommand: commands };
      if (name === './chat-crypto.ts') return cryptography;
      if (name === './keycloak-storage.ts') return { KeycloakStorageError, keycloakStorageConfigured: () => configured, keycloakStorageConfig: () => ({ issuer }), createKeycloakStorageClient: () => client };
      throw new Error(name);
    }
  });
  return { run: module.exports.recoveringChatCommand, local, remote, calls, denied,
    failDatabaseOnce: () => { dbFail = true; }, failProvider: () => { providerFailure = true; }, afterRead: fn => { afterRead = fn; } };
}
const enroll = value => ({ action: 'register', registration: value.registration, recoveryCode: value.recoveryCode });

test('phase1 opt-in and new browser restore same crypto identity; only Keycloak holds recovery secret', async () => {
  const f = fixture(), a = await cryptography.createChatIdentity('a');
  const fresh = await f.run('a', { action: 'identity' });
  assert.equal(fresh.identity, null); assert.equal(fresh.recoveryMode, 'keycloak');
  const result = await f.run('a', enroll(a));
  assert.equal(result.recoveryCode, a.recoveryCode);
  assert.equal(JSON.stringify([...f.local.values()]).includes(a.recoveryCode), false);
  const identity = await f.run('a', { action: 'identity' });
  assert.equal(identity.recoveryMode, 'keycloak'); assert.equal('recoveryCode' in identity, false);
  const recovery = await f.run('a', { action: 'recover' });
  const keys = await cryptography.restoreChatIdentity('a', recovery.identity, recovery.recoveryCode);
  assert.equal(keys.identity.fingerprint, a.keys.identity.fingerprint);
  const b = await cryptography.createChatIdentity('b');
  const envelope = await cryptography.encryptMessage(b.keys, 'a', a.keys.identity, 'pair', 'Recovered history');
  assert.equal(await cryptography.decryptMessage(keys, 'b', b.keys.identity, 'pair', envelope), 'Recovered history');
});
test('provider-first commit survives failed app write and lost browser state without creating new keys', async () => {
  const f = fixture(), a = await cryptography.createChatIdentity('a');
  f.failDatabaseOnce();
  await assert.rejects(f.run('a', enroll(a)), /database_unavailable/);
  assert.equal(f.local.size, 0); assert.equal(f.remote.size, 1);
  const restored = await f.run('a', { action: 'identity' });
  assert.equal(restored.identity.identity.fingerprint, a.keys.identity.fingerprint);
  assert.equal(f.local.size, 1);
  assert.equal((await f.run('a', { action: 'recover' })).recoveryCode, a.recoveryCode);
});
test('two browser first-enrollment race converges on one immutable winner', async () => {
  const f = fixture();
  const [a, competing] = await Promise.all([cryptography.createChatIdentity('a'), cryptography.createChatIdentity('a')]);
  const replies = await Promise.all([f.run('a', enroll(a)), f.run('a', enroll(competing))]);
  assert.equal(replies[0].identity.identity.fingerprint, replies[1].identity.identity.fingerprint);
  assert.equal(replies[0].recoveryCode, replies[1].recoveryCode);
  assert.equal(f.remote.size, 1); assert.equal(f.local.size, 1);
});
test('legacy identities remain code protected until explicit correct-code escrow; no overwrite or wrong-code enrollment', async () => {
  const f = fixture(), a = await cryptography.createChatIdentity('a');
  f.local.set('a', a.registration);
  assert.equal((await f.run('a', { action: 'identity' })).recoveryMode, 'legacy');
  assert.equal((await f.run('a', { action: 'recover' })).error, 'recovery_unavailable');
  assert.equal(f.remote.size, 0);
  const replacement = await cryptography.createChatIdentity('a');
  assert.equal((await f.run('a', enroll(replacement))).error, 'invalid_identity');
  assert.equal((await f.run('a', { ...enroll(a), recoveryCode: replacement.recoveryCode })).error, 'invalid_recovery');
  assert.equal(f.remote.size, 0);
  assert.equal((await f.run('a', enroll(a))).identity.identity.fingerprint, a.keys.identity.fingerprint);
  assert.equal((await f.run('a', { action: 'identity' })).recoveryMode, 'keycloak');
});
test('actor/subject substitution, revocation during fetch and wrong-provider code fail closed', async () => {
  const a = await cryptography.createChatIdentity('a');
  for (const override of [{ actorId: 'b' }, { subject: 'subject-b' }, { recoveryCode: 'A'.repeat(43) }]) {
    const f = fixture(); await f.run('a', enroll(a));
    Object.assign(f.remote.get('subject-a'), override);
    await assert.rejects(f.run('a', { action: 'recover' }), /storage_identity_invalid|storage_response_invalid/);
  }
  const f = fixture(); await f.run('a', enroll(a));
  f.afterRead(() => f.denied.add('a'));
  await assert.rejects(f.run('a', { action: 'recover' }), /access_denied/);
});
test('storage outage/unconfigured deployment does not create replacement keys or bypass recovery; unrelated chat passes through', async () => {
  const f = fixture(); f.failProvider();
  await assert.rejects(f.run('a', { action: 'identity' }), /storage_unavailable/);
  assert.equal(f.local.size, 0);
  const disabled = fixture({ configured: false });
  assert.equal((await disabled.run('a', { action: 'identity' })).recoveryMode, 'unavailable');
  await assert.rejects(disabled.run('a', { action: 'recover' }), /storage_configuration_invalid/);
  assert.equal((await disabled.run('a', { action: 'inbox' })).passthrough, 'inbox');
});
