import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentActor } from "@/lib/current-actor";
import { getPetSnapshot } from "@/lib/pet-service";
import { getRequestLocale } from "@/lib/request-locale";
import { getMessages } from "@/lib/messages";
import { AsterionClient } from "../asterion-client";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function CarePage() {
  const actor = await getCurrentActor();
  if (!actor) redirect("/login");
  const [pet, locale] = await Promise.all([getPetSnapshot(actor.id), getRequestLocale()]);
  const t = getMessages(locale);
  return (
    <>
      <div className="care-navigation">
        <Link href="/">← {t.care.back}</Link>
        {locale !== "de" && <p>{t.care.legacyLanguage}</p>}
      </div>
      {/* The existing care screen is migrated in the next localization slice. */}
      <div lang="de">
        <AsterionClient initialPet={pet} userId={actor.id} userName={actor.name} internalTestMode={actor.internalTestMode} />
      </div>
    </>
  );
}
