export const SCHEMA_VERSION = 1;

const HOUR_MS = 60 * 60 * 1000;
const MAX_OFFLINE_HOURS = 24 * 14;
const MAX_LEVEL = 10_000;
const MAX_XP = 1_000_000;
const MAX_INTERACTIONS = 2_000_000_000;

export type CareAction = "feed" | "play" | "pet" | "sleep" | "wake";
export type Mood = "sleeping" | "hungry" | "tired" | "lonely" | "radiant" | "attentive" | "calm";

export type CompanionState = {
  schemaVersion: number;
  createdAt: number;
  lastUpdatedAt: number;
  stats: {
    satiety: number;
    energy: number;
    joy: number;
    bond: number;
  };
  sleeping: boolean;
  level: number;
  xp: number;
  interactions: number;
  journal: Array<{ at: number; text: string }>;
};

export type CareResult = {
  state: CompanionState;
  animation: string;
  message: string;
  leveledUp: boolean;
  accepted: boolean;
};

const DEFAULT_STATS = Object.freeze({
  satiety: 76,
  energy: 82,
  joy: 74,
  bond: 24
});

export const ACTION_DETAILS = Object.freeze({
  feed: {
    animation: "review",
    label: "Füttern",
    message: "Die Sternenbeere knistert leise. Asterion wirkt sehr zufrieden."
  },
  play: {
    animation: "jumping",
    label: "Spielen",
    message: "Asterion jagt einem Lichtfunken nach und landet stolz vor dir."
  },
  pet: {
    animation: "waving",
    label: "Streicheln",
    message: "Er schmiegt den Kopf an deine Hand. Sein Sternenglanz wird wärmer."
  },
  sleep: {
    animation: "idle",
    label: "Schlafen",
    message: "Asterion rollt sich zusammen und lässt die Sterne über sich wachen."
  },
  wake: {
    animation: "waving",
    label: "Wecken",
    message: "Asterion öffnet die Augen und begrüßt dich mit einem kleinen Funkeln."
  }
});

export function clamp(value: number, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, Number.isFinite(value) ? value : minimum));
}

export function createInitialState(now = Date.now()): CompanionState {
  return {
    schemaVersion: SCHEMA_VERSION,
    createdAt: now,
    lastUpdatedAt: now,
    stats: { ...DEFAULT_STATS },
    sleeping: false,
    level: 1,
    xp: 0,
    interactions: 0,
    journal: [
      {
        at: now,
        text: "Asterion ist geschlüpft. Ein ruhiger Sternenfunke begleitet dich von nun an."
      }
    ]
  };
}

