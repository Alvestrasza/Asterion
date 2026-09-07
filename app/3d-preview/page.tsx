"use client";

import { useEffect, useState } from "react";
import { AsterionModel, type AsterionView } from "@/app/asterion-model";
import { COMPANIONS, COMPANION_KINDS, type CompanionKind } from "@/lib/companions";
import {
  companion3DModelAsset,
  ASTERION_REQUIRED_CLIPS,
  type AsterionClip
} from "@/lib/companion-3d";

const REVIEW_ENABLED = process.env.NEXT_PUBLIC_ASTERION_3D_ENABLED === "true";
const REVIEW_VIEWS: { view: AsterionView; label: string }[] = [
  { view: "hero", label: "Dreiviertel" },
  { view: "front", label: "Vorne" },
  { view: "side", label: "Seite" },
  { view: "rear", label: "Hinten" }
];

export default function Asterion3DPreviewPage() {
  const [kind, setKind] = useState<CompanionKind>("asterion");
  const [clip, setClip] = useState<AsterionClip>("idle");
  const [view, setView] = useState<AsterionView>("hero");
  const [viewKey, setViewKey] = useState(0);
  const [replayKey, setReplayKey] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [simulateReducedMotion, setSimulateReducedMotion] = useState(false);
  const [equipmentVisibility, setEquipmentVisibility] = useState<Partial<Record<CompanionKind, boolean>>>({});
  const armorVisible = equipmentVisibility[kind] ?? true;
  const effectiveReducedMotion = reducedMotion || simulateReducedMotion;
  const companion = COMPANIONS[kind];

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updateMotion = () => setReducedMotion(media.matches);
    updateMotion();
    media.addEventListener("change", updateMotion);
    return () => media.removeEventListener("change", updateMotion);
  }, []);

  function selectClip(nextClip: AsterionClip) {
    setClip(nextClip);
    setReplayKey((value) => value + 1);
  }

  if (!REVIEW_ENABLED) {
    return (
      <main className="model-review-shell model-review-disabled">
        <p className="eyebrow">3D ASSET REVIEW</p>
        <h1>Der 3D-Prüfstand ist deaktiviert.</h1>
        <p>Setze `NEXT_PUBLIC_ASTERION_3D_ENABLED=true` nur in einer freigegebenen Testumgebung.</p>
      </main>
    );
  }

  return (
    <main className="model-review-shell">
      <header className="model-review-copy">
        <p className="eyebrow">STERNENGEFÄHRTEN · 3D-FIGUREN</p>
        <h1>{companion.name} in Bewegung</h1>
        <p>
          Der lokale Prüfstand lädt exakt dieselbe GLB-Datei wie die Tamagotchi-Ansicht. Wähle einen Clip,
          um Rig, Silhouette und Übergang zurück in den Leerlauf zu prüfen. Ziehe das Modell zum Drehen
          oder wähle eine feste Ansicht.
        </p>
      </header>

      <section className="model-review-stage" aria-label={`Animierte ${companion.name}-Modellvorschau`}>
        <div className="model-review-aura" aria-hidden="true" />
        <AsterionModel
          key={kind}
          alt={`${companion.ariaLabel} als animierte 3D-Figur`}
          armorVisible={armorVisible}
          clip={clip}
          enabled
          fallbackSrc={companion.stillAsset}
          interactive
          modelAsset={companion3DModelAsset(kind)}
          reducedMotion={effectiveReducedMotion}
          replayKey={replayKey}
          view={view}
          viewKey={viewKey}
        />
      </section>

      <section className="model-review-controls" aria-labelledby="companionHeading">
        <div>
          <p className="eyebrow">GEFÄHRTEN</p>
          <h2 id="companionHeading">Acht eigene Persönlichkeiten</h2>
        </div>
        <div className="model-review-buttons">
          {COMPANION_KINDS.map((option) => (
            <button
              className="quiet-button"
              data-active={kind === option}
              type="button"
              aria-pressed={kind === option}
              onClick={() => {
                setKind(option);
                setClip("idle");
                setView("hero");
                setViewKey((value) => value + 1);
              }}
              key={option}
            >
              {COMPANIONS[option].name}
            </button>
          ))}
        </div>
      </section>

        <section className="model-review-controls" aria-labelledby="equipmentHeading">
          <div>
            <p className="eyebrow">AUSRÜSTUNG</p>
            <h2 id="equipmentHeading">{companion.name}: äußere Ausrüstung</h2>
          </div>
          <div className="model-review-buttons">
            {[{ visible: true, label: kind === "asterion" ? "Mit Rüstung" : "Mit Ausrüstung" },
              { visible: false, label: kind === "asterion" ? "Ohne Rüstung" : "Ohne Ausrüstung" }].map((option) => (
              <button
                className="quiet-button"
                data-active={armorVisible === option.visible}
                type="button"
                aria-pressed={armorVisible === option.visible}
                aria-describedby="equipmentNote"
                onClick={() => setEquipmentVisibility((previous) => ({ ...previous, [kind]: option.visible }))}
                key={option.label}
              >
                {option.label}
              </button>
            ))}
          </div>
          <p id="equipmentNote" className="model-review-meta">
            Nur 3D-Vorschau: Die äußere Ausrüstung ist separat schaltbar. Körper, Grundkleidung und
            ursprüngliches 2D-Bild bleiben erhalten. Die Auswahl gilt einzeln je Gefährte.
          </p>
        </section>

      <section className="model-review-controls" aria-labelledby="viewHeading">
        <div>
          <p className="eyebrow">ANSICHTEN</p>
          <h2 id="viewHeading">{companion.name} von allen Seiten</h2>
        </div>
        <div className="model-review-buttons">
          {REVIEW_VIEWS.map((option) => (
            <button
              className="quiet-button"
              data-active={view === option.view}
              type="button"
              aria-pressed={view === option.view}
              onClick={() => {
                setView(option.view);
                setViewKey((value) => value + 1);
              }}
              key={option.view}
            >
              {option.label}
            </button>
          ))}
        </div>
      </section>

      <section className="model-review-controls" aria-labelledby="animationHeading">
        <div>
          <p className="eyebrow">ANIMATIONEN</p>
          <h2 id="animationHeading">Neun stabile Clips</h2>
        </div>
        <div className="model-review-buttons">
          {ASTERION_REQUIRED_CLIPS.map((name) => (
            <button
              className="quiet-button"
              data-active={clip === name}
              type="button"
              aria-pressed={clip === name}
              onClick={() => selectClip(name)}
              key={name}
            >
              {name}
            </button>
          ))}
          <button
            className="quiet-button model-review-motion-toggle"
            data-active={effectiveReducedMotion}
            type="button"
            aria-pressed={effectiveReducedMotion}
            onClick={() => setSimulateReducedMotion((value) => !value)}
          >
            Reduced Motion
          </button>
        </div>
        <p className="model-review-meta">
          {companion.species} · Vollplastische Figur · 9 Animationen
          {effectiveReducedMotion ? " · Reduced Motion: statischer 2D-Fallback" : ""}
        </p>
      </section>
    </main>
  );
}
