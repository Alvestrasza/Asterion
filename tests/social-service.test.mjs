import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import ts from 'typescript';
import * as policy from '../lib/social-policy.ts';
import * as codePolicy from '../lib/friend-code-policy.ts';
import { createHash } from 'node:crypto';
const codes = { a: 'AAAAA-AAA-AAAAA', b: 'BBBBB-BBB-BBBBB', c: 'CCCCC-CCC-CCCCC' };
const hash = code => createHash('sha256').update(code, 'utf8').digest('hex');
const source = await readFile(new URL('../lib/social-service.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
function fixture() {
  const profiles = new Map(), users = new Map(), pairs = new Map();
  const locks = [], provisioned = [];
  let inTransaction = false;
  for (const id of ['a', 'b', 'c']) {
    profiles.set(id, { userId: id, username: `player_${id}`, friendCodeHash: hash(codes[id]), discoverable: true, lastSeenAt: new Date(), windowStartedAt: new Date(), windowCount: 0, requestDay: new Date(), requestCount: 0 });
    users.set(id, { id, email: `${id}@example.invalid`, emailVerified: new Date(), access: { allowed: true }, pet: { level: 7 } });
  }
  const user = id => users.has(id) ? { ...users.get(id), socialProfile: profiles.get(id) } : null;
  const findPair = where => where.id ? pairs.get(where.id) : [...pairs.values()].find(p => p.leftId === where.leftId_rightId.leftId && p.rightId === where.leftId_rightId.rightId);
  const tx = {
    async $executeRaw(...args) { locks.push(args); },
    socialProfile: {
      async upsert({ where, create }) { if (!profiles.has(where.userId)) profiles.set(where.userId, { ...create }); return { ...profiles.get(where.userId) }; },
      async findUnique({ where }) { return where.userId ? profiles.get(where.userId) : [...profiles.values()].find(p => p.username === where.username) ?? null; },
      async update({ where, data }) { Object.assign(profiles.get(where.userId), data); return { ...profiles.get(where.userId) }; }
    },
    user: {
      async findUnique({ where }) { return user(where.id); },
      async findMany({ where }) {
        return [...users.keys()].map(user).filter(u => u.id !== where.id.not && u.socialProfile.discoverable && u.socialProfile.username &&
          u.socialProfile.friendCodeHash === where.socialProfile.is.friendCodeHash);
      }
    },
    friendship: {
      async findUnique({ where }) { return findPair(where) ?? null; },
      async findMany({ where }) { const id = where.AND[0].OR[0].leftId; return [...pairs.values()].filter(p => [p.leftId, p.rightId].includes(id)).map(p => ({ ...p, left: user(p.leftId), right: user(p.rightId) })); },
      async count({ where }) { const id = where.OR[0].leftId; return [...pairs.values()].filter(p => [p.leftId, p.rightId].includes(id) && ['pending', 'accepted'].includes(p.status)).length; },
      async upsert({ where, create, update }) {
        const old = findPair(where);
        if (old) { Object.assign(old, update, { updatedAt: new Date() }); return old; }
        const row = { id: `pair${pairs.size}`, status: 'pending', leftBlocked: false, rightBlocked: false, updatedAt: new Date(), ...create };
        pairs.set(row.id, row); return row;
      },
      async update({ where, data }) { const row = pairs.get(where.id); Object.assign(row, data, { updatedAt: new Date() }); return row; }
    }
  };
  class KnownError extends Error {}
  const db = { async $transaction(fn, options) { assert.equal(options.isolationLevel, 'Serializable'); inTransaction = true; try { return await fn(tx); } finally { inTransaction = false; } } };
  const module = { exports: {} };
  vm.runInNewContext(compiled, { exports: module.exports, module, Date, Set, Promise,
    require(name) {
      if (name === '@prisma/client') return { Prisma: { TransactionIsolationLevel: { Serializable: 'Serializable' }, PrismaClientKnownRequestError: KnownError } };
      if (name === '@/lib/db') return { prisma: db };
      if (name === '@/lib/access-service') return { assertAccess: async (_, id) => { if (!users.get(id)?.access.allowed) throw new Error('access_denied'); }, accessIsEffective: a => a?.allowed === true };
      if (name === './social-policy.ts') return policy;
      if (name === './friend-code-policy.ts') return codePolicy;
      if (name === 'node:crypto') return { createHash };
      if (name === '@/lib/friend-code-service') return { ensureFriendCode: async id => { assert.equal(inTransaction, false); provisioned.push(id); return codes[id]; } };
      throw new Error(name);
    }
  });
  return { run: module.exports.socialCommand, profiles, users, pairs, locks, provisioned };
}
test('exact opt-in code search omits email, status, level and code; name or email cannot find users', async () => {
  const f = fixture();
  let result = await f.run('a', { action: 'search', query: ' bbbbb-bbb-bbbbb ' });
  assert.equal(result.result.username, 'player_b');
  assert.deepEqual(Object.keys(result.result).sort(), ['id', 'username']);
  assert.equal((await f.run('a', { action: 'search', query: 'player_' })).result, null);
  f.users.get('b').emailVerified = null;
  assert.equal((await f.run('a', { action: 'search', query: 'b@example.invalid' })).result, null);
  f.profiles.get('b').discoverable = false;
  assert.equal((await f.run('a', { action: 'search', query: codes.b })).result, null);
});
test('request requires explicit recipient consent, including crossed requests; outsider cannot read or accept', async () => {
  const f = fixture();
  await f.run('a', { action: 'request', friendCode: codes.b });
  await f.run('b', { action: 'request', friendCode: codes.a });
  assert.equal(f.pairs.size, 1);
  assert.equal(f.pairs.get('pair0').status, 'pending');
  const pending = (await f.run('b', { action: 'list' })).friends[0];
  assert.equal(pending.status, 'incoming'); assert.equal(pending.level, null); assert.equal(pending.online, null);
  assert.equal((await f.run('c', { action: 'list' })).friends.length, 0);
  assert.equal((await f.run('c', { action: 'accept', friendshipId: 'pair0' })).error, 'target_unavailable');
  assert.equal((await f.run('a', { action: 'accept', friendshipId: 'pair0' })).error, 'request_unavailable');
  await f.run('b', { action: 'accept', friendshipId: 'pair0' });
  const friend = (await f.run('a', { action: 'list' })).friends[0];
  assert.equal(friend.level, 7); assert.equal(friend.online, true);
  assert.equal(JSON.stringify(friend).includes('@'), false);
  assert.ok(f.locks.length > 0);
});
test('removal and blocks stop disclosure; one participant cannot clear the other block', async () => {
  const f = fixture();
  await f.run('a', { action: 'request', friendCode: codes.b });
  await f.run('b', { action: 'accept', friendshipId: 'pair0' });
  await f.run('b', { action: 'block', friendshipId: 'pair0' });
  assert.equal((await f.run('a', { action: 'list' })).friends.length, 0);
  assert.equal((await f.run('a', { action: 'search', query: 'player_b' })).result, null);
  assert.equal((await f.run('a', { action: 'request', friendCode: codes.b })).error, 'target_unavailable');
  await f.run('a', { action: 'unblock', friendshipId: 'pair0' });
  assert.equal(f.pairs.get('pair0').rightBlocked, true);
  const own = (await f.run('b', { action: 'list' })).friends[0];
  assert.equal(own.status, 'blocked'); assert.equal(own.online, null);
});
test('decline enforces cooldown; revocation prevents operations and presence disclosure', async () => {
  const f = fixture();
  await f.run('a', { action: 'request', friendCode: codes.b });
  await f.run('b', { action: 'decline', friendshipId: 'pair0' });
  assert.equal((await f.run('a', { action: 'request', friendCode: codes.b })).error, 'request_cooldown');
  f.users.get('a').access.allowed = false;
  await assert.rejects(f.run('a', { action: 'heartbeat' }), /access_denied/);
  assert.equal((await f.run('b', { action: 'search', query: codes.a })).result, null);
});
test('shared abuse budgets and username uniqueness are enforced', async () => {
  const f = fixture();
  assert.equal((await f.run('a', { action: 'profile', username: 'PLAYER_B', discoverable: true })).error, 'username_unavailable');
  f.profiles.get('a').requestCount = 5;
  assert.equal((await f.run('a', { action: 'request', friendCode: codes.b })).error, 'rate_limited');
  f.profiles.get('a').windowCount = 30;
  assert.equal((await f.run('a', { action: 'search', query: 'player_b' })).error, 'rate_limited');
});

test('profile saves preserve display case and case-only changes without changing normalized uniqueness', async () => {
  const f = fixture();
  assert.equal((await f.run('b', { action: 'profile', username: '  Player_B  ', discoverable: true })).ok, true);
  assert.equal(f.profiles.get('b').username, 'player_b');
  assert.equal(f.profiles.get('b').usernameDisplay, 'Player_B');
  assert.equal((await f.run('b', { action: 'list' })).profile.username, 'Player_B');
  assert.equal((await f.run('a', { action: 'search', query: codes.b })).result.username, 'Player_B');
  assert.equal((await f.run('a', { action: 'search', query: 'B@EXAMPLE.INVALID' })).result, null);
  assert.equal((await f.run('a', { action: 'profile', username: 'pLaYeR_B', discoverable: true })).error, 'username_unavailable');
  await f.run('a', { action: 'request', friendCode: codes.b });
  assert.equal((await f.run('a', { action: 'list' })).friends[0].username, 'Player_B');
  await f.run('b', { action: 'accept', friendshipId: 'pair0' });
  assert.equal((await f.run('a', { action: 'list' })).friends[0].username, 'Player_B');
  await f.run('b', { action: 'profile', username: 'pLayer_B', discoverable: true });
  assert.equal(f.profiles.get('b').username, 'player_b');
  assert.equal((await f.run('a', { action: 'list' })).friends[0].username, 'pLayer_B');
  await f.run('a', { action: 'block', friendshipId: 'pair0' });
  const blocked = (await f.run('a', { action: 'list' })).friends[0];
  assert.equal(blocked.username, 'pLayer_B');
  assert.equal(blocked.online, null);
  assert.equal(blocked.level, null);
});

test('codes do not allow self-invites or ID bypass and request rechecks opt-in after preview', async () => {
  const f = fixture();
  assert.equal((await f.run('a', { action: 'search', query: codes.a })).result, null);
  assert.equal((await f.run('a', { action: 'request', friendCode: codes.a })).error, 'target_unavailable');
  assert.equal((await f.run('a', { action: 'request', targetId: 'b' })).error, 'target_unavailable');
  assert.equal((await f.run('a', { action: 'search', query: codes.b })).result.username, 'player_b');
  f.profiles.get('b').discoverable = false;
  assert.equal((await f.run('a', { action: 'request', friendCode: codes.b })).error, 'target_unavailable');
  assert.equal(f.pairs.size, 0);
});

test('only successful actor list provisions own code after transaction and after abuse budget', async () => {
  const f = fixture();
  const result = await f.run('a', { action: 'list' });
  assert.equal(result.profile.friendCode, codes.a);
  assert.deepEqual(f.provisioned, ['a']);
  f.profiles.get('a').windowCount = 30;
  assert.equal((await f.run('a', { action: 'list' })).error, 'rate_limited');
  assert.deepEqual(f.provisioned, ['a']);
  f.users.get('b').access.allowed = false;
  await assert.rejects(f.run('b', { action: 'list' }), /access_denied/);
  assert.deepEqual(f.provisioned, ['a']);
});
