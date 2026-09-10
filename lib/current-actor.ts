import { auth } from "@/auth";
import { prisma } from "@/lib/db";
import { isPublicDeployment } from "@/lib/deployment-config";
import { accessIsEffective, admitAuthenticatedUser } from "@/lib/access-service";

const INTERNAL_TEST_EMAIL = "internal-test@asterion.invalid";

export type CurrentActor = {
  id: string;
  name: string;
  internalTestMode: boolean;
  isAdmin: boolean;
};

export function isInternalTestMode() {
  return !isPublicDeployment() && process.env.ASTERION_INTERNAL_TEST_MODE?.trim().toLowerCase() === "true";
}

export async function getCurrentActor(): Promise<CurrentActor | null> {
  const session = await auth();
  if (session?.user?.id) {
    if (!isPublicDeployment() && !isInternalTestMode()) return null;
    const access = isPublicDeployment() ? await admitAuthenticatedUser(session.user.id) : null;
    if (isPublicDeployment() && !accessIsEffective(access)) return null;
    return {
      id: session.user.id,
      name: session.user.name ?? session.user.email ?? "Gefährte",
      internalTestMode: false,
      isAdmin: access?.effectiveRole === "admin"
    };
  }

  if (!isInternalTestMode()) return null;

  const user = await prisma.user.upsert({
    where: { email: INTERNAL_TEST_EMAIL },
    update: { name: "Interner Test" },
    create: { email: INTERNAL_TEST_EMAIL, name: "Interner Test" },
    select: { id: true, name: true }
  });

  return {
    id: user.id,
    name: user.name ?? "Interner Test",
    internalTestMode: true,
    isAdmin: false
  };
}
