import test, { after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { randomBytes, createHash } from 'node:crypto';
import { createKeycloakStorageClient, keycloakStorageConfig, keycloakStorageConfigured, KeycloakStorageError } from '../lib/keycloak-storage.ts';
import { createChatIdentity } from '../lib/chat-crypto.ts';

const directory = await mkdtemp(join(tmpdir(), 'starfriends-storage-'));
const keyFile = join(directory, 'key'), otherKeyFile = join(directory, 'other-key');
await writeFile(keyFile, randomBytes(32).toString('base64url'), { mode: 0o600 });
await writeFile(otherKeyFile, randomBytes(32).toString('base64url'), { mode: 0o600 });
after(() => rm(directory, { recursive: true, force: true }));
const config = { issuer: 'https://login.example.invalid/auth/realms/friends', privateOrigin: 'https://private.example.invalid',
  clientId: 'friends-storage', clientSecret: 'fixture-only', masterKeyFile: keyFile };
const FRIEND = 'starfriends_friend_code', RECOVERY = 'starfriends_chat_recovery';
const hash = value => createHash('sha256').update(value, 'utf8').digest('hex');

function fixture() {
  const calls = [], rows = new Map();
  let attributes = { external: ['preserve', 'both'] }, unmanaged = { historic: ['also preserve'] };
  let putMode = 'normal', getFailure, reserveCrash = false;
  const journal = {
    async get(subject, attribute) { return rows.get(`${subject}/${attribute}`) ?? null; },
    async reserve(subject, attribute, digest, friendCodeHash) {
      const id = `${subject}/${attribute}`, previous = rows.get(id);
      if (previous) return { owned: false, write: previous };
      if (attribute === RECOVERY && !rows.get(`${subject}/${FRIEND}`)?.confirmed) throw new KeycloakStorageError('storage_write_pending');
      if (attribute === FRIEND && [...rows.values()].some(row => row.friendCodeHash === friendCodeHash)) throw new KeycloakStorageError('storage_conflict');
      const entry = { digest, confirmed: false, ...(friendCodeHash ? { friendCodeHash } : {}) }; rows.set(id, entry);
      if (reserveCrash) throw new Error('crash_after_marker');
      return { owned: true, write: entry };
    },
    async confirm(subject, attribute, digest) {
      const row = rows.get(`${subject}/${attribute}`);
      assert.equal(row.digest, digest); row.confirmed = true;
    }
  };
  const fetcher = async (url, init) => {
    calls.push({ url, init });
    assert.equal(init.cache, 'no-store'); assert.equal(init.redirect, 'error'); assert.ok(init.signal instanceof AbortSignal);
    if (url.endsWith('/token')) {
      assert.equal(new URL(url).origin, 'https://login.example.invalid');
      assert.equal(init.body.get('client_id'), 'friends-storage');
      assert.equal(init.headers.has('Authorization'), false);
      return Response.json({ access_token: 'fixture-token' });
    }
    assert.equal(new URL(url).origin, 'https://private.example.invalid');
    assert.equal(init.headers.get('Authorization'), 'Bearer fixture-token');
    assert.equal(init.body?.includes('fixture-only') ?? false, false);
    if (init.method === 'GET' && getFailure) return getFailure(url, init);
    if (url.endsWith('/unmanagedAttributes')) return Response.json(unmanaged);
    const subject = url.split('/').at(-1);
    if (init.method === 'GET') return Response.json({ id: subject, username: 'PlayerName', firstName: 'Player', lastName: 'Name',
      email: 'player@example.invalid', enabled: true, requiredActions: ['UPDATE_PASSWORD'], attributes });
    assert.equal(init.method, 'PUT');
    const body = JSON.parse(init.body);
    assert.equal('enabled' in body, false); assert.equal('requiredActions' in body, false); assert.equal('id' in body, false);
    assert.equal(body.username, 'PlayerName');
    if (putMode === 'absent') throw new Error('network_unknown');
    attributes = body.attributes; unmanaged = {};
    if (putMode === 'lost') throw new Error('response_lost_after_commit');
    return new Response(null, { status: 204 });
  };
  const client = createKeycloakStorageClient(config, fetcher, journal);
  return { client, calls, rows, journal, fetcher, get attrs() { return attributes; },
    putMode: mode => { putMode = mode; }, failGet: failure => { getFailure = failure; }, crashReservation: () => { reserveCrash = true; },
    puts: () => calls.filter(call => call.init.method === 'PUT') };
}
async function registration(actor = 'actor-a') {
  const generated = await createChatIdentity(actor);
  return { actorId: actor, fingerprint: generated.registration.identity.fingerprint, recoveryCode: generated.recoveryCode, registration: generated.registration };
}

test('first login generates stable random formatted code via standard private Admin API, preserving profile/managed/unmanaged attributes', async () => {
  const f = fixture(), code = await f.client.ensureFriendCode('subject-a');
  assert.match(code, /^[0-9A-HJKMNP-TV-Z]{5}-[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{5}$/);
  assert.equal(await f.client.ensureFriendCode('subject-a'), code);
  assert.equal(f.puts().length, 1);
  assert.equal(f.puts()[0].url, 'https://private.example.invalid/auth/admin/realms/friends/users/subject-a');
  assert.deepEqual(f.attrs.external, ['preserve', 'both']); assert.deepEqual(f.attrs.historic, ['also preserve']);
  assert.equal(f.rows.get(`subject-a/${FRIEND}`).digest, hash(code));
  assert.equal(JSON.stringify([...f.rows.values()]).includes(code), false);
  assert.ok(f.calls.every(call => !call.url.includes('starfriends-storage')));
});

test('configuration rejects ambiguous origins, missing independent key path and inherited sync credentials before I/O', async () => {
  assert.equal(keycloakStorageConfigured({}), false);
  assert.equal(keycloakStorageConfigured({ ASTERION_CHAT_RECOVERY_KEY_FILE: keyFile }), true);
  assert.throws(() => keycloakStorageConfig({ ASTERION_KEYCLOAK_ADMIN_CLIENT_ID: 'sync', ASTERION_KEYCLOAK_ADMIN_CLIENT_SECRET: 'fixture' }), /storage_configuration_invalid/);
  for (const privateOrigin of ['', 'http://private.example.invalid', 'https://private.example.invalid/', 'https://private.example.invalid/admin',
    'https://private.example.invalid:443', 'https://127.0.0.1', 'https://[::1]', 'https://user:secret@private.example.invalid'])
    assert.throws(() => createKeycloakStorageClient({ ...config, privateOrigin }), /storage_configuration_invalid/);
  for (const issuer of ['https://login.example.invalid/realms/a%2fb', 'https://login.example.invalid/realms/a?x=y', 'https://login.example.invalid/realms/a/'])
    assert.throws(() => createKeycloakStorageClient({ ...config, issuer }), /storage_configuration_invalid/);
  assert.throws(() => createKeycloakStorageClient({ ...config, masterKeyFile: 'relative/key' }), /storage_configuration_invalid/);
  let network = 0;
  await assert.rejects(createKeycloakStorageClient(config, async () => { network++; }).ensureFriendCode('subject-a'), /storage_configuration_invalid/);
  assert.equal(network, 0);
});

test('recovery attribute and Admin request contain only app-key encrypted envelope; correct independent key restores exact record', async () => {
  const f = fixture(), candidate = await registration();
  const code = await f.client.ensureFriendCode('subject-a');
  assert.equal(await f.client.readRecovery('subject-a'), null);
  assert.deepEqual(await f.client.createRecovery('subject-a', candidate), { ...candidate, subject: 'subject-a' });
  assert.deepEqual(await f.client.readRecovery('subject-a'), { ...candidate, subject: 'subject-a' });
  assert.equal(f.attrs[FRIEND][0], code);
  const value = f.attrs[RECOVERY][0];
  assert.equal(value.includes(candidate.recoveryCode), false); assert.equal(value.includes(candidate.registration.backup.ciphertext), false);
  assert.equal(f.puts().some(call => call.init.body.includes(candidate.recoveryCode)), false);
  assert.equal(JSON.stringify([...f.rows.values()]).includes(value), false);
  const wrongKey = createKeycloakStorageClient({ ...config, masterKeyFile: otherKeyFile }, f.fetcher, f.journal);
  await assert.rejects(wrongKey.readRecovery('subject-a'), /^KeycloakStorageError: storage_response_invalid$/);
  const missingKey = createKeycloakStorageClient({ ...config, masterKeyFile: join(directory, 'missing') }, f.fetcher, f.journal);
  await assert.rejects(missingKey.readRecovery('subject-a'), /^KeycloakStorageError: storage_key_unavailable$/);
  const directoryKey = createKeycloakStorageClient({ ...config, masterKeyFile: directory }, f.fetcher, f.journal);
  await assert.rejects(directoryKey.readRecovery('subject-a'), /^KeycloakStorageError: storage_key_unavailable$/);
  const malformed = join(directory, 'malformed'); await writeFile(malformed, 'not-a-256-bit-key', { mode: 0o600 });
  const malformedKey = createKeycloakStorageClient({ ...config, masterKeyFile: malformed }, f.fetcher, f.journal);
  await assert.rejects(malformedKey.readRecovery('subject-a'), /^KeycloakStorageError: storage_key_unavailable$/);
});

test('immutable enrollment returns canonical winner, never replaces existing material with another browser candidate', async () => {
  const f = fixture(); await f.client.ensureFriendCode('subject-a');
  const [a, b] = await Promise.all([registration(), registration()]);
  const secondNode = createKeycloakStorageClient(config, f.fetcher, f.journal);
  const results = await Promise.allSettled([f.client.createRecovery('subject-a', a), secondNode.createRecovery('subject-a', b)]);
  assert.equal(results.some(result => result.status === 'fulfilled'), true);
  assert.equal(f.puts().length, 2);
  const winner = await f.client.readRecovery('subject-a');
  assert.ok([a.fingerprint, b.fingerprint].includes(winner.fingerprint));
  assert.deepEqual(await f.client.createRecovery('subject-a', b), winner);
  assert.equal(f.puts().length, 2);
});

test('two independent first-login clients can attempt at most one friend-code PUT and converge after readback', async () => {
  const f = fixture(), secondNode = createKeycloakStorageClient(config, f.fetcher, f.journal);
  const results = await Promise.allSettled([f.client.ensureFriendCode('subject-a'), secondNode.ensureFriendCode('subject-a')]);
  assert.equal(results.some(result => result.status === 'fulfilled'), true);
  assert.equal(f.puts().length, 1);
  assert.equal(await f.client.ensureFriendCode('subject-a'), await secondNode.ensureFriendCode('subject-a'));
  assert.equal(f.puts().length, 1);
});

test('a stale recovery GET snapshot without the confirmed friend attribute cannot reserve or issue a PUT', async () => {
  const f = fixture(); await f.client.ensureFriendCode('subject-a');
  f.failGet(url => Response.json(url.endsWith('/unmanagedAttributes') ? {} : { id: 'subject-a', username: 'PlayerName', attributes: {} }));
  await assert.rejects(f.client.createRecovery('subject-a', await registration()), /storage_conflict/);
  assert.equal(f.puts().length, 1); assert.equal(f.rows.size, 1);
});

test('lost PUT reply is reconciled by reading exact digest, with no second write', async () => {
  const f = fixture(); f.putMode('lost');
  const code = await f.client.ensureFriendCode('subject-a');
  assert.equal(await f.client.ensureFriendCode('subject-a'), code);
  assert.equal(f.puts().length, 1);
  const candidate = await registration();
  assert.deepEqual(await f.client.createRecovery('subject-a', candidate), { ...candidate, subject: 'subject-a' });
  assert.equal(f.puts().length, 2); assert.ok([...f.rows.values()].every(row => row.confirmed));
});

test('uncertain absent write blocks retries and later recovery; delayed single write can be reconciled without overwriting', async () => {
  const f = fixture(); f.putMode('absent');
  await assert.rejects(f.client.ensureFriendCode('subject-a'), /storage_write_pending/);
  f.putMode('normal');
  await assert.rejects(f.client.ensureFriendCode('subject-a'), /storage_write_pending/);
  await assert.rejects(f.client.createRecovery('subject-a', await registration()), /storage_write_pending/);
  assert.equal(f.puts().length, 1); assert.equal(f.rows.size, 1);
  const pendingBody = JSON.parse(f.puts()[0].init.body);
  Object.assign(f.attrs, pendingBody.attributes);
  assert.equal(await f.client.ensureFriendCode('subject-a'), f.attrs[FRIEND][0]);
  assert.equal(f.puts().length, 1);
  await f.client.createRecovery('subject-a', await registration());
  assert.equal(f.puts().length, 2);
});

test('crash after committed reservation but before PUT never grants another attempt', async () => {
  const f = fixture(); f.crashReservation();
  await assert.rejects(f.client.ensureFriendCode('subject-a'), /crash_after_marker/);
  await assert.rejects(f.client.ensureFriendCode('subject-a'), /storage_write_pending/);
  assert.equal(f.puts().length, 0); assert.equal(f.rows.size, 1);
});

test('confirmed attribute removal or substitution is a conflict, not authorization to recreate', async () => {
  for (const replacement of [null, ['01234-ABC-56789']]) {
    const f = fixture(); await f.client.ensureFriendCode('subject-a');
    if (replacement) f.attrs[FRIEND] = replacement; else delete f.attrs[FRIEND];
    await assert.rejects(f.client.ensureFriendCode('subject-a'), /storage_conflict/);
    await assert.rejects(f.client.createRecovery('subject-a', await registration()), /storage_conflict/);
    assert.equal(f.puts().length, 1);
  }
});

test('untracked or multi-valued fields are never adopted and incorrect subject/path cannot provision', async () => {
  for (const value of [['01234-ABC-56789'], [], ['01234-ABC-56789', 'ABCDE-FGH-12345']]) {
    const f = fixture(); f.attrs[FRIEND] = value;
    await assert.rejects(f.client.ensureFriendCode('subject-a'), /storage_conflict|storage_response_invalid/);
    assert.equal(f.puts().length, 0);
  }
  const f = fixture(); await assert.rejects(f.client.ensureFriendCode('../victim'), /storage_identity_invalid/); assert.equal(f.calls.length, 0);
  f.failGet(() => Response.json({ id: 'victim', username: 'Another' }));
  await assert.rejects(f.client.ensureFriendCode('subject-a'), /storage_response_invalid/);
});

test('tampered envelope, changed actor AAD and issuer/subject copying fail closed even if a digest is re-pinned', async () => {
  const f = fixture(); await f.client.ensureFriendCode('subject-a'); await f.client.createRecovery('subject-a', await registration());
  const original = f.attrs[RECOVERY][0];
  const entry = f.rows.get(`subject-a/${RECOVERY}`);
  const modified = { ...JSON.parse(original), actorId: 'actor-b' }; f.attrs[RECOVERY] = [JSON.stringify(modified)];
  entry.digest = hash(f.attrs[RECOVERY][0]);
  await assert.rejects(f.client.readRecovery('subject-a'), /storage_response_invalid/);
  f.attrs[RECOVERY] = [original]; entry.digest = hash(original);
  const otherIssuer = createKeycloakStorageClient({ ...config, issuer: 'https://login.example.invalid/auth/realms/other' }, f.fetcher, f.journal);
  await assert.rejects(otherIssuer.readRecovery('subject-a'), /storage_response_invalid/);
  f.rows.set(`subject-b/${RECOVERY}`, { ...entry });
  await assert.rejects(f.client.readRecovery('subject-b'), /storage_response_invalid/);
});

test('missing users, permission, oversized/truncated/TLS failures are closed and sanitized', async () => {
  for (const status of [401, 403, 404]) {
    const f = fixture(); f.failGet(() => new Response('private diagnostic', { status }));
    await assert.rejects(f.client.readRecovery('subject-a'), status === 404 ? /^KeycloakStorageError: storage_identity_invalid$/ : /^KeycloakStorageError: storage_permission_denied$/);
  }
  for (const response of ['x'.repeat(131073), '{broken']) {
    const f = fixture(); f.failGet(() => new Response(response));
    await assert.rejects(f.client.readRecovery('subject-a'), /storage_response_invalid/);
  }
  const f = fixture(); f.failGet(() => { throw new Error('certificate secret'); });
  await assert.rejects(f.client.readRecovery('subject-a'), /^KeycloakStorageError: storage_unavailable$/);
});
