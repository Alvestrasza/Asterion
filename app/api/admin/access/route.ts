import { z } from "zod";
import { getCurrentActor } from "@/lib/current-actor";
import { hasSameOrigin, readBoundedJson } from "@/lib/http";
import { matchesExpectedActor } from "@/lib/actor-binding";
import { AccessPolicyError, setDesiredRole } from "@/lib/access-service";

export const dynamic = "force-dynamic";
const schema = z.object({ targetId: z.string().min(1).max(100), desiredRole: z.enum(["none", "member", "admin"]) }).strict();
const headers = { "Cache-Control": "private, no-store" };

export async function POST(request: Request) {
  if (!hasSameOrigin(request)) return Response.json({ error: "origin_not_allowed" }, { status: 403, headers });
  const actor = await getCurrentActor();
  if (!actor?.isAdmin || actor.internalTestMode) return Response.json({ error: "admin_required" }, { status: 403, headers });
  if (!matchesExpectedActor(request.headers.get("x-asterion-actor"), actor.id)) return Response.json({ error: "session_changed" }, { status: 409, headers });
  let input;
  try { input = schema.parse(await readBoundedJson(request, 2048)); }
  catch { return Response.json({ error: "invalid_request" }, { status: 400, headers }); }
  try {
    await setDesiredRole(actor.id, input.targetId, input.desiredRole);
    return Response.json({ status: "pending" }, { headers });
  } catch (error) {
    return Response.json({ error: error instanceof AccessPolicyError ? error.code : "temporarily_unavailable" }, { status: error instanceof AccessPolicyError ? 409 : 503, headers });
  }
}
