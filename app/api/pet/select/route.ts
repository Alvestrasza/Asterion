import { z } from "zod";
import { getCurrentActor } from "@/lib/current-actor";
import { hasSameOrigin, readBoundedJson } from "@/lib/http";
import { matchesExpectedActor } from "@/lib/actor-binding";
import { selectOwnedPet, PetRequestError } from "@/lib/pet-service";
import { AccessPolicyError } from "@/lib/access-policy";

export const runtime = "nodejs";
const schema = z.object({ petId: z.string().min(1).max(128) }).strict();
const reply = (body: unknown, status = 200) => Response.json(body, { status, headers: { "Cache-Control": "private, no-store" } });

export async function POST(request: Request) {
  if (!hasSameOrigin(request)) return reply({ error: "origin_not_allowed" }, 403);
  const actor = await getCurrentActor();
  if (!actor) return reply({ error: "authentication_required" }, 401);
  if (!matchesExpectedActor(request.headers.get("x-asterion-actor"), actor.id)) return reply({ error: "session_changed" }, 409);
  let input;
  try { input = schema.safeParse(await readBoundedJson(request, 1024)); } catch { return reply({ error: "invalid_command" }, 400); }
  if (!input.success) return reply({ error: "invalid_command" }, 400);
  try {
    await selectOwnedPet(actor.id, input.data.petId);
    return reply({ selected: input.data.petId });
  } catch (error) {
    const status = error instanceof AccessPolicyError ? 403 : error instanceof PetRequestError ? error.status : 503;
    return reply({ error: error instanceof PetRequestError ? error.code : "temporarily_unavailable" }, status);
  }
}
