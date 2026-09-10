import { Prisma, type ChatMessage, type PrismaClient } from "@prisma/client";
import { prisma } from "@/lib/db";
import { assertAccess, accessIsEffective } from "@/lib/access-service";
import { displayUsername, maySeePresence } from "./social-policy.ts";
import { envelopeDigest, verifyEnvelope, verifyRegistration, type ChatEnvelope, type ChatRegistration } from "./chat-crypto.ts";

export type ChatCommand =
  | { action: "identity" }
  | { action: "recovery-check" }
  | { action: "inbox" }
  | { action: "register"; registration: ChatRegistration }
  | { action: "open"; friendshipId: string; before?: string }
  | { action: "send"; envelope: ChatEnvelope }
  | { action: "read"; friendshipId: string; messageId: string };

const failure = (error: string) => ({ error });
const registration = (value: Prisma.JsonValue) => value as unknown as ChatRegistration;
const json = (value: ChatRegistration | ChatEnvelope) => value as unknown as Prisma.InputJsonValue;
function message(row: ChatMessage) {
  return { ...(row.envelope as unknown as ChatEnvelope), sequence: row.sequence.toString(), createdAt: row.createdAt.toISOString() };
}

/** All nodes share these budgets. Expected denials commit their request charge. */
async function consumeBudget(tx: Prisma.TransactionClient, actorId: string, action: ChatCommand["action"], now: Date) {
  const old = await tx.chatBudget.upsert({ where: { userId: actorId }, create: { userId: actorId }, update: {} });
  const resetMinute = now.getTime() - old.windowStartedAt.getTime() >= 60_000;
  const resetDay = now.toISOString().slice(0, 10) !== old.dayStartedAt.toISOString().slice(0, 10);
  const windowCount = resetMinute ? 0 : old.windowCount;
  const sendCount = resetMinute ? 0 : old.sendCount;
  const registrationCount = resetMinute ? 0 : old.registrationCount;
  const daySendCount = resetDay ? 0 : old.daySendCount;
  const recoveryAttempt = action === "register" || action === "recovery-check";
  if (windowCount >= 180 || (action === "send" && (sendCount >= 20 || daySendCount >= 1000)) ||
    (recoveryAttempt && registrationCount >= 5)) return false;
  await tx.chatBudget.update({ where: { userId: actorId }, data: {
    windowStartedAt: resetMinute ? now : old.windowStartedAt,
    windowCount: windowCount + 1, sendCount: sendCount + Number(action === "send"),
    registrationCount: registrationCount + Number(recoveryAttempt),
    dayStartedAt: resetDay ? now : old.dayStartedAt, daySendCount: daySendCount + Number(action === "send")
  } });
  return true;
}

