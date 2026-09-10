"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { localizedPath, type Locale } from "@/lib/i18n";
import { getMessages } from "@/lib/messages";
import { getAccessMessages } from "@/lib/access-messages";
import { getSocialMessages } from "@/lib/social-messages";
import { LanguageSelector } from "./language-selector";
import { logout } from "./actions";
import { FriendsDock } from "./friends/friends-dock";
import { Presence } from "./presence";

type HeaderActor = { id: string; name: string; isAdmin: boolean; internalTestMode: boolean };
type PagePath = "/" | "/care" | "/friends" | "/admin";

export function SiteHeader({ locale, currentPath, actor, children, onLogout }: {
  locale: Locale; currentPath: PagePath; actor: HeaderActor | null;
  children?: ReactNode; onLogout?: () => void;
}) {
  const t = getMessages(locale);
  const access = getAccessMessages(locale);
  const links: { path: PagePath; label: string }[] = [{ path: "/", label: t.nav.home }];
  if (actor) {
    links.push({ path: "/care", label: t.nav.care });
    if (!actor.internalTestMode) links.push({ path: "/friends", label: getSocialMessages(locale).title });
    if (actor.isAdmin && !actor.internalTestMode) links.push({ path: "/admin", label: access.admin });
  }
  return <><header className="public-header site-header" lang={locale}>
    <Link className="public-brand" href={localizedPath("/", locale)} aria-label={t.nav.home}><span aria-hidden="true">✦</span> Starfriends</Link>
    <nav className="public-nav" aria-label={t.nav.home}>
      {links.map(({ path, label }) => <Link key={path} href={localizedPath(path, locale)} prefetch={false} aria-current={currentPath === path ? "page" : undefined}>{label}</Link>)}
      {!actor && <><Link href={`${localizedPath("/", locale)}#about`}>{t.nav.about}</Link><Link href={`${localizedPath("/", locale)}#companions`}>{t.nav.companions}</Link></>}
    </nav>
    <div className="public-header-actions">
      {actor && <span className="user-chip" title={actor.name}>{actor.name}</span>}
      <LanguageSelector locale={locale} labels={t.nav} returnTo={currentPath} />
      {children}
      {actor ? !actor.internalTestMode && <form action={logout} onSubmit={() => {
        try { localStorage.setItem("asterion.session-ended", String(Date.now())); } catch { /* Storage is optional. */ }
        window.dispatchEvent(new Event("asterion-session-ended"));
        onLogout?.();
      }}><button className="quiet-button" type="submit">{access.logout}</button></form>
        : <Link className="public-button primary" href={localizedPath("/login", locale)} prefetch={false}>{t.nav.signIn}</Link>}
    </div>
  </header>{actor && !actor.internalTestMode && <><Presence key={`presence:${actor.id}`} actorId={actor.id} /><FriendsDock key={actor.id} actorId={actor.id} locale={locale} /></>}</>;
}
