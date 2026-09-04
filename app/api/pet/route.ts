import { getCurrentActor } from "@/lib/current-actor";
import { getPetSnapshot } from "@/lib/pet-service";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const actor = await getCurrentActor();
  if (!actor) {
    return Response.json({ error: "authentication_required" }, { status: 401 });
  }

  const pet = await getPetSnapshot(actor.id);
  return Response.json(
    { pet },
    {
      headers: {
        "Cache-Control": "private, no-store"
      }
    }
  );
}
