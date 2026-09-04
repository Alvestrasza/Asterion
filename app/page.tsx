import { redirect } from "next/navigation";
import { getCurrentActor } from "@/lib/current-actor";
import { getPetSnapshot } from "@/lib/pet-service";
import { AsterionClient } from "./asterion-client";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const actor = await getCurrentActor();
  if (!actor) redirect("/login");

  const pet = await getPetSnapshot(actor.id);
  return (
    <AsterionClient
      initialPet={pet}
      userId={actor.id}
      userName={actor.name}
      internalTestMode={actor.internalTestMode}
    />
  );
}
