import { Prisma } from "@prisma/client";
import { prisma } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    await prisma.$queryRaw(Prisma.sql`SELECT 1`);
    return Response.json(
      { status: "healthy", database: "reachable" },
      { headers: { "Cache-Control": "no-store" } }
    );
  } catch {
    return Response.json(
      { status: "unhealthy", database: "unreachable" },
      { status: 503, headers: { "Cache-Control": "no-store" } }
    );
  }
}
