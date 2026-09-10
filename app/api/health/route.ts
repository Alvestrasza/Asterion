import { Prisma } from "@prisma/client";
import { prisma } from "@/lib/db";
import { isPublicDeployment, publicRuntimeErrors } from "@/lib/deployment-config";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET() {
  try {
    if (publicRuntimeErrors().length) throw new Error("configuration_not_ready");
    await prisma.$queryRaw(Prisma.sql`SELECT 1`);
    if (isPublicDeployment()) await prisma.userAccess.findFirst({ select: { userId: true } });
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
