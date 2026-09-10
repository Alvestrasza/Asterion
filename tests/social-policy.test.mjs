import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeUsername, displayUsername, isOnline, mayAccept, maySeePresence } from '../lib/social-policy.ts';
const row = { leftId: 'a', rightId: 'b', requestedBy: 'a', status: 'pending', leftBlocked: false, rightBlocked: false };
test('only exact safe usernames normalize; email is not a username', () => {
  assert.equal(normalizeUsername('  Star_Friend '), 'star_friend');
  for (const input of ['ab', 'a@b.test', '<script>', 'a b', 'x'.repeat(33)]) assert.equal(normalizeUsername(input), null);
});
test('display names preserve entered case without inventing missing or stale case', () => {
  assert.equal(displayUsername({ username: 'star_friend', usernameDisplay: 'Star_Friend' }), 'Star_Friend');
  assert.equal(displayUsername({ username: 'star_friend', usernameDisplay: null }), 'star_friend');
  assert.equal(displayUsername({ username: 'renamed', usernameDisplay: 'Star_Friend' }), 'renamed');
  assert.equal(displayUsername({ username: null, usernameDisplay: 'Star_Friend' }), null);
  assert.equal(displayUsername(null), null);
});
test('only recipient can accept an unblocked pending request', () => {
  assert.equal(mayAccept(row, 'b'), true);
  for (const actor of ['a', 'outsider']) assert.equal(mayAccept(row, actor), false);
  assert.equal(mayAccept({ ...row, leftBlocked: true }, 'b'), false);
  assert.equal(mayAccept({ ...row, status: 'closed' }, 'b'), false);
});
test('presence is visible only to accepted unblocked participants', () => {
  assert.equal(maySeePresence(row, 'b'), false);
  const accepted = { ...row, status: 'accepted' };
  assert.equal(maySeePresence(accepted, 'b'), true);
  assert.equal(maySeePresence(accepted, 'outsider'), false);
  assert.equal(maySeePresence({ ...accepted, rightBlocked: true }, 'a'), false);
});
test('presence expires and future timestamps fail closed', () => {
  const now = new Date(100000);
  assert.equal(isOnline(new Date(99999), now), true);
  assert.equal(isOnline(new Date(10000), now), false);
  assert.equal(isOnline(new Date(100001), now), false);
  assert.equal(isOnline(null, now), false);
});
