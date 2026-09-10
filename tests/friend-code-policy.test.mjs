import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeFriendCode, FRIEND_CODE_ALPHABET } from '../lib/friend-code-policy.ts';

test('friend codes accept only exact 5-3-5 Crockford groups, case insensitive with surrounding whitespace', () => {
  assert.equal(FRIEND_CODE_ALPHABET.length, 32);
  assert.equal(normalizeFriendCode('  012ab-cde-fghjk  '), '012AB-CDE-FGHJK');
  assert.equal(normalizeFriendCode('AAAAA-AAA-AAAAſ'), null, 'Unicode lookalikes do not alias ASCII codes');
  for (const value of [undefined, null, '', 'player_name', 'person@example.invalid', '012ABCDEFGHIJ', 'AAAAA-AAA-AAAA', 'AAAAA-AAAA-AAAAA', 'AAAAA AAA AAAAA', 'AAAAA-AAA-AAAAI', 'AAAAA-AAA-AAAAO', 'AAAAA-AAA-AAAAL', 'AAAAA-AAA-AAAAU', 'AAAAA-AAA-AAAAÄ', 'AAAAA-AAA-AAAAA\nBBBBB-BBB-BBBBB']) {
    assert.equal(normalizeFriendCode(value), null, String(value));
  }
});
