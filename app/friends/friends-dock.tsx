"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { localizedPath, type Locale } from "@/lib/i18n";
import { getSocialMessages } from "@/lib/social-messages";
import { getDockMessages } from "@/lib/dock-messages";
import { createDockPolling, type DockFriend } from "@/lib/dock-polling";
import { Messenger } from "./messenger";
import styles from "./friends-dock.module.css";

export function FriendsDock({ actorId, locale }: { actorId: string; locale: Locale }) {
  const t = getSocialMessages(locale);
  const d = getDockMessages(locale);
  const listId = useId();
  const [expanded, setExpanded] = useState(false);
  const [friends, setFriends] = useState<DockFriend[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "unavailable" | "ended">("loading");
  const [conversation, setConversation] = useState<DockFriend | null>(null);
  const [unread, setUnread] = useState<Record<string, number>>({});
  const toggle = useRef<HTMLButtonElement>(null);
  const key = `asterion.friends-dock.${actorId}.expanded`;

  useEffect(() => {
    // Only the panel preference is stored, never friends, presence or messages.
    const desktop = window.matchMedia("(min-width: 1280px)").matches;
    try { setExpanded(desktop && localStorage.getItem(key) !== "false"); }
    catch { setExpanded(desktop); }
  }, [key]);

  useEffect(() => {
    document.body.dataset.friendsDock = expanded ? "expanded" : "collapsed";
    return () => { delete document.body.dataset.friendsDock; };
  }, [expanded]);

  useEffect(() => {
    setFriends([]); setConversation(null); setStatus("loading");
    const polling = createDockPolling({ actorId, request: fetch,
      publish(rows, transient) {
        setFriends(rows); setStatus("ready");
        if (!transient) setConversation(current => rows.find(friend => friend.id === current?.id && friend.status === "accepted") ?? null);
      },
      unread: setUnread,
      unavailable() { setStatus("unavailable"); },
      sessionEnded() { setStatus("ended"); setConversation(null); }
    });
    const visibility = () => polling.setVisible(document.visibilityState === "visible");
    const sessionEnded = () => polling.endSession();
    const storage = (event: StorageEvent) => { if (event.key === "asterion.session-ended") sessionEnded(); };
    visibility();
    const timer = setInterval(() => { void polling.refresh(); }, 30_000);
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("storage", storage);
    window.addEventListener("asterion-session-ended", sessionEnded);
    return () => {
      clearInterval(timer); polling.dispose();
      document.removeEventListener("visibilitychange", visibility);
      window.removeEventListener("storage", storage);
      window.removeEventListener("asterion-session-ended", sessionEnded);
    };
  }, [actorId]);

  const accepted = friends.filter(friend => friend.status === "accepted");
  const incoming = friends.filter(friend => friend.status === "incoming").length;
  const unreadTotal = accepted.reduce((total, friend) => total + (unread[friend.id] ?? 0), 0);
  const active = conversation;
  function changeExpanded() {
    const next = !expanded;
    setExpanded(next);
    if (!next) setConversation(null);
    try { localStorage.setItem(key, String(next)); } catch { /* Storage is optional. */ }
  }
  function closeConversation() { setConversation(null); toggle.current?.focus(); }

  return <aside className={styles.dock} aria-label={t.title} lang={locale} onKeyDown={event => {
    if (event.key === "Escape") {
      if (conversation) closeConversation();
      else if (expanded) { changeExpanded(); toggle.current?.focus(); }
    }
  }}>
    <button className={styles.toggle} type="button" ref={toggle} aria-expanded={expanded} aria-controls={listId}
      aria-label={`${expanded ? d.collapse : d.expand}${incoming ? `, ${d.requests}: ${incoming}` : ""}${unreadTotal ? `, ${d.unread}: ${unreadTotal}` : ""}`} onClick={changeExpanded}>
      <span>{t.title}{status === "ready" && <> · {accepted.length}</>}</span>
      {incoming > 0 && <span className={styles.badge} aria-label={`${d.requests}: ${incoming}`}>{incoming}</span>}
      {unreadTotal > 0 && <span className={styles.badge} aria-label={`${d.unread}: ${unreadTotal}`}><span aria-hidden="true">✉ </span>{unreadTotal > 99 ? "99+" : unreadTotal}</span>}
      <span aria-hidden="true">{expanded ? "▴" : "▾"}</span>
    </button>
    <div id={listId} hidden={!expanded} className={styles.panel}>
      {status !== "ready" && <p role="status">{status === "loading" ? d.loading : status === "ended"
        ? <Link href={localizedPath("/login", locale)}>{d.sessionEnded}</Link> : d.unavailable}</p>}
      {status === "ready" && (accepted.length ? <ul className={styles.list}>{accepted.map(friend => <li key={friend.id}>
        <button type="button" className={styles.friend} onClick={() => setConversation(friend)} aria-label={`${d.chat} ${friend.username}${unread[friend.id] ? `, ${d.unread}: ${unread[friend.id]}` : ""}`}>
          <span className={friend.online ? styles.online : styles.offline} aria-hidden="true" />
          <span className={styles.identity}><strong>{friend.username}</strong><small>
            {friend.online === null ? d.unknown : friend.online ? t.online : t.offline}
            {friend.level !== null && <> · {t.level} {friend.level}</>}
          </small></span>
          {unread[friend.id] > 0 && <span className={styles.badge} aria-label={`${d.unread}: ${unread[friend.id]}`}>{unread[friend.id] > 99 ? "99+" : unread[friend.id]}</span>}
        </button>
      </li>)}</ul> : <p>{t.empty}</p>)}
      <Link className={styles.manage} href={localizedPath("/friends", locale)} prefetch={false}>
        {incoming ? `${d.requests}: ${incoming}` : d.manage}
      </Link>
    </div>
    {expanded && active && <Messenger key={`${actorId}:${active.id}`} actorId={actorId} friendshipId={active.id} friendName={active.username} locale={locale} onClose={closeConversation} />}
  </aside>;
}
