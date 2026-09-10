import { z } from "zod";
import { getCurrentActor } from "@/lib/current-actor";
import { hasSameOrigin, readBoundedJson } from "@/lib/http";
import { matchesExpectedActor } from "@/lib/actor-binding";
import { recoveringChatCommand } from "@/lib/chat-recovery-service";
import { AccessPolicyError } from "@/lib/access-policy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const opaque = (minimum: number, maximum: number) => z.string().min(minimum).max(maximum).regex(/^[A-Za-z0-9_-]+$/);
const id = z.string().min(1).max(128);
const identity = z.object({ version: z.literal(1), encryptionKey: opaque(512, 2048), signingKey: opaque(100, 256), fingerprint: opaque(43, 43) }).strict();
const registration = z.object({ identity, backup: z.object({ iv: opaque(16, 16), ciphertext: opaque(100, 16384) }).strict(), proof: opaque(86, 86) }).strict();
const envelope = z.object({ version: z.literal(1), id: z.string().uuid(), friendshipId: id, senderId: id, recipientId: id,
  senderFingerprint: opaque(43, 43), recipientFingerprint: opaque(43, 43), iv: opaque(16, 16),
  ciphertext: opaque(23, 10688), senderKey: opaque(512, 512), recipientKey: opaque(512, 512), signature: opaque(86, 86) }).strict();
const schema = z.discriminatedUnion("action", [
  z.object({ action: z.literal("identity") }).strict(),
  z.object({ action: z.literal("recover") }).strict(),
  z.object({ action: z.literal("inbox") }).strict(),
  z.object({ action: z.literal("register"), registration, recoveryCode: opaque(43, 43) }).strict(),
  z.object({ action: z.literal("open"), friendshipId: id, before: z.string().regex(/^[1-9][0-9]{0,18}$/).refine(value => BigInt(value) <= 9223372036854775807n).optional() }).strict(),
  z.object({ action: z.literal("send"), envelope }).strict(),
  z.object({ action: z.literal("read"), friendshipId: id, messageId: z.string().uuid() }).strict()
]);
const reply = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "private, no-store" } });
export async function POST(request: Request) {
  if (!hasSameOrigin(request)) return reply({ error: "origin_not_allowed" }, 403);
  try {
    const actor = await getCurrentActor();
    if (!actor || actor.internalTestMode) return reply({ error: "authentication_required" }, 401);
    if (!matchesExpectedActor(request.headers.get("x-asterion-actor"), actor.id)) return reply({ error: "session_changed" }, 409);
    let input;
    try { input = schema.safeParse(await readBoundedJson(request, 24_576)); } catch { return reply({ error: "invalid_command" }, 400); }
    if (!input.success) return reply({ error: "invalid_command" }, 400);
    const result = await recoveringChatCommand(actor.id, input.data);
    return reply(result, "error" in result ? result.error === "rate_limited" ? 429 : 400 : 200);
  } catch (error) {
    return reply({ error: error instanceof AccessPolicyError ? "access_denied" : "temporarily_unavailable" }, error instanceof AccessPolicyError ? 403 : 503);
  }
}
