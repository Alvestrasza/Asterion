import { z } from "zod";
import { COMPANION_KINDS } from "@/lib/companions";
import { getCurrentActor } from "@/lib/current-actor";
import { hasSameOrigin, readBoundedJson } from "@/lib/http";
import { matchesExpectedActor } from "@/lib/actor-binding";
import { adoptAdditionalPet, chooseFirstPet, PetRequestError } from "@/lib/pet-service";
import { AccessPolicyError } from "@/lib/access-policy";
export const runtime = "nodejs";
const schema = z.object({ kind: z.enum(COMPANION_KINDS), requestId: z.string().uuid().optional() }).strict();
const reply = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "private, no-store" } });
export async function POST(request: Request) {
  if (!hasSameOrigin(request)) return reply({ error: "origin_not_allowed" }, 403);
  try {
    const actor = await getCurrentActor();
    if (!actor) return reply({ error: "authentication_required" }, 401);
    if (!matchesExpectedActor(request.headers.get("x-asterion-actor"), actor.id)) return reply({ error: "session_changed" }, 409);
    let input;
    try { input = schema.safeParse(await readBoundedJson(request, 1024)); } catch { return reply({ error: "invalid_command" }, 400); }
    if (!input.success) return reply({ error: "invalid_command" }, 400);
    return reply({ pet: input.data.requestId
      ? await adoptAdditionalPet(actor.id, input.data.kind, input.data.requestId)
      : await chooseFirstPet(actor.id, input.data.kind) });
  } catch (error) {
    const status = error instanceof AccessPolicyError ? 403 : error instanceof PetRequestError ? error.status : 503;
    return reply({ error: error instanceof PetRequestError ? error.code : "temporarily_unavailable" }, status);
  }
}
