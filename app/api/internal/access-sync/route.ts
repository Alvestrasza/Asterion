import { timingSafeEqual } from "node:crypto";
import { isPublicDeployment } from "@/lib/deployment-config";
import { syncAccessBatch } from "@/lib/access-service";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export async function POST(request: Request) {
  const secret = process.env.ASTERION_ACCESS_SYNC_SECRET;
  const supplied = request.headers.get("authorization") ?? "";
  const expected = `Bearer ${secret ?? ""}`;
  if (!isPublicDeployment() || !secret || secret.length < 32 || supplied.length > 512 ||
    Buffer.byteLength(supplied) !== Buffer.byteLength(expected) || !timingSafeEqual(Buffer.from(supplied), Buffer.from(expected))) {
    return new Response(null, { status: 404, headers: { "Cache-Control": "no-store" } });
  }
  try { return Response.json(await syncAccessBatch(20), { headers: { "Cache-Control": "no-store" } }); }
  catch { return Response.json({ error: "sync_unavailable" }, { status: 503, headers: { "Cache-Control": "no-store" } }); }
}
