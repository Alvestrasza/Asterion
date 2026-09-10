"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import type { Locale } from "@/lib/i18n";
import { getSocialMessages } from "@/lib/social-messages";
import { normalizeFriendCode } from "@/lib/friend-code-policy";
type Friend = { id: string; username: string; status: string; online: boolean | null; level: number | null };
export function FriendsClient({ actorId, locale }: { actorId: string; locale: Locale }) {
  const t = getSocialMessages(locale);
  const [friends, setFriends] = useState<Friend[]>([]);
  const [username, setUsername] = useState("");
  const [discoverable, setDiscoverable] = useState(false);
  const [query, setQuery] = useState("");
  const [friendCode, setFriendCode] = useState("");
  const [result, setResult] = useState<{ username: string; friendCode: string } | null>(null);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [sessionChanged, setSessionChanged] = useState(false);
  const stopped = useRef(false);
  const initialized = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const call = useCallback(async (command: Record<string, unknown>) => {
    if (stopped.current) throw new Error("session_changed");
    const signal = controller.current?.signal;
    const response = await fetch("/api/friends", { method: "POST", cache: "no-store", signal,
      headers: { "Content-Type": "application/json", "X-Asterion-Actor": actorId }, body: JSON.stringify(command) });
    if (signal?.aborted) throw new Error("session_changed");
    if ([401, 403, 409].includes(response.status)) {
      stopped.current = true; setSessionChanged(true); setFriends([]); setResult(null); setUsername(""); setQuery(""); setFriendCode("");
    }
    const data = await response.json();
    if (signal?.aborted) throw new Error("session_changed");
    if (!response.ok) throw new Error(data.error ?? "unavailable");
    return data;
  }, [actorId]);
  const load = useCallback(async (initial = false) => {
    const data = await call({ action: "list" });
    if (stopped.current) return;
    setFriends(data.friends);
    setFriendCode(data.profile.friendCode);
    if (initial || !initialized.current) {
      setUsername(data.profile.username); setDiscoverable(data.profile.discoverable);
      initialized.current = true; setReady(true); setNotice("");
    }
  }, [call]);
  useEffect(() => {
    stopped.current = false; controller.current = new AbortController();
    initialized.current = false; setReady(false); setFriendCode(""); setFriends([]); setResult(null); setQuery(""); setUsername(""); setSessionChanged(false);
    void load(true).catch(() => { if (!stopped.current) setNotice(t.error); });
    let refreshing = false;
    const timer = setInterval(async () => {
      if (stopped.current || refreshing || document.visibilityState !== "visible") return;
      refreshing = true;
      try { await load(); } catch { if (!stopped.current) setNotice(t.error); } finally { refreshing = false; }
    }, 30_000);
    return () => { stopped.current = true; controller.current?.abort(); clearInterval(timer); };
  }, [load, t.error]);
  async function act(command: Record<string, unknown>, success = "") {
    if (busy || stopped.current) return;
    setBusy(true); setNotice("");
    if (command.action === "search") setResult(null);
    try {
      const data = await call(command);
      if (stopped.current) return;
      if (command.action === "search") {
        const searchedCode = normalizeFriendCode(command.query);
        setResult(data.result && searchedCode ? { username: data.result.username, friendCode: searchedCode } : null);
        setQuery(""); if (!data.result) setNotice(t.noResult);
      }
      else { setResult(null); setNotice(success); await load(); }
    } catch (error) {
      const code = error instanceof Error ? error.message : "";
      const message: Record<string, string> = { rate_limited: t.rate, profile_required: t.profileRequired, invalid_username: t.hint,
        username_unavailable: t.usernameUnavailable, request_cooldown: t.cooldown, target_unavailable: t.unavailable, request_unavailable: t.unavailable };
      setNotice(message[code] ?? t.error);
    } finally { setBusy(false); }
  }
  const disabled = busy || !ready || sessionChanged;
  return <>
    <p>{t.privacy}</p><p role="status" aria-live="polite">{notice}</p>
    {sessionChanged && <p role="alert"><a href="/login">{t.error}</a></p>}
    <section className="social-card">
      <label htmlFor="own-friend-code">{t.friendCode}</label>
      <input id="own-friend-code" value={friendCode} readOnly autoComplete="off" aria-describedby="friend-code-hint" onFocus={event => event.target.select()} />
      <p id="friend-code-hint">{t.friendCodeHint}</p>
      <form onSubmit={event => { event.preventDefault(); void act({ action: "profile", username, discoverable }, t.saved); }}>
      <label htmlFor="player-name">{t.username}</label>
      <input id="player-name" value={username} onChange={event => setUsername(event.target.value)} minLength={3} maxLength={32} pattern="[a-zA-Z0-9][a-zA-Z0-9_.\-]{2,31}" required autoComplete="off" aria-describedby="username-hint" disabled={disabled} />
      <p id="username-hint">{t.hint}</p>
      <label className="social-checkbox"><input type="checkbox" checked={discoverable} onChange={event => setDiscoverable(event.target.checked)} disabled={disabled} />{t.discoverable}</label>
      <button className="quiet-button" disabled={disabled}>{t.save}</button>
    </form></section>
    <section className="social-card"><h2>{t.search}</h2><form onSubmit={event => { event.preventDefault(); if (!normalizeFriendCode(query)) { setNotice(t.codeInvalid); return; } void act({ action: "search", query }); }}>
      <label htmlFor="friend-query">{t.query}</label><input id="friend-query" type="search" autoComplete="off" autoCapitalize="characters" spellCheck={false} placeholder="XXXXX-XXX-XXXXX" value={query} onChange={event => { setQuery(event.target.value); setResult(null); }} maxLength={64} required disabled={disabled} />
      <button className="quiet-button" disabled={disabled}>{t.find}</button>
    </form>{result && <p>{result.username} <button className="quiet-button" disabled={disabled} onClick={() => void act({ action: "request", friendCode: result.friendCode }, t.sent)}>{t.request}</button></p>}</section>
    {(["accepted", "incoming", "outgoing", "blocked"] as const).map(status => <section className="social-card" key={status}>
      <h2>{t[status]}</h2>{!friends.some(friend => friend.status === status) && <p>{t.empty}</p>}
      <ul className="friend-list">{friends.filter(friend => friend.status === status).map(friend => <li key={friend.id}>
        <strong>{friend.username}</strong>{status === "accepted" && <span>{friend.online ? t.online : t.offline} · {t.level} {friend.level}</span>}
        <div className="friend-actions">{(status === "accepted" ? ["remove", "block"] : status === "incoming" ? ["accept", "decline", "block"] : status === "outgoing" ? ["remove", "block"] : ["unblock"]).map(action => <button
          className="quiet-button" key={action} disabled={disabled} onClick={() => {
            if (["remove", "block", "unblock"].includes(action) && !window.confirm(t.confirm)) return;
            void act({ action, friendshipId: friend.id });
          }}>{status === "outgoing" && action === "remove" ? t.cancel : t[action as "accept" | "decline" | "remove" | "block" | "unblock"]}</button>)}</div>
      </li>)}</ul>
    </section>)}
  </>;
}
