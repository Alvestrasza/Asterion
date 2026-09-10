import type { Prisma, PrismaClient } from "@prisma/client";
import { prisma } from "@/lib/db";
import { assertAccess } from "@/lib/access-service";
import { KeycloakStorageError } from "./keycloak-storage.ts";

export type StorageAttribute = "starfriends_friend_code" | "starfriends_chat_recovery";
export type StorageWrite = { digest: string; confirmed: boolean };
export type StorageJournal = {
  get(subject: string, attribute: StorageAttribute): Promise<StorageWrite | null>;
  reserve(subject: string, attribute: StorageAttribute, digest: string, friendCodeHash?: string): Promise<{ owned: boolean; write: StorageWrite }>;
  confirm(subject: string, attribute: StorageAttribute, digest: string): Promise<void>;
};

const FRIEND_CODE: StorageAttribute = "starfriends_friend_code";
const RECOVERY: StorageAttribute = "starfriends_chat_recovery";
const validHash = (value: unknown): value is string => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);

/** This is an at-most-once write journal, not a retry lease or a secret store.
 * Pending reservations never expire. Only their sole creator may attempt the remote PUT.
 * Provider I/O happens outside these transactions, in the storage client.
 */
export function createStorageJournal(actorId: string, binding: { issuer: string; subject: string }, db: PrismaClient = prisma): StorageJournal {
  // Snapshot the binding so mutating the caller's object cannot silently change this journal.
  const { issuer, subject: boundSubject } = binding;
  const where = (attribute: StorageAttribute) => ({ issuer_subject_attribute: { issuer, subject: boundSubject, attribute } });
  async function authorize(tx: Prisma.TransactionClient, subject: string, attribute: StorageAttribute) {
    const access = await assertAccess(tx, actorId);
    if (subject !== boundSubject || access.issuer !== issuer || access.subject !== boundSubject)
      throw new KeycloakStorageError("storage_identity_invalid");
    if (attribute !== FRIEND_CODE && attribute !== RECOVERY) throw new KeycloakStorageError("storage_response_invalid");
  }
  function project(row: { userId: string; digest: string; confirmed: boolean }): StorageWrite {
    if (row.userId !== actorId) throw new KeycloakStorageError("storage_identity_invalid");
    return { digest: row.digest, confirmed: row.confirmed };
  }
  return {
    get(subject, attribute) {
      return db.$transaction(async tx => {
        await authorize(tx, subject, attribute);
        const row = await tx.identityStorageWrite.findUnique({ where: where(attribute) });
        return row ? project(row) : null;
      });
    },
    reserve(subject, attribute, digest, friendCodeHash) {
      return db.$transaction(async tx => {
        await authorize(tx, subject, attribute);
        if (!validHash(digest) || (attribute === FRIEND_CODE ? !validHash(friendCodeHash) : friendCodeHash !== undefined))
          throw new KeycloakStorageError("storage_response_invalid");
        if (attribute === RECOVERY) {
          const friendWrite = await tx.identityStorageWrite.findUnique({ where: where(FRIEND_CODE) });
          if (!friendWrite || !project(friendWrite).confirmed) throw new KeycloakStorageError("storage_conflict");
        }
        // PostgreSQL ON CONFLICT DO NOTHING elects the sole owner without resetting old rows.
        const created = await tx.identityStorageWrite.createMany({ data: [{
          userId: actorId, issuer, subject: boundSubject, attribute, digest,
          friendCodeHash: attribute === FRIEND_CODE ? friendCodeHash : null
        }], skipDuplicates: true });
        const row = await tx.identityStorageWrite.findUnique({ where: where(attribute) });
        if (!row) throw new KeycloakStorageError("storage_conflict"); // A code hash belongs to another account.
        return { owned: created.count === 1, write: project(row) };
      });
    },
    confirm(subject, attribute, digest) {
      return db.$transaction(async tx => {
        await authorize(tx, subject, attribute);
        if (!validHash(digest)) throw new KeycloakStorageError("storage_response_invalid");
        const row = await tx.identityStorageWrite.findUnique({ where: where(attribute) });
        if (!row) throw new KeycloakStorageError("storage_conflict");
        if (project(row).digest !== digest) throw new KeycloakStorageError("storage_conflict");
        const changed = await tx.identityStorageWrite.updateMany({
          where: { userId: actorId, issuer, subject: boundSubject, attribute, digest }, data: { confirmed: true }
        });
        if (changed.count !== 1) throw new KeycloakStorageError("storage_conflict");
      });
    }
  };
}