/** Ciphertext-only persistence. Phase 1 escrow is handled separately, never stored here. */
export async function chatCommand(actorId: string, command: ChatCommand, db: PrismaClient = prisma,
  expectedBinding?: { issuer: string; subject: string }) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await db.$transaction(async (tx) => {
        const friendshipId = command.action === "send" ? command.envelope.friendshipId :
          command.action === "open" || command.action === "read" ? command.friendshipId : null;
        // Acquire participant access locks in a stable order before the social lock.
        // The pair is read again after locks; this first read conveys no authorization.
        const initialPair = friendshipId ? await tx.friendship.findUnique({ where: { id: friendshipId } }) : null;
        const participantIds = initialPair && [initialPair.leftId, initialPair.rightId].includes(actorId)
          ? [initialPair.leftId, initialPair.rightId].sort() : [actorId];
        for (const id of participantIds) {
          const access = await assertAccess(tx, id);
          if (id === actorId && expectedBinding && (access.issuer !== expectedBinding.issuer || access.subject !== expectedBinding.subject))
            return failure("invalid_identity");
        }
        await tx.$executeRaw`SELECT pg_advisory_xact_lock(1093863253::integer, 0)`;
        if (!await consumeBudget(tx, actorId, command.action, new Date())) return failure("rate_limited");

        if (command.action === "identity" || command.action === "recovery-check") {
          const own = await tx.chatIdentity.findUnique({ where: { userId: actorId } });
          return { identity: own ? registration(own.registration) : null };
        }
        if (command.action === "register") {
          if (!await verifyRegistration(actorId, command.registration)) return failure("invalid_identity");
          const own = await tx.chatIdentity.findUnique({ where: { userId: actorId } });
          if (own) {
            const previous = registration(own.registration);
            // Keep the original encrypted backup even when a client retries registration.
            if (previous.identity.version !== command.registration.identity.version ||
              previous.identity.fingerprint !== command.registration.identity.fingerprint ||
              previous.identity.encryptionKey !== command.registration.identity.encryptionKey ||
              previous.identity.signingKey !== command.registration.identity.signingKey ||
              previous.backup.iv !== command.registration.backup.iv || previous.backup.ciphertext !== command.registration.backup.ciphertext) return failure("identity_exists");
            return { identity: previous };
          }
          const reused = await tx.chatIdentity.findUnique({ where: { fingerprint: command.registration.identity.fingerprint } });
          if (reused) return failure("invalid_identity");
          await tx.chatIdentity.create({ data: { userId: actorId, fingerprint: command.registration.identity.fingerprint, registration: json(command.registration) } });
          return { identity: command.registration };
        }
        if (command.action === "inbox") {
          const pairs = await tx.friendship.findMany({ where: { status: "accepted", leftBlocked: false, rightBlocked: false,
            OR: [{ leftId: actorId }, { rightId: actorId }] },
            include: { left: { select: { access: true } }, right: { select: { access: true } } }, take: 100 });
          const unread: { friendshipId: string; count: number }[] = [];
          for (const pair of pairs) {
            const other = pair.leftId === actorId ? pair.right : pair.left;
            if (!accessIsEffective(other.access)) continue;
            const cursor = await tx.chatRead.findUnique({ where: { userId_friendshipId: { userId: actorId, friendshipId: pair.id } } });
            const count = await tx.chatMessage.count({ where: { friendshipId: pair.id, recipientId: actorId, sequence: { gt: cursor?.sequence ?? 0n } } });
            if (count) unread.push({ friendshipId: pair.id, count });
          }
          return { unread };
        }
        const pair = friendshipId ? await tx.friendship.findUnique({ where: { id: friendshipId } }) : null;
        if (!pair || !maySeePresence(pair, actorId)) return failure("conversation_unavailable");
        const peerId = pair.leftId === actorId ? pair.rightId : pair.leftId;
        const own = await tx.chatIdentity.findUnique({ where: { userId: actorId } });
        const peer = await tx.chatIdentity.findUnique({ where: { userId: peerId } });

        if (command.action === "open") {
          const profile = await tx.socialProfile.findUnique({ where: { userId: peerId } });
          const rows = await tx.chatMessage.findMany({ where: { friendshipId: pair.id,
            ...(command.before ? { sequence: { lt: BigInt(command.before) } } : {}) }, orderBy: { sequence: "desc" }, take: 51 });
          return { peerId, peerName: displayUsername(profile) ?? "—", identity: peer ? registration(peer.registration).identity : null,
            messages: rows.slice(0, 50).reverse().map(message), hasMore: rows.length > 50 };
        }
        if (command.action === "read") {
          const row = await tx.chatMessage.findUnique({ where: { id: command.messageId } });
          if (!row || row.friendshipId !== pair.id || row.recipientId !== actorId) return failure("message_unavailable");
          const where = { userId_friendshipId: { userId: actorId, friendshipId: pair.id } };
          const old = await tx.chatRead.findUnique({ where });
          if (!old || old.sequence < row.sequence) await tx.chatRead.upsert({ where,
            create: { userId: actorId, friendshipId: pair.id, sequence: row.sequence }, update: { sequence: row.sequence } });
          return { ok: true };
        }
        if (!own || !peer) return failure("identity_required");
        const envelope = command.envelope;
        if (envelope.senderId !== actorId || envelope.recipientId !== peerId ||
          envelope.senderFingerprint !== own.fingerprint || envelope.recipientFingerprint !== peer.fingerprint) return failure("invalid_message");
        if (!await verifyEnvelope(envelope, registration(own.registration).identity)) return failure("invalid_message");
        const digest = await envelopeDigest(envelope);
        const existing = await tx.chatMessage.findUnique({ where: { id: envelope.id } });
        if (existing) return existing.senderId === actorId && existing.friendshipId === pair.id && existing.digest === digest
          ? { message: message(existing) } : failure("message_conflict");
        const row = await tx.chatMessage.create({ data: { id: envelope.id, friendshipId: pair.id, senderId: actorId,
          recipientId: peerId, envelope: json(envelope), digest } });
        return { message: message(row) };
      }, { isolationLevel: Prisma.TransactionIsolationLevel.Serializable, maxWait: 5000, timeout: 10000 });
    } catch (error) {
      if (error instanceof Prisma.PrismaClientKnownRequestError && ["P2034", "P2002"].includes(error.code) && attempt < 3) continue;
      throw error;
    }
  }
}
