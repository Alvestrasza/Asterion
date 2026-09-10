import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import ts from 'typescript';
import * as policy from '../lib/social-policy.ts';
import * as realCrypto from '../lib/chat-crypto.ts';

const source = await readFile(new URL('../lib/chat-service.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
const makeRegistration = id => ({ identity: { version: 1, encryptionKey: `enc-${id}`, signingKey: `sign-${id}`, fingerprint: `fingerprint-${id}` }, backup: { iv: 'opaque-iv', ciphertext: 'opaque-encrypted-backup' }, proof: 'valid' });
function fixture(cryptoImplementation) {
  const identities = new Map(), budgets = new Map(), messages = new Map(), reads = new Map(), locks = [];
  const access = new Map(['a', 'b', 'c'].map(id => [id, { allowed: true }]));
  const pairs = new Map([['pair', { id: 'pair', leftId: 'a', rightId: 'b', status: 'accepted', leftBlocked: false, rightBlocked: false }]]);
  const matches = (row, where) => (!where.friendshipId || row.friendshipId === where.friendshipId) &&
    (!where.recipientId || row.recipientId === where.recipientId) &&
    (!where.sequence?.gt || row.sequence > where.sequence.gt) && (!where.sequence?.lt || row.sequence < where.sequence.lt);
  const tx = {
    async $executeRaw(...args) { locks.push(args); },
    chatBudget: {
      async upsert({ where }) { if (!budgets.has(where.userId)) budgets.set(where.userId, { windowStartedAt: new Date(), windowCount: 0, sendCount: 0, registrationCount: 0, dayStartedAt: new Date(), daySendCount: 0 }); return { ...budgets.get(where.userId) }; },
      async update({ where, data }) { Object.assign(budgets.get(where.userId), data); }
    },
    chatIdentity: {
      async findUnique({ where }) { return where.userId ? identities.get(where.userId) ?? null : [...identities.values()].find(row => row.fingerprint === where.fingerprint) ?? null; },
      async create({ data }) { identities.set(data.userId, data); return data; }
    },
    friendship: {
      async findUnique({ where }) { return pairs.get(where.id) ?? null; },
      async findMany({ where }) { const id = where.OR[0].leftId; return [...pairs.values()].filter(row => [row.leftId, row.rightId].includes(id) && row.status === 'accepted' && !row.leftBlocked && !row.rightBlocked)
        .map(row => ({ ...row, left: { access: access.get(row.leftId) }, right: { access: access.get(row.rightId) } })); }
    },
    socialProfile: { async findUnique({ where }) { return { username: `player_${where.userId}`, usernameDisplay: `Player_${where.userId}` }; } },
    chatMessage: {
      async findUnique({ where }) { return messages.get(where.id) ?? null; },
      async create({ data }) { const row = { ...data, sequence: BigInt(messages.size + 1), createdAt: new Date() }; messages.set(row.id, row); return row; },
      async findMany({ where, take }) { return [...messages.values()].filter(row => matches(row, where)).sort((a, b) => a.sequence < b.sequence ? 1 : -1).slice(0, take); },
      async count({ where }) { return [...messages.values()].filter(row => matches(row, where)).length; }
    },
    chatRead: {
      async findUnique({ where }) { const key = where.userId_friendshipId; return reads.get(`${key.userId}/${key.friendshipId}`) ?? null; },
      async upsert({ where, create, update }) { const key = `${where.userId_friendshipId.userId}/${where.userId_friendshipId.friendshipId}`; const old = reads.get(key); reads.set(key, old ? { ...old, ...update } : create); }
    }
  };
  class KnownError extends Error {}
  const db = { async $transaction(fn, options) { assert.equal(options.isolationLevel, 'Serializable'); return fn(tx); } };
  const module = { exports: {} };
  vm.runInNewContext(compiled, { exports: module.exports, module, Date, BigInt, Set, Promise,
    require(name) {
      if (name === '@prisma/client') return { Prisma: { TransactionIsolationLevel: { Serializable: 'Serializable' }, PrismaClientKnownRequestError: KnownError } };
      if (name === '@/lib/db') return { prisma: db };
      if (name === '@/lib/access-service') return { assertAccess: async (_, id) => { locks.push(id); if (!access.get(id)?.allowed) throw new Error('access_denied'); return { issuer: 'https://identity.example.invalid/realms/test', subject: `subject-${id}` }; }, accessIsEffective: value => value?.allowed === true };
      if (name === './social-policy.ts') return policy;
      if (name === './chat-crypto.ts') return cryptoImplementation ?? { verifyRegistration: async (_, value) => value.proof === 'valid', verifyEnvelope: async value => value.signature === 'valid', envelopeDigest: async value => JSON.stringify(value) };
      throw new Error(name);
    }
  });
  const run = module.exports.chatCommand;
  const register = async id => run(id, { action: 'register', registration: makeRegistration(id) });
  const envelope = (id = 'one', senderId = 'a', recipientId = 'b') => ({ version: 1, id, friendshipId: 'pair', senderId, recipientId,
    senderFingerprint: `fingerprint-${senderId}`, recipientFingerprint: `fingerprint-${recipientId}`, iv: 'opaque', ciphertext: 'encrypted', senderKey: 'wrapped-a', recipientKey: 'wrapped-b', signature: 'valid' });
  return { run, register, envelope, identities, budgets, messages, reads, access, pairs, locks };
}

test('chat identity registration is immutable, proof checked, account scoped and backups never disclosed to peer', async () => {
  const f = fixture();
  assert.equal((await f.run('a', { action: 'identity' })).identity, null);
  assert.equal((await f.run('a', { action: 'register', registration: { ...makeRegistration('a'), proof: 'invalid' } })).error, 'invalid_identity');
  await f.register('a'); await f.register('b');
  assert.ok((await f.register('a')).identity);
  assert.equal((await f.run('a', { action: 'register', registration: makeRegistration('replacement') })).error, 'identity_exists');
  assert.equal(f.identities.get('a').fingerprint, 'fingerprint-a');
  const opened = await f.run('a', { action: 'open', friendshipId: 'pair' });
  assert.equal(opened.peerName, 'Player_b'); assert.equal(opened.identity.fingerprint, 'fingerprint-b');
  assert.equal('backup' in opened.identity, false);
  assert.equal((await f.run('c', { action: 'identity' })).identity, null);
});

test('recovery attachment rechecks expected issuer and subject inside the persistence transaction', async () => {
  const f = fixture();
  for (const binding of [{ issuer: 'https://other.example.invalid/realms/test', subject: 'subject-a' },
    { issuer: 'https://identity.example.invalid/realms/test', subject: 'subject-b' }]) {
    const result = await f.run('a', { action: 'register', registration: makeRegistration('a') }, undefined, binding);
    assert.equal(result.error, 'invalid_identity'); assert.equal(f.identities.size, 0);
  }
  assert.ok((await f.run('a', { action: 'register', registration: makeRegistration('a') }, undefined,
    { issuer: 'https://identity.example.invalid/realms/test', subject: 'subject-a' })).identity);
});

test('outsiders, unaccepted friendships, either block and inactive participants cannot send or read', async () => {
  const f = fixture(); await f.register('a'); await f.register('b');
  assert.equal((await f.run('c', { action: 'open', friendshipId: 'pair' })).error, 'conversation_unavailable');
  for (const state of [{ status: 'pending' }, { status: 'closed' }, { status: 'accepted', leftBlocked: true }, { leftBlocked: false, rightBlocked: true }]) {
    Object.assign(f.pairs.get('pair'), state);
    assert.equal((await f.run('a', { action: 'open', friendshipId: 'pair' })).error, 'conversation_unavailable');
    assert.equal((await f.run('a', { action: 'send', envelope: f.envelope() })).error, 'conversation_unavailable');
  }
  Object.assign(f.pairs.get('pair'), { status: 'accepted', rightBlocked: false });
  f.access.get('b').allowed = false;
  await assert.rejects(f.run('a', { action: 'open', friendshipId: 'pair' }), /access_denied/);
  await assert.rejects(f.run('a', { action: 'send', envelope: f.envelope() }), /access_denied/);
  assert.equal(f.messages.size, 0);
});

test('send binds both identities, validates signature, stores only envelope and provides exact idempotency', async () => {
  const f = fixture(); await f.register('a'); await f.register('b');
  for (const override of [{ senderId: 'b' }, { recipientId: 'c' }, { recipientFingerprint: 'changed' }, { senderFingerprint: 'changed' }, { signature: 'invalid' }])
    assert.equal((await f.run('a', { action: 'send', envelope: { ...f.envelope(), ...override } })).error, 'invalid_message');
  const first = await f.run('a', { action: 'send', envelope: f.envelope() });
  const second = await f.run('a', { action: 'send', envelope: f.envelope() });
  assert.equal(first.message.sequence, second.message.sequence); assert.equal(f.messages.size, 1);
  assert.equal((await f.run('a', { action: 'send', envelope: { ...f.envelope(), ciphertext: 'different' } })).error, 'message_conflict');
  assert.equal(f.messages.get('one').envelope.ciphertext, 'encrypted');
  assert.equal('plaintext' in f.messages.get('one'), false);
  assert.deepEqual(f.locks.filter(value => typeof value === 'string').slice(-2), ['a', 'b']);
});

test('unread counts and acknowledgements are recipient scoped, monotonic, and revoked on block', async () => {
  const f = fixture(); await f.register('a'); await f.register('b');
  await f.run('a', { action: 'send', envelope: f.envelope('one') });
  await f.run('a', { action: 'send', envelope: f.envelope('two') });
  assert.equal((await f.run('a', { action: 'inbox' })).unread.length, 0);
  assert.equal((await f.run('b', { action: 'inbox' })).unread[0].count, 2);
  assert.equal((await f.run('a', { action: 'read', friendshipId: 'pair', messageId: 'two' })).error, 'message_unavailable');
  assert.equal((await f.run('b', { action: 'read', friendshipId: 'pair', messageId: 'future' })).error, 'message_unavailable');
  await f.run('b', { action: 'read', friendshipId: 'pair', messageId: 'two' });
  await f.run('b', { action: 'read', friendshipId: 'pair', messageId: 'one' });
  assert.equal(f.reads.get('b/pair').sequence, 2n);
  assert.equal((await f.run('b', { action: 'inbox' })).unread.length, 0);
  f.pairs.get('pair').leftBlocked = true;
  assert.equal((await f.run('b', { action: 'read', friendshipId: 'pair', messageId: 'one' })).error, 'conversation_unavailable');
});

test('history pagination is bounded, chronological, scoped and excludes another friendship', async () => {
  const f = fixture(); await f.register('a'); await f.register('b');
  for (let i = 1; i <= 55; i++) f.messages.set(`m${i}`, { id: `m${i}`, sequence: BigInt(i), friendshipId: 'pair', senderId: 'a', recipientId: 'b', envelope: f.envelope(`m${i}`), createdAt: new Date() });
  f.messages.set('foreign', { id: 'foreign', sequence: 100n, friendshipId: 'other', senderId: 'b', recipientId: 'c', envelope: f.envelope('foreign'), createdAt: new Date() });
  const latest = await f.run('a', { action: 'open', friendshipId: 'pair' });
  assert.equal(latest.messages.length, 50); assert.equal(latest.messages[0].sequence, '6'); assert.equal(latest.hasMore, true);
  const older = await f.run('a', { action: 'open', friendshipId: 'pair', before: '6' });
  assert.equal(older.messages.length, 5); assert.equal(older.messages[0].sequence, '1'); assert.equal(older.hasMore, false);
});

test('durable chat budgets limit failed crypto attempts, sending and polling independently of social profile', async () => {
  const f = fixture(); await f.register('a'); await f.register('b');
  for (let i = 0; i < 20; i++) await f.run('a', { action: 'send', envelope: { ...f.envelope(`m${i}`), signature: 'invalid' } });
  assert.equal((await f.run('a', { action: 'send', envelope: f.envelope() })).error, 'rate_limited');
  assert.ok('unread' in await f.run('a', { action: 'inbox' }));
  f.budgets.get('a').windowCount = 180;
  assert.equal((await f.run('a', { action: 'inbox' })).error, 'rate_limited');
  f.budgets.get('a').windowStartedAt = new Date(Date.now() - 61000);
  f.budgets.get('a').daySendCount = 1000;
  assert.equal((await f.run('a', { action: 'send', envelope: f.envelope() })).error, 'rate_limited');
});

test('real WebCrypto registration, encrypted service storage, peer read and recipient decryption integrate', async () => {
  const f = fixture(realCrypto);
  const [alice, bob] = await Promise.all(['a', 'b'].map(realCrypto.createChatIdentity));
  await f.run('a', { action: 'register', registration: alice.registration });
  await f.run('b', { action: 'register', registration: bob.registration });
  const envelope = await realCrypto.encryptMessage(alice.keys, 'b', bob.keys.identity, 'pair', 'Hello Grüße 🌟');
  const sent = await f.run('a', { action: 'send', envelope });
  assert.equal(sent.message.id, envelope.id);
  const opened = await f.run('b', { action: 'open', friendshipId: 'pair' });
  assert.equal(await realCrypto.decryptMessage(bob.keys, 'a', opened.identity, 'pair', opened.messages[0]), 'Hello Grüße 🌟');
  assert.equal(JSON.stringify([...f.messages.values()].map(row => row.envelope)).includes('Hello'), false);
  const tampered = { ...envelope, id: crypto.randomUUID(), recipientKey: envelope.senderKey };
  assert.equal((await f.run('a', { action: 'send', envelope: tampered })).error, 'invalid_message');
});
