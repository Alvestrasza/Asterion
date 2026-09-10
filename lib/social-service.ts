import { Prisma, type PrismaClient } from "@prisma/client";
import { createHash } from "node:crypto";
import { prisma } from "@/lib/db";
import { assertAccess, accessIsEffective } from "@/lib/access-service";
import { displayUsername, isOnline, mayAccept, maySeePresence, normalizeUsername, REQUEST_COOLDOWN_MS } from "./social-policy.ts";
import { normalizeFriendCode } from "./friend-code-policy.ts";
import { ensureFriendCode } from "@/lib/friend-code-service";

export type SocialCommand =
  | { action: "list" }
  | { action: "heartbeat" }
  | { action: "profile"; username: string; discoverable: boolean }
  | { action: "search"; query: string }
  | { action: "request"; friendCode: string }
  | { action: "accept" | "decline" | "remove" | "block" | "unblock"; friendshipId: string };

const userSelect = { id: true, socialProfile: true, access: true, pet: { select: { level: true } } } as const;
const failure = (error: string) => ({ error });

/** One shared database governs both nodes. Expected denials commit the abuse budget. */
export async function socialCommand(actorId: string, command: SocialCommand, db: PrismaClient = prisma) {
  const result = await runSocialCommand(actorId, command, db);
  if (command.action === "list" && "profile" in result) {
    // Consume the shared budget first. Provider I/O must not hold a database transaction open.
    const friendCode = await ensureFriendCode(actorId, db);
    return { ...result, profile: { ...result.profile, friendCode } };
  }
  return result;
}

