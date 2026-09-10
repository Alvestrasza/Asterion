import { z } from "zod";
import { getCurrentActor } from "@/lib/current-actor";
import { hasSameOrigin, readBoundedJson } from "@/lib/http";
import { matchesExpectedActor } from "@/lib/actor-binding";
import { socialCommand } from "@/lib/social-service";
import { AccessPolicyError } from "@/lib/access-policy";
import { normalizeFriendCode } from "@/lib/friend-code-policy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const schema = z.discriminatedUnion("action", [
  z.object({ action: z.literal("list") }).strict(),
  z.object({ action: z.literal("heartbeat") }).strict(),
  z.object({ action: z.literal("profile"), username: z.string().max(32), discoverable: z.boolean() }).strict(),
  z.object({ action: z.literal("search"), query: z.string().max(64).refine(value => normalizeFriendCode(value) !== null) }).strict(),
  z.object({ action: z.literal("request"), friendCode: z.string().max(64).refine(value => normalizeFriendCode(value) !== null) }).strict(),
  ...(["accept", "decline", "remove", "block", "unblock"] as const).map(action => z.object({ action: z.literal(action), friendshipId: z.string().min(1).max(128) }).strict())
]);
const reply = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "private, no-store" } });
export async function POST(request: Request) {
  if (!hasSameOrigin(request)) return reply({ error: "origin_not_allowed" }, 403);
  try {
    const actor = await getCurrentActor();
    if (!actor || actor.internalTestMode) return reply({ error: "authentication_required" }, 401);
    if (!matchesExpectedActor(request.headers.get("x-asterion-actor"), actor.id)) return reply({ error: "session_changed" }, 409);
    let input;
    try { input = schema.safeParse(await readBoundedJson(request, 2048)); } catch { return reply({ error: "invalid_command" }, 400); }
    if (!input.success) return reply({ error: "invalid_command" }, 400);
    const result = await socialCommand(actor.id, input.data);
    return reply(result, "error" in result ? result.error === "rate_limited" ? 429 : 400 : 200);
  } catch (error) {
    return reply({ error: error instanceof AccessPolicyError ? "access_denied" : "temporarily_unavailable" }, error instanceof AccessPolicyError ? 403 : 503);
  }
}
