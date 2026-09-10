"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Locale } from "@/lib/i18n";
import type { AccessRole } from "@/lib/access-policy";
import { getAccessMessages } from "@/lib/access-messages";

type Account = { userId: string; name: string; username: string | null; desiredRole: AccessRole; effectiveRole: AccessRole; syncStatus: "pending" | "applied" | "failed" | "blocked"; errorCode: string | null; checkedAt: string | null };

export function Administration({ actorId, locale, accounts }: { actorId: string; locale: Locale; accounts: Account[] }) {
  const t = getAccessMessages(locale);
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const roleLabel = (role: AccessRole) => role === "admin" ? t.administrator : t[role];
  async function save(event: React.FormEvent<HTMLFormElement>, targetId: string) {
    event.preventDefault();
    if (busy) return;
    const desiredRole = new FormData(event.currentTarget).get("role");
    setBusy(true); setMessage("");
    try {
      const result = await fetch("/api/admin/access", { method: "POST", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-Asterion-Actor": actorId }, body: JSON.stringify({ targetId, desiredRole }) });
      setMessage(result.ok ? t.success : t.error);
      if (result.ok) router.refresh();
    } catch { setMessage(t.error); } finally { setBusy(false); }
  }
  return <>
    <p role="status">{message}</p><button className="quiet-button" type="button" disabled={busy} onClick={() => router.refresh()}>{t.refresh}</button>
    <div className="public-feature-grid">
      {accounts.map((account) => <article key={`${account.userId}:${account.desiredRole}:${account.syncStatus}`}>
        <h2>{account.name}</h2><p>{t.playerName}: <strong>{account.username ?? t.noPlayerName}</strong></p>
        <p>{t.effective}: {roleLabel(account.effectiveRole)}</p><p>{t.status}: {t[account.syncStatus]}</p>
        {account.errorCode && <p><code>{account.errorCode}</code></p>}
        <form onSubmit={(event) => void save(event, account.userId)}>
          <label htmlFor={`role-${account.userId}`}>{t.desired}</label>{" "}
          <select id={`role-${account.userId}`} name="role" defaultValue={account.desiredRole} disabled={busy}>
            <option value="none">{t.none}</option><option value="member">{t.member}</option><option value="admin">{t.administrator}</option>
          </select><p><button className="quiet-button" type="submit" disabled={busy}>{t.save}</button></p>
        </form>
      </article>)}
    </div>
  </>;
}
