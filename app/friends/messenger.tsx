"use client";

import { useEffect, useId, useRef, useState } from "react";
import type { Locale } from "@/lib/i18n";
import { chatMessages } from "@/lib/chat-messages";
import { createChatIdentity, restoreChatIdentity, encryptMessage, decryptMessage, verifyRegistration, identityFingerprint, conversationSafetyCode,
  type ChatKeys, type ChatRegistration, type ChatPublicIdentity, type ChatEnvelope } from "@/lib/chat-crypto";
import { loadChatKeys, saveChatKeys, getPeerPin, savePeerPin } from "@/lib/chat-vault";
import { mergeChatMessages, hasChatHistoryGap, lastReceivedMessage, type DisplayMessage, type StoredEnvelope } from "@/lib/chat-client-state";
import styles from "./messenger.module.css";

type Stage = "loading" | "setup" | "restore" | "ready" | "pending" | "denied" | "changed" | "unavailable";
type RecoveryMode = "keycloak" | "legacy" | "unavailable";
type Setup = Awaited<ReturnType<typeof createChatIdentity>>;
type Peer = { id: string; identity: ChatPublicIdentity };
type Conversation = { peerId: string; identity: ChatPublicIdentity | null; messages: StoredEnvelope[]; hasMore: boolean };

export function Messenger({ actorId, friendshipId, friendName, locale, onClose }: {
  actorId: string; friendshipId: string; friendName: string; locale: Locale; onClose: () => void;
}) {
  const t = chatMessages[locale];
  const heading = useId(), codeId = useId(), textId = useId();
  const [stage, setStage] = useState<Stage>("loading");
  const [busy, setBusy] = useState(false), [notice, setNotice] = useState("");
  const [setupPending, setSetupPending] = useState(false);
  const [migrationConsent, setMigrationConsent] = useState(false), [recovery, setRecovery] = useState("");
  const [recoveryMode, setRecoveryMode] = useState<RecoveryMode>("unavailable");
  const [memoryOnly, setMemoryOnly] = useState(false), [verified, setVerified] = useState(false);
  const [safety, setSafety] = useState("");
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [hasMore, setHasMore] = useState(false), [draft, setDraft] = useState("");
  const [retry, setRetry] = useState(false);
  const dialog = useRef<HTMLElement>(null), closeButton = useRef<HTMLButtonElement>(null);
  const epoch = useRef(0), stopped = useRef(false), running = useRef(false), polling = useRef(false);
  const keys = useRef<ChatKeys | null>(null), ownRegistration = useRef<ChatRegistration | null>(null);
  const setup = useRef<Setup | null>(null);
  const peer = useRef<Peer | null>(null), pending = useRef<ChatEnvelope | null>(null);
  const messageState = useRef<DisplayMessage[]>([]), readSequence = useRef(0n);
  const requests = useRef(new Map<AbortController, boolean>());
  const pins = useRef(new Map<string, { fingerprint: string; verified: boolean }>());
  const refreshRef = useRef<() => Promise<void>>(async () => {});

  function erase(update = true) {
    epoch.current++; stopped.current = true;
    requests.current.forEach((_, controller) => controller.abort()); requests.current.clear();
    keys.current = null; ownRegistration.current = null; peer.current = null; pending.current = null; setup.current = null;
    messageState.current = []; pins.current.clear(); readSequence.current = 0n;
    if (update) {
      setMessages([]); setDraft(""); setRecovery(""); setSetupPending(false); setMigrationConsent(false); setSafety(""); setVerified(false); setRetry(false); setNotice("");
    }
  }
  function lock(next: "denied" | "changed") { erase(); setStage(next); }
  function current(version: number) { return !stopped.current && epoch.current === version; }
  async function call(command: Record<string, unknown>, poll = false, endpoint = "/api/chat") {
    if (stopped.current) throw new Error("stale");
    const version = epoch.current, controller = new AbortController();
    requests.current.set(controller, poll);
    const timer = setTimeout(() => controller.abort(), 12_000);
    try {
      const response = await fetch(endpoint, { method: "POST", cache: "no-store", credentials: "same-origin", signal: controller.signal,
        headers: { "Content-Type": "application/json", "X-Asterion-Actor": actorId }, body: JSON.stringify(command) });
      if (!current(version)) throw new Error("stale");
      if ([401, 403, 409].includes(response.status)) { lock("denied"); throw new Error("stale"); }
      const data = await response.json();
      if (!current(version)) throw new Error("stale");
      if (!response.ok) {
        if (data.error === "conversation_unavailable") { lock("denied"); throw new Error("stale"); }
        if (["identity_exists", "invalid_identity", "invalid_message", "message_conflict"].includes(data.error)) { lock("changed"); throw new Error("stale"); }
        throw new Error(data.error ?? "unavailable");
      }
      return data;
    } finally { clearTimeout(timer); requests.current.delete(controller); }
  }
  async function validatePeer(data: Conversation, version: number): Promise<Peer | null> {
    if (!data.identity) {
      if (peer.current) throw new Error("peer_key_changed");
      if (current(version)) setStage("pending"); return null;
    }
    if (typeof data.peerId !== "string" || !data.peerId || data.peerId === actorId || data.identity.version !== 1 ||
      await identityFingerprint(data.identity.encryptionKey, data.identity.signingKey) !== data.identity.fingerprint) throw new Error("peer_key_changed");
    const known = pins.current.get(data.peerId);
    let pin = known;
    try { pin = await getPeerPin(actorId, data.peerId) ?? known; }
    catch { if (current(version)) setMemoryOnly(true); }
    if (!current(version)) return null;
    if ((pin && pin.fingerprint !== data.identity.fingerprint) || (peer.current && (peer.current.id !== data.peerId || peer.current.identity.fingerprint !== data.identity.fingerprint))) throw new Error("peer_key_changed");
    const nextPin = pin ?? { fingerprint: data.identity.fingerprint, verified: false };
    try { await savePeerPin(actorId, data.peerId, nextPin); }
    catch (error) { if (error instanceof Error && error.message === "peer_key_changed") throw error; if (current(version)) setMemoryOnly(true); }
    if (!current(version)) return null;
    pins.current.set(data.peerId, nextPin);
    const next = { id: data.peerId, identity: data.identity };
    peer.current = next; setVerified(nextPin.verified);
    const code = await conversationSafetyCode(keys.current!.identity, next.identity);
    if (!current(version)) return null;
    setSafety(code); return next;
  }
  async function refresh(before?: string) {
    if (polling.current || stopped.current || !keys.current || document.visibilityState !== "visible") return;
    polling.current = true;
    const version = epoch.current;
    try {
      const data: Conversation = await call({ action: "open", friendshipId, ...(before ? { before } : {}) }, true);
      if (!current(version) || document.visibilityState !== "visible") return;
      const recipient = await validatePeer(data, version);
      if (!recipient || !current(version)) return;
      if (!Array.isArray(data.messages) || data.messages.length > 50) throw new Error("invalid_message");
      const decoded: DisplayMessage[] = [];
      const ownKeys = keys.current!;
      for (const envelope of data.messages) {
        const text = await decryptMessage(ownKeys, recipient.id, recipient.identity, friendshipId, envelope);
        if (!current(version) || document.visibilityState !== "visible") return;
        decoded.push({ id: envelope.id, sequence: envelope.sequence, senderId: envelope.senderId, text });
      }
      const resetWindow = !before && hasChatHistoryGap(messageState.current, decoded, data.hasMore);
      const previousCount = messageState.current.length;
      const merged = mergeChatMessages(resetWindow ? [] : messageState.current, decoded);
      messageState.current = merged; setMessages(merged); setStage("ready");
      if (before || resetWindow || previousCount <= 50) setHasMore(data.hasMore);
      const last = lastReceivedMessage(decoded, actorId);
      if (last && BigInt(last.sequence) > readSequence.current && document.visibilityState === "visible") {
        await call({ action: "read", friendshipId, messageId: last.id }, true);
        if (current(version)) readSequence.current = BigInt(last.sequence);
      }
    } catch (error) {
      if (!current(version)) return;
      if (error instanceof Error && ["peer_key_changed", "invalid_message", "message_conflict"].includes(error.message)) lock("changed");
      else if (document.visibilityState === "visible") setNotice(t.error);
    } finally { polling.current = false; }
  }
  refreshRef.current = () => refresh();

  async function install(next: ChatKeys, version: number) {
    if (!current(version)) return;
    try { await saveChatKeys(next); } catch { if (current(version)) setMemoryOnly(true); }
    if (!current(version)) return;
    keys.current = next; setup.current = null; setSetupPending(false); setRecovery(""); setMigrationConsent(false); setStage("pending");
    await refresh();
  }
  async function installRecovered(result: { identity: ChatRegistration; recoveryCode: string }, version: number, expectedFingerprint?: string) {
    if (!current(version)) return;
    if (!result.identity || typeof result.recoveryCode !== "string" ||
      (expectedFingerprint && result.identity.identity.fingerprint !== expectedFingerprint)) { lock("changed"); return; }
    const valid = await verifyRegistration(actorId, result.identity);
    if (!current(version)) return;
    if (!valid) { lock("changed"); return; }
    // A simultaneous first registration may have won with different keys. Always
    // validate and restore the canonical response, never install our draft blindly.
    const restored = await restoreChatIdentity(actorId, result.identity, result.recoveryCode);
    if (!current(version)) return;
    ownRegistration.current = result.identity; setRecoveryMode("keycloak");
    await install(restored, version);
  }
  async function initialize(version: number) {
    try {
      const data = await call({ action: "identity" });
      if (!current(version)) return;
      if (!["keycloak", "legacy", "unavailable"].includes(data.recoveryMode)) throw new Error("invalid_identity_response");
      setRecoveryMode(data.recoveryMode);
      if (!data.identity) { setStage(data.recoveryMode === "keycloak" ? "setup" : "unavailable"); return; }
      const registrationValid = await verifyRegistration(actorId, data.identity);
      if (!current(version)) return;
      if (!registrationValid) { lock("changed"); return; }
      ownRegistration.current = data.identity;
      let stored: ChatKeys | undefined;
      try { stored = await loadChatKeys(actorId, data.identity.identity.fingerprint); }
      catch (error) {
        if (!current(version)) return;
        if (error instanceof Error && error.message === "key_mismatch") { lock("changed"); return; }
        setMemoryOnly(true);
      }
      if (!current(version)) return;
      if (stored) { keys.current = stored; await refreshRef.current(); }
      else if (data.recoveryMode === "keycloak") {
        const result = await call({ action: "recover" });
        await installRecovered(result, version, data.identity.identity.fingerprint);
      } else setStage(data.recoveryMode === "legacy" ? "restore" : "unavailable");
    } catch { if (current(version)) { setNotice(t.error); setStage("unavailable"); } }
  }
  useEffect(() => {
    stopped.current = false; const version = ++epoch.current;
    closeButton.current?.focus();
    void initialize(version);
    const visibility = () => {
      if (document.visibilityState !== "visible") requests.current.forEach((isPoll, controller) => { if (isPoll) controller.abort(); });
      else void refreshRef.current();
    };
    const ended = () => lock("denied");
    const storage = (event: StorageEvent) => { if (event.key === "asterion.session-ended") ended(); };
    const timer = setInterval(() => { void refreshRef.current(); }, 10_000);
    document.addEventListener("visibilitychange", visibility);
    window.addEventListener("storage", storage); window.addEventListener("asterion-session-ended", ended);
    return () => {
      clearInterval(timer); erase(false);
      document.removeEventListener("visibilitychange", visibility);
      window.removeEventListener("storage", storage); window.removeEventListener("asterion-session-ended", ended);
    };
    // The parent keys this component to the actor and friendship; no private state survives either change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [actorId, friendshipId]);

  async function act(work: (version: number) => Promise<void>) {
    if (running.current || stopped.current) return;
    running.current = true; setBusy(true); setNotice(""); const version = epoch.current;
    try { await work(version); }
    catch (error) {
      if (current(version)) {
        if (error instanceof Error && error.message === "peer_key_changed") lock("changed");
        else setNotice(pending.current ? t.failed : t.error);
      }
    } finally { running.current = false; if (current(version)) setBusy(false); }
  }
  async function send(version: number) {
    const own = keys.current, recipient = peer.current;
    if (!own || !recipient) return;
    if (!pending.current) {
      const encrypted = await encryptMessage(own, recipient.id, recipient.identity, friendshipId, draft);
      if (!current(version)) return;
      pending.current = encrypted; setRetry(true);
    }
    const envelope = pending.current;
    const result = await call({ action: "send", envelope });
    if (!current(version)) return;
    if (result.message?.id !== envelope.id) { lock("changed"); return; }
    const text = await decryptMessage(own, recipient.id, recipient.identity, friendshipId, result.message);
    if (!current(version)) return;
    const merged = mergeChatMessages(messageState.current, [{ id: result.message.id, sequence: result.message.sequence, senderId: actorId, text }]);
    messageState.current = merged; setMessages(merged); pending.current = null; setRetry(false); setDraft("");
    void refreshRef.current();
  }
  function close() { erase(); onClose(); }
  function legacyRestore(migrationOnly = false) {
    return <form onSubmit={event => { event.preventDefault(); void act(async version => {
      const registration = ownRegistration.current;
      if (!registration || (migrationOnly && !migrationConsent)) return;
      const restored = await restoreChatIdentity(actorId, registration, recovery);
      if (!current(version)) return;
      if (migrationConsent) {
        const result = await call({ action: "register", registration, recoveryCode: recovery.trim() });
        await installRecovered(result, version, registration.identity.fingerprint);
      } else await install(restored, version);
    }); }}>
      <h3>{migrationOnly ? t.migrate : t.restore}</h3><p>{t.legacyExplanation}</p>
      <label htmlFor={codeId}>{t.code}</label><input id={codeId} type="password" value={recovery} onChange={event => setRecovery(event.target.value)} autoComplete="off" spellCheck={false} maxLength={64} required disabled={busy} />
      <label className={styles.confirm}><input type="checkbox" checked={migrationConsent} onChange={event => setMigrationConsent(event.target.checked)} disabled={busy} />{t.migrationConsent}</label>
      <p>{t.explanation}</p>
      <button type="submit" disabled={busy || !recovery.trim() || (migrationOnly && !migrationConsent)}>{busy ? t.waiting : migrationConsent ? t.migrate : t.unlock}</button>
    </form>;
  }
  return <section className={styles.window} role="dialog" aria-modal="false" aria-labelledby={heading} ref={dialog} lang={locale} onKeyDown={event => {
    if (event.key === "Escape") { event.stopPropagation(); close(); }
  }}>
    <header className={styles.header}><h2 id={heading}>{t.title} · {friendName}</h2><button type="button" ref={closeButton} onClick={close} aria-label={t.close}>×</button></header>
    <div className={styles.body}>
      {memoryOnly && <p role="status" className={styles.warning}>{recoveryMode === "keycloak" ? t.memory : t.legacyMemory}</p>}
      {notice && <p role="status" className={styles.warning}>{notice}</p>}
      {stage === "loading" && <p role="status">{t.loading}</p>}
      {stage === "unavailable" && <><p role="status">{t.unavailable}</p><button type="button" disabled={busy} onClick={() => void act(async version => { setStage("loading"); await initialize(version); })}>{busy ? t.waiting : t.retryRecovery}</button></>}
      {stage === "denied" || stage === "changed" ? <p role="alert">{stage === "denied" ? t.denied : t.changed}</p> : null}
      {stage === "setup" && <><h3>{t.setup}</h3><p>{t.explanation}</p><button type="button" disabled={busy} onClick={() => void act(async version => {
        if (!setup.current) {
          const created = await createChatIdentity(actorId); if (!current(version)) return;
          setup.current = created; setSetupPending(true);
        }
        const created = setup.current;
        const result = await call({ action: "register", registration: created.registration, recoveryCode: created.recoveryCode });
        await installRecovered(result, version);
      })}>{busy ? t.waiting : setupPending ? t.retrySetup : t.create}</button></>}
      {stage === "restore" && legacyRestore()}
      {recoveryMode === "legacy" && ["pending", "ready"].includes(stage) && <details><summary>{t.legacy}</summary>{legacyRestore(true)}</details>}
      {recoveryMode === "unavailable" && ["pending", "ready"].includes(stage) && <p role="status" className={styles.warning}>{t.unavailableLocal}</p>}
      {stage === "pending" && <p role="status">{t.pending}</p>}
      {stage === "ready" && <>
        <details className={styles.safety}><summary>{t.safety} · {verified ? t.verifiedLabel : t.unverified}</summary><p>{t.compare}</p><code>{safety}</code>
          {!verified && <button type="button" disabled={busy} onClick={() => void act(async version => {
            const contact = peer.current; if (!contact) return;
            const pin = { fingerprint: contact.identity.fingerprint, verified: true };
            try { await savePeerPin(actorId, contact.id, pin); }
            catch (error) { if (error instanceof Error && error.message === "peer_key_changed") throw error; if (current(version)) setMemoryOnly(true); }
            if (current(version)) { pins.current.set(contact.id, pin); setVerified(true); }
          })}>{t.verified}</button>}
        </details>
        {hasMore && messages.length < 200 && <button type="button" disabled={busy} onClick={() => void act(async () => { await refresh(messages[0]?.sequence); })}>{t.older}</button>}
        <ol className={styles.messages} aria-label={t.title} aria-live="polite" aria-relevant="additions">
          {messages.map(message => <li key={message.id} className={message.senderId === actorId ? styles.own : styles.received}><p>{message.text}</p></li>)}
        </ol>{!messages.length && <p>{t.empty}</p>}
        <form className={styles.compose} onSubmit={event => { event.preventDefault(); void act(send); }}>
          <label htmlFor={textId}>{t.message}</label><textarea id={textId} value={draft} onChange={event => setDraft(event.target.value)} maxLength={2000} rows={3} disabled={busy || retry} autoComplete="off" spellCheck={false} />
          <button type="submit" disabled={busy || (!retry && !draft.trim())}>{busy ? t.waiting : retry ? t.retry : t.send}</button>
        </form>
      </>}
      <p className={styles.privacy}>{recoveryMode === "keycloak" ? t.privacy : recoveryMode === "legacy" ? t.legacyPrivacy : t.unavailablePrivacy}</p>
      {!["denied", "changed"].includes(stage) && <button className={styles.block} type="button" disabled={busy} onClick={() => {
        if (window.confirm(t.blockConfirm)) void act(async version => { await call({ action: "block", friendshipId }, false, "/api/friends"); if (current(version)) close(); });
      }}>{t.blocked}</button>}
    </div>
  </section>;
}
