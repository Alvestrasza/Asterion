import { redirect } from "next/navigation";
import { getCurrentActor } from "@/lib/current-actor";
import { assertAccess } from "@/lib/access-service";
import { prisma } from "@/lib/db";
import { getRequestLocale } from "@/lib/request-locale";
import { getAccessMessages } from "@/lib/access-messages";
import { accessCheckIsFresh } from "@/lib/access-policy";
import { Administration } from "./administration";
import { SiteHeader } from "../site-header";
import { localizedPath } from "@/lib/i18n";
import { displayUsername } from "@/lib/social-policy";

export const dynamic = "force-dynamic";
export const metadata = { robots: { index: false, follow: false } };

export default async function AdministrationPage() {
  const actor = await getCurrentActor();
  const locale = await getRequestLocale();
  if (!actor) redirect(localizedPath("/login", locale));
  if (!actor.isAdmin || actor.internalTestMode) redirect(localizedPath("/care", locale));
  const accounts = await prisma.$transaction(async (tx) => {
    await assertAccess(tx, actor.id, "admin");
    return tx.userAccess.findMany({ where: { issuer: process.env.AUTH_KEYCLOAK_ISSUER },
      select: { userId: true, desiredRole: true, effectiveRole: true, syncStatus: true, errorCode: true, checkedAt: true, user: { select: { name: true, email: true, socialProfile: { select: { username: true, usernameDisplay: true } } } } },
      orderBy: { createdAt: "desc" }, take: 100 });
  });
  const t = getAccessMessages(locale);
  return <div className="public-shell"><SiteHeader locale={locale} currentPath="/admin" actor={actor} /><main><section className="public-section admin-section">
    <h1>{t.admin}</h1><p>{t.intro}</p>
    <Administration actorId={actor.id} locale={locale} accounts={accounts.map((entry) => ({
      userId: entry.userId, name: entry.user.name ?? entry.user.email ?? entry.userId,
      username: displayUsername(entry.user.socialProfile),
      desiredRole: entry.desiredRole, effectiveRole: accessCheckIsFresh(entry.checkedAt) ? entry.effectiveRole : "none",
      syncStatus: entry.syncStatus, errorCode: entry.errorCode, checkedAt: entry.checkedAt?.toISOString() ?? null
    }))} />
  </section></main></div>;
}
