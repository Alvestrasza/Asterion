import type { PrismaClient } from "@prisma/client";
import { prisma } from "@/lib/db";
import { assertAccess } from "@/lib/access-service";
import { chatCommand, type ChatCommand } from "./chat-service.ts";
import { restoreChatIdentity, verifyRegistration, type ChatRegistration } from "./chat-crypto.ts";
import { createKeycloakStorageClient, keycloakStorageConfig, keycloakStorageConfigured, KeycloakStorageError, type RecoveryRecord } from "./keycloak-storage.ts";
import { createStorageJournal } from "./keycloak-storage-journal.ts";

export type RecoveringChatCommand = Exclude<ChatCommand, { action: "register" | "recovery-check" }>
  | { action: "register"; registration: ChatRegistration; recoveryCode: string }
  | { action: "recover" };

function sameRegistration(a: ChatRegistration, b: ChatRegistration) {
  return a.identity.version === b.identity.version && a.identity.fingerprint === b.identity.fingerprint &&
    a.identity.encryptionKey === b.identity.encryptionKey && a.identity.signingKey === b.identity.signingKey &&
    a.backup.iv === b.backup.iv && a.backup.ciphertext === b.backup.ciphertext;
}

/** Phase 1: account-authorized escrow, NOT protection from a privileged operator.
 * The recoverable record is committed in Keycloak first. Its complete encrypted
 * registration allows an exact retry after a lost reply or an application DB failure.
 * Neither system may silently replace an existing identity. No diary keys enter here.
 */
export async function recoveringChatCommand(actorId: string, command: RecoveringChatCommand, db: PrismaClient = prisma) {
  if (!["identity", "register", "recover"].includes(command.action)) return chatCommand(actorId, command as ChatCommand, db);
  const initial = await chatCommand(actorId, { action: command.action === "identity" ? "identity" : "recovery-check" }, db);
  if ("error" in initial) return initial;
  if (!("identity" in initial)) throw new KeycloakStorageError("storage_response_invalid");
  if (initial.identity && !("backup" in initial.identity)) throw new KeycloakStorageError("storage_response_invalid");
  const original = initial.identity;
  if (!keycloakStorageConfigured()) {
    if (command.action === "identity") return { identity: original, recoveryMode: "unavailable" as const };
    throw new KeycloakStorageError("storage_configuration_invalid");
  }
  const config = keycloakStorageConfig();
  const binding = await db.$transaction(async tx => {
    const access = await assertAccess(tx, actorId);
    if (access.issuer !== config.issuer) throw new KeycloakStorageError("storage_identity_invalid");
    return { issuer: access.issuer, subject: access.subject };
  });
  const storage = createKeycloakStorageClient(config, fetch, createStorageJournal(actorId, binding, db));
  let remote: RecoveryRecord | null;
  if (command.action === "register") {
    if (!await verifyRegistration(actorId, command.registration) ||
      (original && !sameRegistration(original, command.registration))) return { error: "invalid_identity" };
    // Reject unrecoverable/wrong-key uploads before making immutable escrow durable.
    // In phase 1 the service is trusted with this key; never log the decoded material.
    try { await restoreChatIdentity(actorId, command.registration, command.recoveryCode); }
    catch { return { error: "invalid_recovery" }; }
    try {
      remote = await storage.createRecovery(binding.subject, { actorId, fingerprint: command.registration.identity.fingerprint,
        recoveryCode: command.recoveryCode, registration: command.registration });
    } catch (error) {
      if (!(error instanceof KeycloakStorageError) || error.code !== "storage_conflict") throw error;
      // Two empty browsers can race. Use the first committed identity, never overwrite it.
      remote = await storage.readRecovery(binding.subject);
      if (!remote) throw new KeycloakStorageError("storage_conflict");
    }
  } else remote = await storage.readRecovery(binding.subject);

  if (!remote) {
    if (command.action === "recover") return { error: "recovery_unavailable" };
    // Legacy manual-code records are not silently escrowed without that code.
    return { identity: original, recoveryMode: original ? "legacy" as const : "keycloak" as const };
  }
  if (remote.subject !== binding.subject || remote.actorId !== actorId || remote.fingerprint !== remote.registration.identity.fingerprint ||
    !await verifyRegistration(actorId, remote.registration) || (original && !sameRegistration(original, remote.registration)))
    throw new KeycloakStorageError("storage_identity_invalid");

  if (command.action !== "identity") {
    try { await restoreChatIdentity(actorId, remote.registration, remote.recoveryCode); }
    catch { throw new KeycloakStorageError("storage_response_invalid"); }
  }
  if (!original) {
    const attached = await chatCommand(actorId, { action: "register", registration: remote.registration }, db, binding);
    if ("error" in attached) return attached;
  }
  // Fresh authorization after the external call; never release recovery material
  // to a revoked or differently bound account using an earlier authorization snapshot.
  await db.$transaction(async tx => {
    const access = await assertAccess(tx, actorId);
    if (access.issuer !== binding.issuer || access.subject !== binding.subject) throw new KeycloakStorageError("storage_identity_invalid");
    const current = await tx.chatIdentity.findUnique({ where: { userId: actorId } });
    if (!current || !sameRegistration(current.registration as unknown as ChatRegistration, remote.registration))
      throw new KeycloakStorageError("storage_conflict");
  });
  if (command.action === "identity") return { identity: remote.registration, recoveryMode: "keycloak" as const };
  return { identity: remote.registration, recoveryCode: remote.recoveryCode };
}
