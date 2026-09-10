"use client";
import Image from "next/image";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { COMPANION_KINDS, COMPANIONS, type CompanionKind } from "@/lib/companions";
import { getMessages } from "@/lib/messages";
import { getSocialMessages } from "@/lib/social-messages";
import type { Locale } from "@/lib/i18n";
import { CompanionArt } from "./companion-art";
export function ChooseCompanion({ actorId, locale }: { actorId: string; locale: Locale }) {
  const router = useRouter();
  const t = getSocialMessages(locale);
  const companions = getMessages(locale).companions;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function choose(kind: CompanionKind) {
    if (busy) return;
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/pet/adopt", { method: "POST", headers: { "Content-Type": "application/json", "X-Asterion-Actor": actorId }, body: JSON.stringify({ kind }) });
      if (!response.ok) throw new Error();
      router.refresh();
    } catch { setError(t.error); setBusy(false); }
  }
  return <main className="social-shell"><h1>{t.choose}</h1><p>{t.chooseNote}</p>
    <p role="alert">{error}</p><div className="adoption-grid">{COMPANION_KINDS.map(kind => <article className="social-card" key={kind}>
      {kind === "asterion" ? <CompanionArt alt={companions[kind].alt} width={200} height={220} /> : <Image src={COMPANIONS[kind].stillAsset} alt={companions[kind].alt} width={200} height={220} style={{ objectFit: "contain" }} />}
      <h2>{COMPANIONS[kind].name}</h2><p>{companions[kind].species}</p>
      <button className="quiet-button" type="button" disabled={busy} onClick={() => void choose(kind)}>{busy ? t.busy : t.adopt}</button>
    </article>)}</div></main>;
}
