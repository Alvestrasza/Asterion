import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { getCurrentActor } from "@/lib/current-actor";
import { getPetSnapshot, hasPet } from "@/lib/pet-service";
import { getRequestLocale } from "@/lib/request-locale";
import { getMessages } from "@/lib/messages";
import { AsterionClient } from "../asterion-client";
import { ChooseCompanion } from "../choose-companion";
import { localizedPath } from "@/lib/i18n";
import { SiteHeader } from "../site-header";
import "../social.css";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function CarePage() {
  const locale = await getRequestLocale();
  const actor = await getCurrentActor();
  if (!actor) redirect(localizedPath("/access", locale));
  if (!actor.internalTestMode && !await hasPet(actor.id)) return <>
    <div className="public-shell"><SiteHeader locale={locale} currentPath="/care" actor={actor} /></div>
    <ChooseCompanion actorId={actor.id} locale={locale} />
  </>;
  const pet = await getPetSnapshot(actor.id);
  const t = getMessages(locale);
  return (
    <>
      {locale !== "de" && <p className="care-navigation">{t.care.legacyLanguage}</p>}
      {/* The existing care screen is migrated in the next localization slice. */}
      <div lang="de">
        <AsterionClient initialPet={pet} userId={actor.id} userName={actor.name} internalTestMode={actor.internalTestMode} isAdmin={actor.isAdmin} locale={locale} />
      </div>
    </>
  );
}
