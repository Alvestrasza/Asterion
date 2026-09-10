import Link from "next/link";
import { redirect } from "next/navigation";
import { auth } from "@/auth";
import { logout } from "@/app/actions";
import { getCurrentActor } from "@/lib/current-actor";
import { getRequestLocale } from "@/lib/request-locale";
import { getAccessMessages } from "@/lib/access-messages";
import { localizedPath } from "@/lib/i18n";

export const dynamic = "force-dynamic";
export const metadata = { robots: { index: false, follow: false } };

export default async function AccessPage() {
  const locale = await getRequestLocale();
  const session = await auth();
  if (!session?.user?.id) redirect(localizedPath("/login", locale));
  if (await getCurrentActor()) redirect(localizedPath("/care", locale));
  const t = getAccessMessages(locale);
  return <main className="login-shell"><section className="login-card">
    <p className="eyebrow">Starfriends</p><h1>{t.unavailableTitle}</h1><p>{t.unavailableText}</p>
    <a className="login-button" href={localizedPath("/access", locale)}>{t.refresh}</a>
    <form action={logout}><button className="quiet-button" type="submit">{t.logout}</button></form>
    <Link href={localizedPath("/", locale)}>{t.home}</Link>
  </section></main>;
}
