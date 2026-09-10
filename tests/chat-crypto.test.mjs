import test from 'node:test';
import assert from 'node:assert/strict';
import { createChatIdentity, restoreChatIdentity, verifyRegistration, encryptMessage, decryptMessage, verifyEnvelope, envelopeDigest, conversationSafetyCode, encode64, decode64 } from '../lib/chat-crypto.ts';

const [alice, bob, eve] = await Promise.all(['account-a', 'account-b', 'account-e'].map(createChatIdentity));
const message = await encryptMessage(alice.keys, 'account-b', bob.keys.identity, 'friendship-ab', 'Hello <script> & Grüße 🌟');
test('registration is actor-bound and backup tampering invalidates the proof', async () => {
  assert.equal(await verifyRegistration('account-a', alice.registration), true);
  assert.equal(await verifyRegistration('account-b', alice.registration), false);
  assert.equal(await verifyRegistration('account-a', {...alice.registration, backup: {...alice.registration.backup, iv: 'A'.repeat(16)}}), false);
});
test('both participants decrypt; an unrelated account cannot', async () => {
  assert.equal(await decryptMessage(bob.keys, 'account-a', alice.keys.identity, 'friendship-ab', message), 'Hello <script> & Grüße 🌟');
  assert.equal(await decryptMessage(alice.keys, 'account-b', bob.keys.identity, 'friendship-ab', message), 'Hello <script> & Grüße 🌟');
  await assert.rejects(decryptMessage(eve.keys, 'account-a', alice.keys.identity, 'friendship-ab', message));
  assert.equal(JSON.stringify(message).includes('Hello'), false);
});
test('signed envelope binds every field and rejects cross-conversation copies', async () => {
  assert.equal(await verifyEnvelope(message, alice.keys.identity), true);
  for (const field of ['id','friendshipId','senderId','recipientId','senderFingerprint','recipientFingerprint','iv','ciphertext','senderKey','recipientKey','signature']) {
    const altered = {...message, [field]: message[field] + 'a'};
    assert.equal(await verifyEnvelope(altered, alice.keys.identity), false, field);
  }
  assert.equal(await verifyEnvelope({...message, version: 2}, alice.keys.identity), false);
  await assert.rejects(decryptMessage(bob.keys, 'account-a', alice.keys.identity, 'different', message));
});
test('restore validates account, backup and both key pairs; keys cannot be exported', async () => {
  const restored = await restoreChatIdentity('account-a', alice.registration, alice.recoveryCode);
  assert.equal(restored.encryptionKey.extractable, false);
  assert.equal(restored.signingKey.extractable, false);
  await assert.rejects(crypto.subtle.exportKey('pkcs8', restored.encryptionKey));
  assert.equal(await decryptMessage(restored, 'account-b', bob.keys.identity, 'friendship-ab', message), 'Hello <script> & Grüße 🌟');
  await assert.rejects(restoreChatIdentity('account-b', alice.registration, alice.recoveryCode));
  await assert.rejects(restoreChatIdentity('account-a', alice.registration, bob.recoveryCode));
});
test('message encryption is randomized, recovery codes are independent, safety codes symmetric', async () => {
  const second = await encryptMessage(alice.keys, 'account-b', bob.keys.identity, 'friendship-ab', 'Hello <script> & Grüße 🌟');
  assert.notEqual(second.id, message.id); assert.notEqual(second.iv, message.iv); assert.notEqual(second.ciphertext, message.ciphertext);
  assert.notEqual(await envelopeDigest(second), await envelopeDigest(message));
  assert.equal(await envelopeDigest({...message}), await envelopeDigest(message));
  assert.notEqual(alice.recoveryCode, bob.recoveryCode);
  assert.equal(await conversationSafetyCode(alice.keys.identity, bob.keys.identity), await conversationSafetyCode(bob.keys.identity, alice.keys.identity));
});
test('plaintext length and empty sends are bounded before encryption', async () => {
  await assert.rejects(encryptMessage(alice.keys, 'account-b', bob.keys.identity, 'friendship-ab', ' '));
  await assert.rejects(encryptMessage(alice.keys, 'account-b', bob.keys.identity, 'friendship-ab', 'x'.repeat(2001)));
  await assert.rejects(encryptMessage(alice.keys, 'account-a', alice.keys.identity, 'friendship-ab', 'x'));
});

test('a validly signed backup with a mismatched private key cannot restore', async () => {
  const encode = value => new TextEncoder().encode(JSON.stringify(value));
  const recovery = await crypto.subtle.importKey('raw', decode64(alice.recoveryCode), 'AES-GCM', false, ['encrypt', 'decrypt']);
  const aad = encode(['starfriends-chat', 1, 'private-backup', 'account-a', alice.keys.identity.fingerprint]);
  const data = JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: decode64(alice.registration.backup.iv), additionalData: aad, tagLength: 128 }, recovery, decode64(alice.registration.backup.ciphertext))));
  const unrelated = await crypto.subtle.generateKey({name:'ECDSA',namedCurve:'P-256'}, true, ['sign','verify']);
  data.signingPrivate = encode64(await crypto.subtle.exportKey('pkcs8', unrelated.privateKey));
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const bad = structuredClone(alice.registration);
  bad.backup = { iv: encode64(iv), ciphertext: encode64(await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:aad,tagLength:128}, recovery, encode(data))) };
  const i = bad.identity;
  const registrationBytes = encode(['starfriends-chat',1,'registration','account-a',i.encryptionKey,i.signingKey,i.fingerprint,bad.backup.iv,bad.backup.ciphertext]);
  bad.proof = encode64(await crypto.subtle.sign({name:'ECDSA',hash:'SHA-256'},alice.keys.signingKey,registrationBytes));
  assert.equal(await verifyRegistration('account-a',bad),true, 'outer registration remains valid');
  await assert.rejects(restoreChatIdentity('account-a',bad,alice.recoveryCode), /invalid_recovery/);
});

test('a valid sender signature does not permit a downgraded AES message key', async () => {
  const downgraded = {...message};
  const shortKey = crypto.getRandomValues(new Uint8Array(16));
  for (const [field, identity] of [['senderKey',alice.keys.identity],['recipientKey',bob.keys.identity]]) {
    const key = await crypto.subtle.importKey('spki',decode64(identity.encryptionKey),{name:'RSA-OAEP',hash:'SHA-256'},false,['encrypt']);
    downgraded[field] = encode64(await crypto.subtle.encrypt('RSA-OAEP',key,shortKey));
  }
  const e = downgraded;
  const signed = new TextEncoder().encode(JSON.stringify(['starfriends-chat',1,'message-envelope',e.id,e.friendshipId,e.senderId,e.recipientId,e.senderFingerprint,e.recipientFingerprint,e.iv,e.ciphertext,e.senderKey,e.recipientKey]));
  downgraded.signature = encode64(await crypto.subtle.sign({name:'ECDSA',hash:'SHA-256'},alice.keys.signingKey,signed));
  assert.equal(await verifyEnvelope(downgraded,alice.keys.identity),true);
  await assert.rejects(decryptMessage(bob.keys,'account-a',alice.keys.identity,'friendship-ab',downgraded), /invalid_message/);
});