function finiteOr(value: unknown, fallback: number) {
  return Number.isFinite(Number(value)) ? Number(value) : fallback;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

export function normalizeState(candidate: unknown, now = Date.now()): CompanionState {
  if (!candidate || typeof candidate !== "object") return createInitialState(now);

  const source = asRecord(candidate);
  const createdAt = clamp(finiteOr(source.createdAt, now), 0, now);
  const lastUpdatedAt = clamp(finiteOr(source.lastUpdatedAt, now), createdAt, now);
  const sourceStats = asRecord(source.stats);
  const sourceJournal = Array.isArray(source.journal) ? source.journal : [];

  return {
    schemaVersion: SCHEMA_VERSION,
    createdAt,
    lastUpdatedAt,
    stats: {
      satiety: clamp(finiteOr(sourceStats.satiety, DEFAULT_STATS.satiety)),
      energy: clamp(finiteOr(sourceStats.energy, DEFAULT_STATS.energy)),
      joy: clamp(finiteOr(sourceStats.joy, DEFAULT_STATS.joy)),
      bond: clamp(finiteOr(sourceStats.bond, DEFAULT_STATS.bond))
    },
    sleeping: Boolean(source.sleeping),
    level: Math.floor(clamp(finiteOr(source.level, 1), 1, MAX_LEVEL)),
    xp: Math.floor(clamp(finiteOr(source.xp, 0), 0, MAX_XP)),
    interactions: Math.floor(clamp(finiteOr(source.interactions, 0), 0, MAX_INTERACTIONS)),
    journal: sourceJournal
      .map(asRecord)
      .filter((entry) => typeof entry.text === "string")
      .slice(0, 12)
      .map((entry) => ({
        at: finiteOr(entry.at, now),
        text: String(entry.text).slice(0, 240)
      }))
  };
}

export function advanceState(input: unknown, now = Date.now()) {
  const state = normalizeState(input, now);
  const elapsedHours = clamp((now - state.lastUpdatedAt) / HOUR_MS, 0, MAX_OFFLINE_HOURS);
  if (elapsedHours === 0) return state;

  if (state.sleeping) {
    state.stats.energy = clamp(state.stats.energy + 7.5 * elapsedHours);
    state.stats.satiety = clamp(state.stats.satiety - 1.3 * elapsedHours);
    state.stats.joy = clamp(state.stats.joy - 0.2 * elapsedHours);
  } else {
    state.stats.satiety = clamp(state.stats.satiety - 2.1 * elapsedHours);
    state.stats.energy = clamp(state.stats.energy - 1.15 * elapsedHours);
    state.stats.joy = clamp(state.stats.joy - 0.65 * elapsedHours);
  }

  state.lastUpdatedAt = now;
  return state;
}

export function xpRequiredForLevel(level: number) {
  return 40 + Math.max(0, level - 1) * 20;
}

function addExperience(state: CompanionState, amount: number) {
  state.xp += amount;
  let leveledUp = false;

  while (state.xp >= xpRequiredForLevel(state.level)) {
    state.xp -= xpRequiredForLevel(state.level);
    state.level += 1;
    state.stats.bond = clamp(state.stats.bond + 5);
    leveledUp = true;
  }

  return leveledUp;
}

function addJournalEntry(state: CompanionState, text: string, now: number) {
  state.journal = [{ at: now, text }, ...(state.journal ?? [])].slice(0, 10);
}

export function applyCareAction(input: unknown, action: CareAction, now = Date.now()): CareResult {
  const state = advanceState(input, now);
  let message = "Asterion beobachtet dich aufmerksam.";
  let animation = "idle";
  let xp = 0;

  if (action === "feed") {
    const before = state.stats.satiety;
    state.stats.satiety = clamp(before + (before > 90 ? 4 : 18));
    state.stats.joy = clamp(state.stats.joy + 2);
    state.stats.bond = clamp(state.stats.bond + 0.8);
    message = before > 94 ? "Asterion ist satt und bewahrt die Sternenbeere für später auf." : ACTION_DETAILS.feed.message;
    animation = ACTION_DETAILS.feed.animation;
    xp = before > 94 ? 1 : 5;
  } else if (action === "play") {
    if (state.sleeping) {
      return {
        state,
        animation: "idle",
        message: "Asterion schläft gerade tief und friedlich.",
        leveledUp: false,
        accepted: false
      };
    }
    if (state.stats.energy < 10) {
      return {
        state,
        animation: "waiting",
        message: "Asterion wäre gern dabei, braucht aber erst etwas Schlaf.",
        leveledUp: false,
        accepted: false
      };
    }
    state.stats.energy = clamp(state.stats.energy - 7);
    state.stats.satiety = clamp(state.stats.satiety - 3);
    state.stats.joy = clamp(state.stats.joy + 17);
    state.stats.bond = clamp(state.stats.bond + 2.2);
    message = ACTION_DETAILS.play.message;
    animation = ACTION_DETAILS.play.animation;
    xp = 9;
  } else if (action === "pet") {
    state.stats.joy = clamp(state.stats.joy + 9);
    state.stats.bond = clamp(state.stats.bond + 2.8);
    message = state.sleeping ? "Asterion brummt zufrieden im Schlaf." : ACTION_DETAILS.pet.message;
    animation = state.sleeping ? "idle" : ACTION_DETAILS.pet.animation;
    xp = 4;
  } else if (action === "sleep") {
    state.sleeping = true;
    message = ACTION_DETAILS.sleep.message;
    animation = ACTION_DETAILS.sleep.animation;
    xp = 2;
  } else {
    state.sleeping = false;
    message = ACTION_DETAILS.wake.message;
    animation = ACTION_DETAILS.wake.animation;
    xp = 2;
  }

  state.interactions += 1;
  const leveledUp = addExperience(state, xp);
  if (leveledUp) message += ` Eure Bindung erreicht Stufe ${state.level}.`;
  addJournalEntry(state, message, now);
  state.lastUpdatedAt = now;

  return { state, animation, message, leveledUp, accepted: true };
}

export function deriveMood(input: unknown): Mood {
  const state = normalizeState(input);
  if (state.sleeping) return "sleeping";
  if (state.stats.satiety <= 22) return "hungry";
  if (state.stats.energy <= 22) return "tired";
  if (state.stats.joy <= 22) return "lonely";

  const average = (state.stats.satiety + state.stats.energy + state.stats.joy) / 3;
  if (average >= 88 && state.stats.bond >= 55) return "radiant";
  if (average <= 48) return "attentive";
  return "calm";
}

export function moodPresentation(mood: Mood) {
  const presentations = {
    sleeping: { label: "Schläft", animation: "idle", message: "Asterion träumt zwischen stillen Sternen." },
    hungry: { label: "Hungrig", animation: "waiting", message: "Eine Sternenbeere wäre jetzt genau richtig." },
    tired: { label: "Müde", animation: "failed", message: "Asterions Flügel werden langsam schwer." },
    lonely: { label: "Sehnsüchtig", animation: "waiting", message: "Er rückt ein kleines Stück näher und wartet auf dich." },
    radiant: { label: "Strahlend", animation: "waving", message: "Asterion leuchtet heute besonders hell." },
    attentive: { label: "Aufmerksam", animation: "review", message: "Asterion beobachtet die Sterne und dich sehr genau." },
    calm: { label: "Geborgen", animation: "idle", message: "Alles ist ruhig. Asterion bleibt einfach bei dir." }
  };
  return presentations[mood];
}

export function bondTitle(value: number) {
  if (value >= 90) return "Seelenstern";
  if (value >= 70) return "Sternenbund";
  if (value >= 45) return "Vertrauter";
  if (value >= 20) return "Freund";
  return "Neuer Gefährte";
}

export function ageInDays(state: CompanionState, now = Date.now()) {
  return Math.max(1, Math.floor((now - normalizeState(state, now).createdAt) / (24 * HOUR_MS)) + 1);
}
