"use client";

import Image from "next/image";
import { useCallback, useEffect, useRef, useState } from "react";
import { logout } from "@/app/actions";
import {
  ageInDays,
  applyCareAction,
  bondTitle,
  deriveMood,
  moodPresentation,
  xpRequiredForLevel,
  type CareAction
} from "@/lib/care-engine";
import {
  COMPANIONS,
  companionAnimationAsset,
  companionProfile,
  type CompanionKind
} from "@/lib/companions";
import type { PetCommand, PetCommandResponse, PetSnapshot } from "@/lib/pet-contract";
import { createRequestId } from "@/lib/request-id";
import { formatJournalTime } from "@/lib/journal-time";

type PendingCare = {
  requestId: string;
  action: CareAction;
  queuedAt: number;
};

type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

class CommandError extends Error {
  constructor(readonly status: number) {
    super(`Asterion command failed with status ${status}`);
  }
}

async function postCommand(command: PetCommand): Promise<PetCommandResponse> {
  const response = await fetch("/api/pet/actions", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(command)
  });

  if (!response.ok) throw new CommandError(response.status);
  return response.json() as Promise<PetCommandResponse>;
}

function readQueue(key: string): PendingCare[] {
  try {
    const value = JSON.parse(localStorage.getItem(key) ?? "[]") as unknown;
    if (!Array.isArray(value)) return [];
    return value.filter(
      (entry): entry is PendingCare =>
        Boolean(entry) &&
        typeof entry.requestId === "string" &&
        ["feed", "play", "pet", "sleep", "wake"].includes(entry.action) &&
        typeof entry.queuedAt === "number"
    );
  } catch {
    return [];
  }
}

function writeQueue(key: string, queue: PendingCare[]) {
  try {
    localStorage.setItem(key, JSON.stringify(queue));
    return true;
  } catch {
    // Private browsing or a full quota must not break an in-progress care action.
    return false;
  }
}

function Stat({
  name,
  label,
  glyph,
  value
}: {
  name: "satiety" | "energy" | "joy" | "bond";
  label: string;
  glyph: string;
  value: number;
}) {
  const rounded = Math.round(value);
  return (
    <div className="stat" data-stat={name}>
      <div className="stat-label">
        <span className={`stat-icon ${name}-icon`} aria-hidden="true">{glyph}</span>
        <span>{label}</span>
        <strong>{rounded}%</strong>
      </div>
      <div
        className="meter"
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={rounded}
      >
        <span style={{ width: `${rounded}%` }} />
      </div>
    </div>
  );
}

