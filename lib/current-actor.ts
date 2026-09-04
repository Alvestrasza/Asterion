import { auth } from "@/auth";
import { prisma } from "@/lib/db";

const INTERNAL_TEST_EMAIL = "internal-test@asterion.invalid";

export type CurrentActor = {
  id: string;
  name: string;
  internalTestMode: boolean;
};

export function isInternalTestMode() {
  return process.env.ASTERION_INTERNAL_TEST_MODE?.trim().toLowerCase() === "true";
}

export async function getCurrentActor(): Promise<CurrentActor | null> {
  const session = await auth();
  if (session?.user?.id) {
    return {
      id: session.user.id,
      name: session.user.name ?? session.user.email ?? "Gefährte",
      internalTestMode: false
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
    internalTestMode: true
  };
}
