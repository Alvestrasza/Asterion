/** Versioned browser-to-browser envelope. Phase 1 recovery secrets use separate Keycloak escrow, never message persistence. */
export type ChatPublicIdentity = { version: 1; encryptionKey: string; signingKey: string; fingerprint: string };
export type ChatRegistration = { identity: ChatPublicIdentity; backup: { iv: string; ciphertext: string }; proof: string };
export type ChatEnvelope = {
  version: 1; id: string; friendshipId: string; senderId: string; recipientId: string;
  senderFingerprint: string; recipientFingerprint: string; iv: string; ciphertext: string;
  senderKey: string; recipientKey: string; signature: string;
};
export type ChatKeys = { actorId: string; identity: ChatPublicIdentity; encryptionKey: CryptoKey; signingKey: CryptoKey };
const utf8 = new TextEncoder();
const decoder = new TextDecoder("utf-8", { fatal: true });
export function encode64(value: ArrayBuffer | Uint8Array): string {
  return btoa(String.fromCharCode(...new Uint8Array(value))).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}
export function decode64(value: string): Uint8Array<ArrayBuffer> {
  if (!/^[A-Za-z0-9_-]+$/.test(value) || value.length > 24000) throw new Error("invalid_encoding");
  const bytes = Uint8Array.from(atob(value.replaceAll("-", "+").replaceAll("_", "/")), (c) => c.charCodeAt(0));
  if (encode64(bytes) !== value) throw new Error("invalid_encoding");
  return bytes;
}
const canonical = (domain: string, values: unknown[]) => utf8.encode(JSON.stringify(["starfriends-chat", 1, domain, ...values]));
async function digest(bytes: Uint8Array<ArrayBuffer>) { return encode64(await crypto.subtle.digest("SHA-256", bytes)); }
export async function identityFingerprint(encryptionKey: string, signingKey: string) {
  return digest(canonical("identity", [encryptionKey, signingKey]));
}
async function importPublic(identity: ChatPublicIdentity) {
  if (identity.version !== 1 || identity.fingerprint !== await identityFingerprint(identity.encryptionKey, identity.signingKey)) throw new Error("invalid_identity");
  const encryptionKey = await crypto.subtle.importKey("spki", decode64(identity.encryptionKey), { name: "RSA-OAEP", hash: "SHA-256" }, false, ["encrypt"]);
  const signingKey = await crypto.subtle.importKey("spki", decode64(identity.signingKey), { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
  const rsa = encryptionKey.algorithm as RsaHashedKeyAlgorithm;
  if (rsa.modulusLength !== 3072 || encode64(rsa.publicExponent) !== "AQAB" || rsa.hash.name !== "SHA-256") throw new Error("invalid_identity");
  if ((signingKey.algorithm as EcKeyAlgorithm).namedCurve !== "P-256") throw new Error("invalid_identity");
  return { encryptionKey, signingKey };
}
const registrationBytes = (actorId: string, r: ChatRegistration) => canonical("registration", [actorId, r.identity.encryptionKey, r.identity.signingKey, r.identity.fingerprint, r.backup.iv, r.backup.ciphertext]);
const contextBytes = (e: Omit<ChatEnvelope, "signature">) => canonical("message-context", [e.id, e.friendshipId, e.senderId, e.recipientId, e.senderFingerprint, e.recipientFingerprint]);
const envelopeBytes = (e: Omit<ChatEnvelope, "signature">) => canonical("message-envelope", [e.id, e.friendshipId, e.senderId, e.recipientId, e.senderFingerprint, e.recipientFingerprint, e.iv, e.ciphertext, e.senderKey, e.recipientKey]);
const backupContext = (actorId: string, fingerprint: string) => canonical("private-backup", [actorId, fingerprint]);
async function sign(key: CryptoKey, data: Uint8Array<ArrayBuffer>) { return encode64(await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, key, data)); }
export async function verifyRegistration(actorId: string, r: ChatRegistration): Promise<boolean> {
  try {
    if (!actorId || decode64(r.backup.iv).length !== 12 || decode64(r.backup.ciphertext).length > 12000 || decode64(r.backup.ciphertext).length < 32 || decode64(r.proof).length !== 64) return false;
    const keys = await importPublic(r.identity);
    return await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, keys.signingKey, decode64(r.proof), registrationBytes(actorId, r));
  } catch { return false; }
}
export async function verifyEnvelope(e: ChatEnvelope, sender: ChatPublicIdentity): Promise<boolean> {
  try {
    if (e.version !== 1 || e.senderFingerprint !== sender.fingerprint || e.senderId === e.recipientId ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(e.id) ||
      decode64(e.iv).length !== 12 || decode64(e.senderKey).length !== 384 || decode64(e.recipientKey).length !== 384 ||
      decode64(e.signature).length !== 64 || decode64(e.ciphertext).length < 17 || decode64(e.ciphertext).length > 8016) return false;
    const keys = await importPublic(sender);
    return await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, keys.signingKey, decode64(e.signature), envelopeBytes(e));
  } catch { return false; }
}
export async function envelopeDigest(e: ChatEnvelope) { return digest(canonical("idempotency", [encode64(envelopeBytes(e)), e.signature])); }
export async function createChatIdentity(actorId: string): Promise<{ keys: ChatKeys; registration: ChatRegistration; recoveryCode: string }> {
  const encryption = await crypto.subtle.generateKey({ name: "RSA-OAEP", modulusLength: 3072, publicExponent: new Uint8Array([1, 0, 1]), hash: "SHA-256" }, true, ["encrypt", "decrypt"]);
  const signing = await crypto.subtle.generateKey({ name: "ECDSA", namedCurve: "P-256" }, true, ["sign", "verify"]);
  const encryptionKey = encode64(await crypto.subtle.exportKey("spki", encryption.publicKey));
  const signingKey = encode64(await crypto.subtle.exportKey("spki", signing.publicKey));
  const identity: ChatPublicIdentity = { version: 1, encryptionKey, signingKey, fingerprint: await identityFingerprint(encryptionKey, signingKey) };
  const encryptionPrivate = await crypto.subtle.exportKey("pkcs8", encryption.privateKey);
  const signingPrivate = await crypto.subtle.exportKey("pkcs8", signing.privateKey);
  const recoveryBytes = crypto.getRandomValues(new Uint8Array(32));
  const recoveryCode = encode64(recoveryBytes);
  const recoveryKey = await crypto.subtle.importKey("raw", recoveryBytes, "AES-GCM", false, ["encrypt"]);
  recoveryBytes.fill(0);
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const plaintext = utf8.encode(JSON.stringify({ version: 1, actorId, fingerprint: identity.fingerprint, encryptionPrivate: encode64(encryptionPrivate), signingPrivate: encode64(signingPrivate) }));
  const ciphertext = await crypto.subtle.encrypt({ name: "AES-GCM", iv, additionalData: backupContext(actorId, identity.fingerprint), tagLength: 128 }, recoveryKey, plaintext);
  plaintext.fill(0);
  const keys: ChatKeys = { actorId, identity,
    encryptionKey: await crypto.subtle.importKey("pkcs8", encryptionPrivate, { name: "RSA-OAEP", hash: "SHA-256" }, false, ["decrypt"]),
    signingKey: await crypto.subtle.importKey("pkcs8", signingPrivate, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]) };
  new Uint8Array(encryptionPrivate).fill(0); new Uint8Array(signingPrivate).fill(0);
  const registration: ChatRegistration = { identity, backup: { iv: encode64(iv), ciphertext: encode64(ciphertext) }, proof: "" };
  registration.proof = await sign(keys.signingKey, registrationBytes(actorId, registration));
  return { keys, registration, recoveryCode };
}
export async function restoreChatIdentity(actorId: string, registration: ChatRegistration, recoveryCode: string): Promise<ChatKeys> {
  if (!await verifyRegistration(actorId, registration)) throw new Error("invalid_identity");
  const raw = decode64(recoveryCode.trim());
  if (raw.length !== 32) throw new Error("invalid_recovery");
  const recoveryKey = await crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["decrypt"]); raw.fill(0);
  const bytes = new Uint8Array(await crypto.subtle.decrypt({ name: "AES-GCM", iv: decode64(registration.backup.iv), additionalData: backupContext(actorId, registration.identity.fingerprint), tagLength: 128 }, recoveryKey, decode64(registration.backup.ciphertext)));
  const payload = JSON.parse(decoder.decode(bytes)); bytes.fill(0);
  if (payload.version !== 1 || payload.actorId !== actorId || payload.fingerprint !== registration.identity.fingerprint) throw new Error("invalid_recovery");
  const keys: ChatKeys = { actorId, identity: registration.identity,
    encryptionKey: await crypto.subtle.importKey("pkcs8", decode64(payload.encryptionPrivate), { name: "RSA-OAEP", hash: "SHA-256" }, false, ["decrypt"]),
    signingKey: await crypto.subtle.importKey("pkcs8", decode64(payload.signingPrivate), { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]) };
  const publicKeys = await importPublic(registration.identity);
  const challenge = crypto.getRandomValues(new Uint8Array(32));
  const decrypted = new Uint8Array(await crypto.subtle.decrypt("RSA-OAEP", keys.encryptionKey, await crypto.subtle.encrypt("RSA-OAEP", publicKeys.encryptionKey, challenge)));
  if (!challenge.every((v, i) => v === decrypted[i]) || !await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, publicKeys.signingKey, decode64(await sign(keys.signingKey, challenge)), challenge)) throw new Error("invalid_recovery");
  return keys;
}
export async function encryptMessage(keys: ChatKeys, peerId: string, peer: ChatPublicIdentity, friendshipId: string, text: string): Promise<ChatEnvelope> {
  if (!text.trim() || text.length > 2000 || peerId === keys.actorId) throw new Error("invalid_message");
  const [ownPublic, peerPublic] = await Promise.all([importPublic(keys.identity), importPublic(peer)]);
  const keyBytes = crypto.getRandomValues(new Uint8Array(32));
  const key = await crypto.subtle.importKey("raw", keyBytes, "AES-GCM", false, ["encrypt"]);
  const e: ChatEnvelope = { version: 1, id: crypto.randomUUID(), friendshipId, senderId: keys.actorId, recipientId: peerId, senderFingerprint: keys.identity.fingerprint, recipientFingerprint: peer.fingerprint, iv: encode64(crypto.getRandomValues(new Uint8Array(12))), ciphertext: "", senderKey: "", recipientKey: "", signature: "" };
  e.senderKey = encode64(await crypto.subtle.encrypt("RSA-OAEP", ownPublic.encryptionKey, keyBytes));
  e.recipientKey = encode64(await crypto.subtle.encrypt("RSA-OAEP", peerPublic.encryptionKey, keyBytes)); keyBytes.fill(0);
  e.ciphertext = encode64(await crypto.subtle.encrypt({ name: "AES-GCM", iv: decode64(e.iv), additionalData: contextBytes(e), tagLength: 128 }, key, utf8.encode(text)));
  e.signature = await sign(keys.signingKey, envelopeBytes(e));
  return e;
}
export async function decryptMessage(keys: ChatKeys, peerId: string, peer: ChatPublicIdentity, friendshipId: string, e: ChatEnvelope): Promise<string> {
  const own = e.senderId === keys.actorId;
  if (e.friendshipId !== friendshipId || (own ? e.recipientId !== peerId : e.senderId !== peerId || e.recipientId !== keys.actorId) ||
    e.senderFingerprint !== (own ? keys.identity.fingerprint : peer.fingerprint) || e.recipientFingerprint !== (own ? peer.fingerprint : keys.identity.fingerprint) ||
    !await verifyEnvelope(e, own ? keys.identity : peer)) throw new Error("invalid_message");
  const raw = new Uint8Array(await crypto.subtle.decrypt("RSA-OAEP", keys.encryptionKey, decode64(own ? e.senderKey : e.recipientKey)));
  if (raw.length !== 32) { raw.fill(0); throw new Error("invalid_message"); }
  const key = await crypto.subtle.importKey("raw", raw, "AES-GCM", false, ["decrypt"]); raw.fill(0);
  const text = decoder.decode(await crypto.subtle.decrypt({ name: "AES-GCM", iv: decode64(e.iv), additionalData: contextBytes(e), tagLength: 128 }, key, decode64(e.ciphertext)));
  if (!text.trim() || text.length > 2000) throw new Error("invalid_message");
  return text;
}
export async function conversationSafetyCode(own: ChatPublicIdentity, peer: ChatPublicIdentity): Promise<string> {
  return digest(canonical("safety-code", [own.fingerprint, peer.fingerprint].sort()));
}
