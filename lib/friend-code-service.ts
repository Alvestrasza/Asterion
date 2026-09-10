import { createHash } from "node:crypto";
import { Prisma, type PrismaClient } from "@prisma/client";
import { prisma } from "@/lib/db";
import { assertAccess } from "@/lib/access-service";
import { createKeycloakStorageClient, keycloakStorageConfig, KeycloakStorageError } from "./keycloak-storage.ts";
import { createStorageJournal } from "./keycloak-storage-journal.ts";

/** Keycloak is authoritative. The application stores only an exact-match lookup hash. */
export async function ensureFriendCode(actorId: string, db: PrismaClient = prisma): Promise<string> {
  const config = keycloakStorageConfig();
  const binding = await db.$transaction(async tx => {
    const access = await assertAccess(tx, actorId);
    if (access.issuer !== config.issuer) throw new KeycloakStorageError("storage_identity_invalid");
    return { issuer: access.issuer, subject: access.subject };
  });
  const code = await createKeycloakStorageClient(config, fetch, createStorageJournal(actorId, binding, db)).ensureFriendCode(binding.subject);
  const hash = createHash("sha256").update(code, "utf8").digest("hex");
  for (let attempt = 0; ; attempt++) {
    try {
      await db.$transaction(async tx => {
        const access = await assertAccess(tx, actorId);
        if (access.issuer !== binding.issuer || access.subject !== binding.subject) throw new KeycloakStorageError("storage_identity_invalid");
        const previous = await tx.socialProfile.findUnique({ where: { userId: actorId } });
        if (previous?.friendCodeHash && previous.friendCodeHash !== hash) throw new KeycloakStorageError("storage_conflict");
        await tx.socialProfile.upsert({ where: { userId: actorId }, create: { userId: actorId, friendCodeHash: hash }, update: { friendCodeHash: hash } });
      }, { isolationLevel: Prisma.TransactionIsolationLevel.Serializable });
      return code;
    } catch (error) {
      if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2034" && attempt < 3) continue;
      // A unique hash collision/misbound account is not resolved by replacing anyone's code.
      throw error;
    }
  }
}