async function runSocialCommand(actorId: string, command: SocialCommand, db: PrismaClient) {
  for (let attempt = 0; ; attempt++) {
    try {
      return await db.$transaction(async (tx) => {
        await assertAccess(tx, actorId);
        // A small bounded social graph: serialize mutations to pairs, including crossed requests.
        await tx.$executeRaw`SELECT pg_advisory_xact_lock(1093863253::integer, 0)`;
        const now = new Date();
        let profile = await tx.socialProfile.upsert({ where: { userId: actorId }, create: { userId: actorId }, update: {} });
        const newWindow = now.getTime() - profile.windowStartedAt.getTime() >= 60_000;
        if (!newWindow && profile.windowCount >= 30) return failure("rate_limited");
        profile = await tx.socialProfile.update({ where: { userId: actorId }, data: {
          windowStartedAt: newWindow ? now : profile.windowStartedAt,
          windowCount: newWindow ? 1 : profile.windowCount + 1
        } });

        if (command.action === "heartbeat") {
          await tx.socialProfile.update({ where: { userId: actorId }, data: { lastSeenAt: now } });
          return { ok: true };
        }
        if (command.action === "profile") {
          const username = normalizeUsername(command.username);
          if (!username) return failure("invalid_username");
          const owner = await tx.socialProfile.findUnique({ where: { username } });
          if (owner && owner.userId !== actorId) return failure("username_unavailable");
          await tx.socialProfile.update({ where: { userId: actorId }, data: { username, usernameDisplay: command.username.trim(), discoverable: command.discoverable } });
          return { ok: true };
        }
        if (command.action === "list") {
          const rows = await tx.friendship.findMany({
            where: { AND: [
              { OR: [{ leftId: actorId }, { rightId: actorId }] },
              { OR: [{ status: { not: "closed" } }, { leftId: actorId, leftBlocked: true }, { rightId: actorId, rightBlocked: true }] }
            ] },
            include: { left: { select: userSelect }, right: { select: userSelect } },
            orderBy: { updatedAt: "desc" }, take: 200
          });
          const friends = rows.flatMap((row) => {
            const other = row.leftId === actorId ? row.right : row.left;
            const mineBlocked = row.leftId === actorId ? row.leftBlocked : row.rightBlocked;
            // Keep only our own block controls; never reveal the other user's block choice.
            if (mineBlocked) return [{ id: row.id, username: displayUsername(other.socialProfile) ?? "—", status: "blocked", online: null, level: null }];
            if (row.leftBlocked || row.rightBlocked || row.status === "closed" || !accessIsEffective(other.access) || !other.socialProfile?.username) return [];
            const visible = maySeePresence(row, actorId);
            return [{ id: row.id, username: displayUsername(other.socialProfile)!,
              status: visible ? "accepted" : row.requestedBy === actorId ? "outgoing" : "incoming",
              online: visible ? isOnline(other.socialProfile.lastSeenAt, now) : null,
              level: visible ? other.pet?.level ?? 1 : null }];
          });
          return { profile: { username: displayUsername(profile) ?? "", discoverable: profile.discoverable }, friends };
        }
        if (!profile.username) return failure("profile_required");
        if (command.action === "search") {
          const code = normalizeFriendCode(command.query);
          if (!code) return { result: null };
          const friendCodeHash = createHash("sha256").update(code, "utf8").digest("hex");
          const users = await tx.user.findMany({ where: {
            id: { not: actorId }, socialProfile: { is: { friendCodeHash, discoverable: true, username: { not: null } } }
          }, select: userSelect, take: 2 });
          if (users.length !== 1 || !accessIsEffective(users[0].access)) return { result: null };
          const user = users[0];
          const [leftId, rightId] = [actorId, user.id].sort();
          const pair = await tx.friendship.findUnique({ where: { leftId_rightId: { leftId, rightId } } });
          if (pair?.leftBlocked || pair?.rightBlocked) return { result: null };
          return { result: { id: user.id, username: displayUsername(user.socialProfile)! } };
        }
        if (command.action === "request") {
          // Re-resolve the invitation code here; a preview or guessed user ID grants no authority.
          const code = normalizeFriendCode(command.friendCode);
          if (!code) return failure("target_unavailable");
          const friendCodeHash = createHash("sha256").update(code, "utf8").digest("hex");
          const targets = await tx.user.findMany({ where: {
            id: { not: actorId }, socialProfile: { is: { friendCodeHash, discoverable: true, username: { not: null } } }
          }, select: userSelect, take: 2 });
          const target = targets.length === 1 ? targets[0] : null;
          if (!target?.socialProfile?.discoverable || !target.socialProfile.username || !accessIsEffective(target.access)) return failure("target_unavailable");
          const [leftId, rightId] = [actorId, target.id].sort();
          const where = { leftId_rightId: { leftId, rightId } };
          const pair = await tx.friendship.findUnique({ where });
          if (pair?.leftBlocked || pair?.rightBlocked) return failure("target_unavailable");
          if (pair && pair.status !== "closed") return { ok: true }; // crossed requests never auto-accept
          if (pair && now.getTime() - pair.updatedAt.getTime() < REQUEST_COOLDOWN_MS) return failure("request_cooldown");
          const sameDay = profile.requestDay.toISOString().slice(0, 10) === now.toISOString().slice(0, 10);
          if (sameDay && profile.requestCount >= 5) return failure("rate_limited");
          for (const id of [actorId, target.id]) {
            const count = await tx.friendship.count({ where: { status: { in: ["pending", "accepted"] }, OR: [{ leftId: id }, { rightId: id }] } });
            if (count >= 100) return failure("limit_reached");
          }
          await tx.friendship.upsert({ where, create: { leftId, rightId, requestedBy: actorId }, update: { requestedBy: actorId, status: "pending" } });
          await tx.socialProfile.update({ where: { userId: actorId }, data: { requestDay: now, requestCount: sameDay ? profile.requestCount + 1 : 1 } });
          return { ok: true };
        }
        const pair = await tx.friendship.findUnique({ where: { id: command.friendshipId } });
        if (!pair || ![pair.leftId, pair.rightId].includes(actorId)) return failure("target_unavailable");
        if (command.action === "block" || command.action === "unblock") {
          await tx.friendship.update({ where: { id: pair.id }, data: {
            status: "closed", [pair.leftId === actorId ? "leftBlocked" : "rightBlocked"]: command.action === "block"
          } });
          return { ok: true };
        }
        if (pair.leftBlocked || pair.rightBlocked) return failure("target_unavailable");
        if (command.action === "accept") {
          if (!mayAccept(pair, actorId)) return failure("request_unavailable");
          const other = await tx.user.findUnique({ where: { id: pair.requestedBy }, select: { access: true } });
          if (!other || !accessIsEffective(other.access)) return failure("target_unavailable");
        } else if (command.action === "decline" && (pair.status !== "pending" || pair.requestedBy === actorId)) return failure("request_unavailable");
        await tx.friendship.update({ where: { id: pair.id }, data: { status: command.action === "accept" ? "accepted" : "closed" } });
        return { ok: true };
      }, { isolationLevel: Prisma.TransactionIsolationLevel.Serializable, maxWait: 5000, timeout: 10000 });
    } catch (error) {
      if (error instanceof Prisma.PrismaClientKnownRequestError && ["P2034", "P2002"].includes(error.code) && attempt < 3) continue;
      throw error;
    }
  }
}
