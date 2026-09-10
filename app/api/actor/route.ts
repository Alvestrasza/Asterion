import { getCurrentActor } from "@/lib/current-actor";
import { matchesExpectedActor } from "@/lib/actor-binding";

export const dynamic = "force-dynamic";
export async function GET(request: Request) {
  const actor = await getCurrentActor();
  const status = !actor ? 401 : matchesExpectedActor(request.headers.get("x-asterion-actor"), actor.id) ? 200 : 409;
  return Response.json({ status: status === 200 ? "current" : "session_changed" }, { status, headers: { "Cache-Control": "private, no-store" } });
}