export function AsterionClient({
  initialPet,
  userId,
  userName,
  internalTestMode
}: {
  initialPet: PetSnapshot;
  userId: string;
  userName: string;
  internalTestMode: boolean;
}) {
  const [pet, setPet] = useState(initialPet);
  const initialMood = moodPresentation(deriveMood(initialPet), companionProfile(initialPet.kind).name);
  const [message, setMessage] = useState(initialMood.message);
  const [animation, setAnimation] = useState(initialMood.animation);
  const [animationKey, setAnimationKey] = useState(0);
  const [busy, setBusy] = useState(false);
  const [online, setOnline] = useState(true);
  const [queueCount, setQueueCount] = useState(0);
  const [toast, setToast] = useState("");
  const [installPrompt, setInstallPrompt] = useState<InstallPromptEvent | null>(null);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [timeZone, setTimeZone] = useState<string>();
  const settingsDialog = useRef<HTMLDialogElement>(null);
  const confirmDialog = useRef<HTMLDialogElement>(null);
  const transientTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const queueKey = `asterion.pending-actions.v1.${userId}`;

  const showToast = useCallback((copy: string) => {
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast(copy);
    toastTimer.current = setTimeout(() => setToast(""), 2_800);
  }, []);

  const showTransient = useCallback((nextPet: PetSnapshot, nextAnimation: string, nextMessage: string) => {
    if (transientTimer.current) clearTimeout(transientTimer.current);
    setAnimation(nextAnimation);
    setMessage(nextMessage);
    setAnimationKey((value) => value + 1);
    transientTimer.current = setTimeout(() => {
      const presentation = moodPresentation(deriveMood(nextPet), companionProfile(nextPet.kind).name);
      setAnimation(presentation.animation);
      setMessage(presentation.message);
    }, 3_400);
  }, []);

  const flushQueue = useCallback(async () => {
    const pending = readQueue(queueKey);
    if (pending.length === 0 || !navigator.onLine) return;

    setBusy(true);
    let remaining = [...pending];
    try {
      while (remaining.length > 0) {
        const command = remaining[0];
        const result = await postCommand({ requestId: command.requestId, action: command.action });
        setPet(result.pet);
        showTransient(result.pet, result.feedback.animation, result.feedback.message);
        remaining = remaining.slice(1);
        writeQueue(queueKey, remaining);
        setQueueCount(remaining.length);
      }
      showToast("Alle vorgemerkten Augenblicke wurden synchronisiert.");
    } catch (error) {
      if (error instanceof CommandError && error.status === 401) window.location.assign("/login");
    } finally {
      setBusy(false);
    }
  }, [queueKey, showToast, showTransient]);

  useEffect(() => {
    setTimeZone(Intl.DateTimeFormat().resolvedOptions().timeZone);
    setOnline(navigator.onLine);
    setQueueCount(readQueue(queueKey).length);

    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const updateMotion = () => setReducedMotion(media.matches);
    updateMotion();
    media.addEventListener("change", updateMotion);

    const updatePhase = () => {
      const hour = new Date().getHours();
      document.body.dataset.phase = hour >= 7 && hour < 19 ? "day" : "night";
    };
    updatePhase();

    const handleOnline = () => {
      setOnline(true);
      void flushQueue();
    };
    const handleOffline = () => setOnline(false);
    const handleInstall = (event: Event) => {
      event.preventDefault();
      setInstallPrompt(event as InstallPromptEvent);
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    window.addEventListener("beforeinstallprompt", handleInstall);
    if ("serviceWorker" in navigator) void navigator.serviceWorker.register("/sw.js");
    if (navigator.onLine) void flushQueue();

    return () => {
      media.removeEventListener("change", updateMotion);
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("beforeinstallprompt", handleInstall);
      if (transientTimer.current) clearTimeout(transientTimer.current);
      if (toastTimer.current) clearTimeout(toastTimer.current);
    };
  }, [flushQueue, queueKey]);

  function requestIdOrNotify() {
    try {
      return createRequestId();
    } catch {
      showToast("Dein Browser unterstützt keine sicheren Aktions-IDs. Bitte verwende einen aktuellen Browser.");
      return null;
    }
  }

  async function handleCare(action: CareAction) {
    if (busy) return;
    const requestId = requestIdOrNotify();
    if (!requestId) return;
    const command = { requestId, action } satisfies PetCommand;

    if (navigator.onLine) {
      setBusy(true);
      try {
        const result = await postCommand(command);
        setPet(result.pet);
        showTransient(result.pet, result.feedback.animation, result.feedback.message);
        return;
      } catch (error) {
        if (error instanceof CommandError && error.status < 500) {
          if (error.status === 401) window.location.assign("/login");
          else showToast("Diese Aktion konnte nicht angenommen werden.");
          return;
        }
      } finally {
        setBusy(false);
      }
    }

    const queue = [...readQueue(queueKey), { requestId, action, queuedAt: Date.now() }];
    if (!writeQueue(queueKey, queue)) {
      showToast("Der Offline-Augenblick konnte auf diesem Gerät nicht vorgemerkt werden.");
      return;
    }
    setQueueCount(queue.length);
    setOnline(false);

    const optimistic = applyCareAction(pet, action, Date.now());
    const optimisticPet: PetSnapshot = {
      ...pet,
      ...optimistic.state,
      journal: [
        { id: `pending:${requestId}`, at: Date.now(), text: optimistic.message, action },
        ...pet.journal
      ].slice(0, 10)
    };
    setPet(optimisticPet);
    showTransient(optimisticPet, optimistic.animation, `${optimistic.message} Wird synchronisiert, sobald du wieder online bist.`);
  }

  async function runImmediate(command: PetCommand, successMessage: string) {
    if (busy || !navigator.onLine) {
      showToast("Dafür braucht dein Begleiter gerade eine Verbindung.");
      return;
    }

    setBusy(true);
    try {
      const result = await postCommand(command);
      setPet(result.pet);
      showTransient(result.pet, result.feedback.animation, result.feedback.message);
      showToast(successMessage);
    } catch (error) {
      if (error instanceof CommandError && error.status === 401) window.location.assign("/login");
      else showToast("Die gemeinsame Chronik konnte nicht aktualisiert werden.");
    } finally {
      setBusy(false);
    }
  }

  function exportSave() {
    const payload = new Blob(
      [`${JSON.stringify({ format: "asterion-save-v2", exportedAt: new Date().toISOString(), pet }, null, 2)}\n`],
      { type: "application/json" }
    );
    const url = URL.createObjectURL(payload);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${pet.kind}-erinnerung-${new Date().toISOString().slice(0, 10)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    showToast(`${companionProfile(pet.kind).name}s Erinnerung wurde gesichert.`);
  }

  async function importSave(event: React.ChangeEvent<HTMLInputElement>) {
    const [file] = Array.from(event.currentTarget.files ?? []);
    event.currentTarget.value = "";
    if (!file) return;

    try {
      const parsed = JSON.parse(await file.text()) as { pet?: unknown };
      const requestId = requestIdOrNotify();
      if (!requestId) return;
      await runImmediate(
        { requestId, action: "restore", state: parsed.pet ?? parsed },
        "Die Erinnerung deines Begleiters wurde wiederhergestellt."
      );
      settingsDialog.current?.close();
    } catch {
      showToast("Diese Datei enthält keine gültige Begleiter-Erinnerung.");
    }
  }

  async function resetPet() {
    const name = companionProfile(pet.kind).name;
    const requestId = requestIdOrNotify();
    if (!requestId) return;
    await runImmediate(
      { requestId, action: "reset" },
      `${name} beginnt eine neue Chronik.`
    );
    confirmDialog.current?.close();
    settingsDialog.current?.close();
  }

  async function selectCompanion(kind: CompanionKind) {
    if (kind === pet.kind) return;
    const selected = COMPANIONS[kind];
    const requestId = requestIdOrNotify();
    if (!requestId) return;
    await runImmediate(
      { requestId, action: "select", kind },
      `${selected.name} begleitet dich jetzt.`
    );
  }

  const companion = companionProfile(pet.kind);
  const mood = moodPresentation(deriveMood(pet), companion.name);
  const requiredXp = xpRequiredForLevel(pet.level);
  const xpPercent = Math.min(100, (pet.xp / requiredXp) * 100);
  const spriteSource = companionAnimationAsset(companion.kind, animation, reducedMotion);
  const syncLabel = busy
    ? "Wird gespeichert …"
    : !online
      ? `Offline · ${queueCount} vorgemerkt`
      : queueCount > 0
        ? `${queueCount} wartet auf Synchronisierung`
        : "Server synchronisiert";

  return (
    <>
      <div className="sky" aria-hidden="true">
        {Array.from({ length: 6 }, (_, index) => <span className={`star star-${String.fromCharCode(97 + index)}`} key={index} />)}
      </div>

      <div className="app-shell">
        <header className="topbar">
          <a className="brand" href="#companion" aria-label="Zum Begleiter springen">
            <span className="brand-mark" aria-hidden="true">✦</span>
            <span><strong>ASTERION</strong><small>STERNENBEGLEITER</small></span>
          </a>
          <div className="topbar-actions">
            <span className="user-chip" title={userName}>{userName}</span>
            {installPrompt ? (
              <button
                className="quiet-button"
                type="button"
                onClick={async () => {
                  await installPrompt.prompt();
                  await installPrompt.userChoice;
                  setInstallPrompt(null);
                }}
              >
                <span aria-hidden="true">↓</span> App installieren
              </button>
            ) : null}
            <button className="icon-button" type="button" aria-label="Einstellungen öffnen" onClick={() => settingsDialog.current?.showModal()}>⚙</button>
            {internalTestMode ? null : (
              <form action={logout}><button className="icon-button" type="submit" aria-label="Abmelden">↪</button></form>
            )}
          </div>
        </header>

        {internalTestMode ? (
          <aside className="test-mode-banner" role="status">
            <strong>Interner Testmodus</strong>
            <span>Alle Tester auf diesem Dienst teilen momentan denselben Spielstand. Vor einer externen Freigabe wird dieser Modus abgeschaltet.</span>
          </aside>
        ) : null}

        <main>
          <section className="hero" id="companion" aria-labelledby="pageTitle">
            <div className="hero-copy">
              <p className="eyebrow">{companion.tagline.toUpperCase()}</p>
              <h1 id="pageTitle">{companion.introduction}</h1>
              <p className="hero-intro">
                Kümmere dich um {companion.name}, sammle gemeinsame Augenblicke und lass eure Bindung wachsen.
                Eure Chronik folgt dir sicher von Gerät zu Gerät.
              </p>
              <div className="identity-strip" aria-label={`${companion.name}s Entwicklung`}>
                <div><span>TAG</span><strong>{ageInDays(pet, pet.lastUpdatedAt)}</strong></div>
                <div><span>STUFE</span><strong>{pet.level}</strong></div>
                <div className="bond-identity"><span>BINDUNG</span><strong>{bondTitle(pet.stats.bond)}</strong></div>
              </div>
            </div>

            <div className="companion-column">
              <div className="speech-bubble" role="status" aria-live="polite">{message}</div>
              <div className="pet-stage">
                <div className="orbit orbit-outer" aria-hidden="true" />
                <div className="orbit orbit-inner" aria-hidden="true" />
                <div className="moon-glow" aria-hidden="true" />
                <div key={animationKey} className={`pet-visual reacting reaction-${animation}`}>
                  <Image
                    src={spriteSource}
                    alt={companion.ariaLabel}
                    fill
                    sizes="(max-width: 590px) 290px, 330px"
                    priority
                    unoptimized
                  />
                </div>
              </div>
              <div className="mood-chip"><span className="mood-dot" aria-hidden="true" /><span>{mood.label}</span></div>
            </div>
          </section>

          <section className="care-grid" aria-label={`${companion.name} versorgen`}>
            <article className="panel status-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">WOHLBEFINDEN</p><h2>Wie es {companion.name} geht</h2></div>
                <span className={`saved-state${online ? "" : " offline"}`}>{syncLabel}</span>
              </div>
              <div className="stats-list">
                <Stat name="satiety" label="Sättigung" glyph="●" value={pet.stats.satiety} />
                <Stat name="energy" label="Energie" glyph="ϟ" value={pet.stats.energy} />
                <Stat name="joy" label="Freude" glyph="✦" value={pet.stats.joy} />
                <Stat name="bond" label="Bindung" glyph="∞" value={pet.stats.bond} />
              </div>
              <div className="xp-block">
                <div className="xp-copy"><span>Nächste Bindungsstufe</span><strong>{pet.xp} / {requiredXp} XP</strong></div>
                <div className="xp-meter" aria-hidden="true"><span style={{ width: `${xpPercent}%` }} /></div>
              </div>
            </article>

            <article className="panel actions-panel">
              <div className="panel-heading"><div><p className="eyebrow">GEMEINSAME ZEIT</p><h2>Was möchtest du tun?</h2></div></div>
              <div className="action-grid">
                <button className="care-action feed-action" disabled={busy} type="button" onClick={() => void handleCare("feed")}>
                  <span className="action-glyph" aria-hidden="true">●</span><span><strong>Füttern</strong><small>Eine Sternenbeere</small></span>
                </button>
                <button className="care-action play-action" disabled={busy} type="button" onClick={() => void handleCare("play")}>
                  <span className="action-glyph" aria-hidden="true">✦</span><span><strong>Spielen</strong><small>Einem Lichtfunken folgen</small></span>
                </button>
                <button className="care-action pet-action" disabled={busy} type="button" onClick={() => void handleCare("pet")}>
                  <span className="action-glyph" aria-hidden="true">♡</span><span><strong>Streicheln</strong><small>Einen ruhigen Moment teilen</small></span>
                </button>
                <button className="care-action sleep-action" disabled={busy} type="button" onClick={() => void handleCare(pet.sleeping ? "wake" : "sleep")}>
                  <span className="action-glyph" aria-hidden="true">☾</span><span><strong>{pet.sleeping ? "Wecken" : "Schlafen"}</strong><small>{pet.sleeping ? "Sanft ins Heute zurückholen" : "Unter Sternen ausruhen"}</small></span>
                </button>
              </div>
            </article>

            <article className="panel journal-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">STERNENCHRONIK</p><h2>Eure letzten Augenblicke</h2></div>
                <span className="journal-count">{pet.interactions} {pet.interactions === 1 ? "Begegnung" : "Begegnungen"}</span>
              </div>
              <ol className="journal-list">
                {pet.journal.slice(0, 3).map((entry) => (
                  <li className="journal-entry" key={entry.id}>
                    <time dateTime={new Date(entry.at).toISOString()}>
                      {formatJournalTime(entry.at, timeZone)}
                    </time>
                    <p>{entry.text}</p>
                  </li>
                ))}
              </ol>
            </article>
          </section>
        </main>

        <footer><span>ASTERION · SERVER FIRST</span><span>Ein Konto. Ein Begleiter. Eine Chronik auf all deinen Geräten.</span></footer>
      </div>

      <dialog className="settings-dialog" ref={settingsDialog} aria-labelledby="settingsTitle">
        <form method="dialog">
          <div className="dialog-heading">
            <div><p className="eyebrow">EINSTELLUNGEN</p><h2 id="settingsTitle">Dein Sternengefährte</h2></div>
            <button className="icon-button" value="close" aria-label="Einstellungen schließen">×</button>
          </div>
          <p className="dialog-copy">Der Zustand deines Begleiters liegt geschützt in deinem Konto und wird zwischen deinen Geräten synchronisiert.</p>
          <fieldset className="companion-picker">
            <legend>Begleiter wählen</legend>
            <p>Beim Wechsel bleiben Werte, Stufe und Chronik erhalten.</p>
            <div className="companion-options">
              {Object.values(COMPANIONS).map((option) => (
                <button
                  className="companion-option"
                  data-selected={option.kind === pet.kind}
                  type="button"
                  aria-pressed={option.kind === pet.kind}
                  disabled={busy || !online}
                  key={option.kind}
                  onClick={() => void selectCompanion(option.kind)}
                >
                  <span className="companion-option-image">
                    <Image src={option.stillAsset} alt="" fill sizes="72px" unoptimized />
                  </span>
                  <span><strong>{option.name}</strong><small>{option.species}</small></span>
                </button>
              ))}
            </div>
          </fieldset>
          <div className="settings-actions">
            <button className="settings-action" type="button" onClick={exportSave}><strong>Erinnerung sichern</strong><small>Spielstand als JSON herunterladen</small></button>
            <label className="settings-action import-label" htmlFor="importInput"><strong>Erinnerung wiederherstellen</strong><small>Einen lokalen oder früheren Spielstand übernehmen</small></label>
            <input id="importInput" type="file" accept="application/json,.json" hidden onChange={(event) => void importSave(event)} />
            <button className="settings-action danger-action" type="button" onClick={() => confirmDialog.current?.showModal()}><strong>Neu beginnen</strong><small>Die serverseitige Chronik nach Bestätigung zurücksetzen</small></button>
          </div>
        </form>
      </dialog>

      <dialog className="confirm-dialog" ref={confirmDialog} aria-labelledby="confirmTitle">
        <span className="confirm-mark" aria-hidden="true">✦</span>
        <h2 id="confirmTitle">Wirklich neu beginnen?</h2>
        <p>Damit werden die Werte und die bisherige Sternenchronik deines Begleiters in deinem Konto zurückgesetzt.</p>
        <div className="confirm-actions">
          <button className="quiet-button" type="button" onClick={() => confirmDialog.current?.close()}>Abbrechen</button>
          <button className="danger-button" type="button" disabled={busy} onClick={() => void resetPet()}>Neu beginnen</button>
        </div>
      </dialog>

      <div className={`toast${toast ? " visible" : ""}`} role="status" aria-live="polite">{toast}</div>
    </>
  );
}
