/** Asterion private achievements page. Version: 1.0.0 | License: UNLICENSED | Updated: 2026-10-05 */
import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { getCurrentActor } from "@/lib/current-actor";
import { getPetSnapshot, hasPet } from "@/lib/pet-service";
import { getRequestLocale } from "@/lib/request-locale";
import { localizedPath } from "@/lib/i18n";
import { achievementCopy } from "@/lib/achievements";
import { companionProfile } from "@/lib/companions";
import { AchievementCollection } from "../achievement-collection";
import { SiteHeader } from "../site-header";
import "../achievements.css";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function AchievementsPage() {
  const locale = await getRequestLocale();
  const actor = await getCurrentActor();
  if (!actor) redirect(localizedPath("/access", locale));
  // Opening this page must not choose or create a first companion.
  if (!await hasPet(actor.id)) redirect(localizedPath("/care", locale));
  const pet = await getPetSnapshot(actor.id, locale);
  const copy = achievementCopy(locale);
  return <>
    <div className="public-shell"><SiteHeader locale={locale} currentPath="/achievements" actor={actor} /></div>
    <main className="achievement-shell" lang={locale}>
      {actor.internalTestMode && <aside className="test-mode-banner" role="status" lang="de">
        <strong>Interner Testbetrieb.</strong> Alle Tester auf diesem Dienst teilen momentan denselben Spielstand.
      </aside>}
      <div className="achievement-page-heading">
        <div><h1>{copy.heading}</h1><p>{copy.introduction}</p></div>
        <Link className="public-button secondary" href={localizedPath("/care", locale)} prefetch={false}>{copy.careLink}</Link>
      </div>
      <AchievementCollection achievements={pet.achievements ?? []} companionName={companionProfile(pet.kind).name} locale={locale} />
    </main>
  </>;
}
