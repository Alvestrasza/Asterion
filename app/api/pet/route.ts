import { auth } from "@/auth";
import { getPetSnapshot } from "@/lib/pet-service";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  const session = await auth();
  if (!session?.user?.id) {
    return Response.json({ error: "authentication_required" }, { status: 401 });
  }

  const pet = await getPetSnapshot(session.user.id);
  return Response.json(
    { pet },
    {
      headers: {
        "Cache-Control": "private, no-store"
      }
    }
  );
}
