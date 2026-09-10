import { z } from "zod";
import { COMPANION_KINDS } from "@/lib/companions";
import { getCurrentActor } from "@/lib/current-actor";
import { hasSameOrigin, readBoundedJson } from "@/lib/http";
import { performPetCommand, PetRequestError } from "@/lib/pet-service";
import { matchesExpectedActor } from "@/lib/actor-binding";
import { AccessPolicyError } from "@/lib/access-policy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const requestId = z.string().uuid();
const commandSchema = z.discriminatedUnion("action", [
  z.object({ requestId, action: z.enum(["feed", "play", "pet", "sleep", "wake"]) }),
  z.object({ requestId, action: z.literal("reset") }),
  z.object({ requestId, action: z.literal("select"), kind: z.enum(COMPANION_KINDS) }),
  z.object({ requestId, action: z.literal("restore"), state: z.record(z.unknown()) })
]);

export async function POST(request: Request) {
  if (!hasSameOrigin(request)) {
    return Response.json({ error: "origin_not_allowed" }, { status: 403 });
  }

  const actor = await getCurrentActor();
  if (!actor) {
    return Response.json({ error: "authentication_required" }, { status: 401 });
  }
  if (!matchesExpectedActor(request.headers.get("x-asterion-actor"), actor.id)) {
    return Response.json({ error: "session_changed" }, { status: 409, headers: { "Cache-Control": "no-store" } });
  }

  let body: unknown;
  try {
    body = await readBoundedJson(request);
  } catch {
    return Response.json({ error: "invalid_json" }, { status: 400 });
  }

  const parsed = commandSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json({ error: "invalid_command" }, { status: 400 });
  }

  try {
    const result = await performPetCommand(actor.id, parsed.data, request.headers.get("x-asterion-pet") ?? undefined);
    return Response.json(result, { headers: { "Cache-Control": "private, no-store" } });
  } catch (error) {
    const status = error instanceof AccessPolicyError ? 403 : error instanceof PetRequestError ? error.status : 503;
    return Response.json({ error: status === 503 ? "temporarily_unavailable" : "command_rejected" }, {
      status, headers: { "Cache-Control": "no-store", ...(status === 429 ? { "Retry-After": "60" } : {}) }
    });
  }
}
