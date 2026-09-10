import { redirect } from "next/navigation";
import { getCurrentActor } from "@/lib/current-actor";
import { getRequestLocale } from "@/lib/request-locale";
import { getSocialMessages } from "@/lib/social-messages";
import { localizedPath } from "@/lib/i18n";
import { SiteHeader } from "../site-header";
import { FriendsClient } from "./friends-client";
import "../social.css";
export const dynamic = "force-dynamic";
export const metadata = { robots: { index: false, follow: false } };
export default async function FriendsPage() {
  const locale = await getRequestLocale();
  const actor = await getCurrentActor();
  if (!actor) redirect(localizedPath("/access", locale));
  if (actor.internalTestMode) redirect(localizedPath("/care", locale));
  const t = getSocialMessages(locale);
  return <><div className="public-shell"><SiteHeader locale={locale} currentPath="/friends" actor={actor} /></div>
    <main className="social-shell" lang={locale}><h1>{t.title}</h1>
    <FriendsClient key={actor.id} actorId={actor.id} locale={locale} /></main></>;
}
