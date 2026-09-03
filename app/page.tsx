import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { getPetSnapshot } from "@/lib/pet-service";
import { AsterionClient } from "./asterion-client";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const session = await auth();
  if (!session?.user?.id) redirect("/login");

  const pet = await getPetSnapshot(session.user.id);
  return <AsterionClient initialPet={pet} userId={session.user.id} userName={session.user.name ?? session.user.email ?? "Gefährte"} />;
}
