import { getCurrentActor } from "@/lib/current-actor";
import { getPetCollection, getPetSnapshot, PetRequestError } from "@/lib/pet-service";
import { matchesExpectedActor } from "@/lib/actor-binding";
import { getRequestLocale } from "@/lib/request-locale";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const actor = await getCurrentActor();
  if (!actor) {
    return Response.json({ error: "authentication_required" }, { status: 401 });
  }
  if (!matchesExpectedActor(request.headers.get("x-asterion-actor"), actor.id)) return Response.json({ error: "session_changed" }, { status: 409, headers: { "Cache-Control": "no-store" } });

  let pet;
  let collection;
  try {
    pet = await getPetSnapshot(actor.id, await getRequestLocale());
    collection = await getPetCollection(actor.id);
  } catch (error) {
    if (error instanceof PetRequestError) {
      return Response.json({ error: error.message }, {
        status: error.status, headers: { "Cache-Control": "private, no-store" }
      });
    }
    throw error;
  }
  return Response.json(
    { pet, collection },
    {
      headers: {
        "Cache-Control": "private, no-store"
      }
    }
  );
}
