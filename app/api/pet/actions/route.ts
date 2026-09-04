import { z } from "zod";
import { COMPANION_KINDS } from "@/lib/companions";
import { getCurrentActor } from "@/lib/current-actor";
import { hasSameOrigin } from "@/lib/http";
import { performPetCommand } from "@/lib/pet-service";

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

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: "invalid_json" }, { status: 400 });
  }

  const parsed = commandSchema.safeParse(body);
  if (!parsed.success) {
    return Response.json({ error: "invalid_command" }, { status: 400 });
  }

  const result = await performPetCommand(actor.id, parsed.data);
  return Response.json(result, {
    headers: {
      "Cache-Control": "private, no-store"
    }
  });
}
