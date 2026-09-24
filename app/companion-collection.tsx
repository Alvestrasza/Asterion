"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { COMPANION_KINDS, companionProfile, isCompanionKind } from "@/lib/companions";
import type { Locale } from "@/lib/i18n";
import type { CompanionSummary } from "@/lib/pet-service";
import { createRequestId } from "@/lib/request-id";

export type CompanionCollectionView = { pets: CompanionSummary[]; activePetId: string | null; unlockedSlots: number; playerLevel: number };

const words = {
  de: { title: "Deine Sternenfreunde", slots: "Plätze", level: "Stufe", active: "Bei dir", choose: "Zu mir holen", adopt: "Adoptieren", confirm: "Soll dein neuer Sternenfreund dauerhaft bei dir bleiben?", locked: "Nächster Platz ab Stufe", error: "Das hat gerade nicht geklappt. Bitte versuche es erneut." },
  en: { title: "Your Starfriends", slots: "Slots", level: "Level", active: "With you", choose: "Choose", adopt: "Adopt", confirm: "Should your new Starfriend stay with you permanently?", locked: "Next slot at level", error: "That did not work. Please try again." },
  fr: { title: "Tes amis des étoiles", slots: "Places", level: "Niveau", active: "Avec toi", choose: "Choisir", adopt: "Adopter", confirm: "Ton nouvel ami des étoiles doit-il rester avec toi pour toujours ?", locked: "Prochaine place au niveau", error: "Cela n'a pas fonctionné. Réessaie." },
  es: { title: "Tus amigos estelares", slots: "Plazas", level: "Nivel", active: "Contigo", choose: "Elegir", adopt: "Adoptar", confirm: "¿Quieres que tu nuevo amigo estelar se quede contigo para siempre?", locked: "Próxima plaza en el nivel", error: "No funcionó. Inténtalo de nuevo." }
} as const;

export function CompanionCollection({ collection, userId, locale }: { collection: CompanionCollectionView; userId: string; locale: Locale }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const t = words[locale];
  const owned = new Set(collection.pets.map((pet) => pet.kind));
  const available = collection.pets.length < collection.unlockedSlots;
  const nextLevel = collection.unlockedSlots >= 5 ? null : collection.unlockedSlots * 15;

  async function send(path: string, body: object) {
    setBusy(true);
    setError("");
    try {
      const response = await fetch(path, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-Asterion-Actor": userId }, body: JSON.stringify(body) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      router.refresh();
      return true;
    } catch {
      setError(t.error);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function adopt(kind: string) {
    if (!isCompanionKind(kind)) return;
    if (!window.confirm(`${companionProfile(kind).name}: ${t.confirm}`)) return;
    const key = `asterion.adoption.v1.${userId}.${kind}`;
    let requestId: string;
    try {
      const saved = localStorage.getItem(key);
      requestId = saved && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(saved)
        ? saved : createRequestId();
      localStorage.setItem(key, requestId);
    } catch {
      setError(t.error);
      return;
    }
    if (await send("/api/pet/adopt", { kind, requestId })) localStorage.removeItem(key);
  }

  return <section className="collection-panel" aria-labelledby="collection-title">
    <div className="collection-heading"><h2 id="collection-title">{t.title}</h2><span>{collection.pets.length}/{collection.unlockedSlots} {t.slots}</span></div>
    <div className="collection-owned">
      {collection.pets.map((pet) => {
        const profile = companionProfile(pet.kind);
        const active = pet.id === collection.activePetId;
        return <button key={pet.id} type="button" className="collection-pet" data-active={active} disabled={busy || active} onClick={() => void send("/api/pet/select", { petId: pet.id })}>
          <span className="collection-art"><Image src={profile.stillAsset} alt="" fill sizes="60px" unoptimized /></span>
          <span><strong>{profile.name}</strong><small>{t.level} {pet.level} · {active ? t.active : t.choose}</small></span>
        </button>;
      })}
    </div>
    {available && <div className="collection-adopt">
      {COMPANION_KINDS.filter((kind) => !owned.has(kind)).map((kind) => {
        const profile = companionProfile(kind);
        return <button key={kind} className="collection-pet" type="button" disabled={busy} onClick={() => void adopt(kind)}>
          <span className="collection-art"><Image src={profile.stillAsset} alt="" fill sizes="60px" unoptimized /></span>
          <span><strong>{profile.name}</strong><small>{t.adopt}</small></span>
        </button>;
      })}
    </div>}
    {!available && nextLevel && <p className="collection-locked">{t.locked} {nextLevel}.</p>}
    {error && <p className="collection-error" role="alert">{error}</p>}
  </section>;
}
