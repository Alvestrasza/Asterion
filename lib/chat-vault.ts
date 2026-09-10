"use client";

import type { ChatKeys } from "./chat-crypto";

// Only non-extractable keys and public peer fingerprints are persisted. Never message text.
const DATABASE = "starfriends-chat-v1";
function openVault(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE, 1);
    request.onupgradeneeded = () => { request.result.createObjectStore("keys"); request.result.createObjectStore("peers"); };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(new Error("vault_unavailable"));
    request.onblocked = () => reject(new Error("vault_unavailable"));
  });
}
async function vault<T>(store: "keys" | "peers", id: string, value?: T): Promise<T | undefined> {
  const db = await openVault();
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(store, value === undefined ? "readonly" : "readwrite");
      const request = value === undefined ? tx.objectStore(store).get(id) : tx.objectStore(store).put(value, id);
      tx.oncomplete = () => resolve(value === undefined ? request.result : value);
      tx.onerror = tx.onabort = () => reject(new Error("vault_unavailable"));
    });
  } finally { db.close(); }
}
export async function loadChatKeys(actorId: string, fingerprint: string): Promise<ChatKeys | undefined> {
  const keys = await vault<ChatKeys>("keys", actorId);
  if (!keys) return undefined;
  if (keys.actorId !== actorId || keys.identity.fingerprint !== fingerprint || keys.encryptionKey.extractable || keys.signingKey.extractable) throw new Error("key_mismatch");
  return keys;
}
export async function saveChatKeys(keys: ChatKeys): Promise<void> {
  if (keys.encryptionKey.extractable || keys.signingKey.extractable) throw new Error("extractable_private_key");
  await vault("keys", keys.actorId, keys);
}
export type PeerPin = { fingerprint: string; verified: boolean };
const peerKey = (actorId: string, peerId: string) => JSON.stringify([actorId, peerId]);
export async function getPeerPin(actorId: string, peerId: string) { return vault<PeerPin>("peers", peerKey(actorId, peerId)); }
export async function savePeerPin(actorId: string, peerId: string, pin: PeerPin) {
  const db = await openVault();
  try {
    await new Promise<void>((resolve, reject) => {
      // Read and compare in the same write transaction: two tabs cannot replace a first-use pin.
      const tx = db.transaction("peers", "readwrite");
      const store = tx.objectStore("peers");
      const request = store.get(peerKey(actorId, peerId));
      let conflict = false;
      request.onsuccess = () => {
        const existing = request.result as PeerPin | undefined;
        if (existing && existing.fingerprint !== pin.fingerprint) { conflict = true; tx.abort(); return; }
        store.put({ ...pin, verified: pin.verified || existing?.verified === true }, peerKey(actorId, peerId));
      };
      tx.oncomplete = () => resolve();
      tx.onerror = tx.onabort = () => reject(new Error(conflict ? "peer_key_changed" : "vault_unavailable"));
    });
  } finally { db.close(); }
}
