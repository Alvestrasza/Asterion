export const SCHEMA_VERSION = 1;

const HOUR_MS = 60 * 60 * 1000;
const MAX_OFFLINE_HOURS = 24 * 14;
export const MAX_LEVEL = 99;
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
  rewardCandidate: number;
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
    message: (name: string) => `Die Sternenbeere knistert leise. ${name} wirkt sehr zufrieden.`
  },
  play: {
    animation: "jumping",
    label: "Spielen",
    message: (name: string) => `${name} jagt einem Lichtfunken nach und landet stolz vor dir.`
  },
  pet: {
    animation: "waving",
    label: "Streicheln",
    message: "Er schmiegt den Kopf an deine Hand. Sein Sternenglanz wird wärmer."
  },
  sleep: {
    animation: "idle",
    label: "Schlafen",
    message: (name: string) => `${name} rollt sich zusammen und lässt die Sterne über sich wachen.`
  },
  wake: {
    animation: "waving",
    label: "Wecken",
    message: (name: string) => `${name} öffnet die Augen und begrüßt dich mit einem kleinen Funkeln.`
  }
});

export function clamp(value: number, minimum = 0, maximum = 100) {
  return Math.min(maximum, Math.max(minimum, Number.isFinite(value) ? value : minimum));
}

export function createInitialState(now = Date.now(), companionName = "Asterion"): CompanionState {
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
        text: `${companionName} ist geschlüpft. Ein ruhiger Sternenfunke begleitet dich von nun an.`
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
    xp: Math.floor(clamp(finiteOr(source.level, 1) >= MAX_LEVEL ? 0 : finiteOr(source.xp, 0), 0, MAX_XP)),
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
    state.stats.energy = clamp(state.stats.energy + 9 * elapsedHours);
    state.stats.satiety = clamp(state.stats.satiety - 0.75 * elapsedHours);
    state.stats.joy = clamp(state.stats.joy - 0.1 * elapsedHours);
  } else {
    state.stats.satiety = clamp(state.stats.satiety - 1.35 * elapsedHours);
    state.stats.energy = clamp(state.stats.energy - 0.45 * elapsedHours);
    state.stats.joy = clamp(state.stats.joy - 0.4 * elapsedHours);
  }

  state.lastUpdatedAt = now;
  return state;
}

export const PROGRESSION_VERSION = 1;

export const XP_REQUIRED_V1 = Object.freeze(Array.from({ length: MAX_LEVEL - 1 }, (_, index) => {
  const level = index + 1;
  const late = Math.max(0, level - 10);
  return 40 + (level - 1) * 18 + Math.floor((late * late) / 3);
}));

export function xpRequiredForLevel(level: number) {
  if (!Number.isSafeInteger(level) || level < 1 || level >= MAX_LEVEL) return 0;
  return XP_REQUIRED_V1[level - 1];
}

export function totalXpForLevel(level: number) {
  let total = 0;
  for (let current = 1; current < Math.min(MAX_LEVEL, Math.max(1, Math.floor(level))); current += 1) {
    total += xpRequiredForLevel(current);
  }
  return total;
}

export function grantExperience(progress: { level: number; xp: number }, amount: number) {
  if (!Number.isSafeInteger(amount) || amount < 0) throw new RangeError("Invalid experience amount.");
  if (progress.level >= MAX_LEVEL) return false;
  progress.xp += amount;
  let leveledUp = false;

  while (progress.level < MAX_LEVEL && progress.xp >= xpRequiredForLevel(progress.level)) {
    progress.xp -= xpRequiredForLevel(progress.level);
    progress.level += 1;
    leveledUp = true;
  }

  if (progress.level === MAX_LEVEL) progress.xp = 0;

  return leveledUp;
}

function addJournalEntry(state: CompanionState, text: string, now: number) {
  state.journal = [{ at: now, text }, ...(state.journal ?? [])].slice(0, 10);
}

export function applyCareAction(
  input: unknown,
  action: CareAction,
  now = Date.now(),
  companionName = "Asterion"
): CareResult {
  const state = advanceState(input, now);
  let message = `${companionName} beobachtet dich aufmerksam.`;
  let animation = "idle";
  let xp = 0;

  if (action === "feed") {
    if (state.sleeping) {
      return { state, animation: "idle", message: `${companionName} schläft gerade. Die Sternenbeere wartet auf später.`, leveledUp: false, accepted: false, rewardCandidate: 0 };
    }
    const before = state.stats.satiety;
    if (before >= 95) {
      return { state, animation: "idle", message: `${companionName} ist satt und bewahrt die Sternenbeere für später auf.`, leveledUp: false, accepted: false, rewardCandidate: 0 };
    }
    state.stats.satiety = clamp(before + 22);
    state.stats.joy = clamp(state.stats.joy + 2);
    state.stats.bond = clamp(state.stats.bond + 0.8);
    message = ACTION_DETAILS.feed.message(companionName);
    animation = ACTION_DETAILS.feed.animation;
    xp = 15;
  } else if (action === "play") {
    if (state.sleeping) {
      return {
        state,
        animation: "idle",
        message: `${companionName} schläft gerade tief und friedlich.`,
        leveledUp: false,
        accepted: false,
        rewardCandidate: 0
      };
    }
    if (state.stats.energy < 10) {
      return {
        state,
        animation: "waiting",
        message: `${companionName} wäre gern dabei, braucht aber erst etwas Schlaf.`,
        leveledUp: false,
        accepted: false,
        rewardCandidate: 0
      };
    }
    const canBenefit = state.stats.joy < 100 || state.stats.bond < 100;
    state.stats.energy = clamp(state.stats.energy - 4);
    state.stats.satiety = clamp(state.stats.satiety - 2);
    state.stats.joy = clamp(state.stats.joy + 12);
    state.stats.bond = clamp(state.stats.bond + 2.2);
    message = ACTION_DETAILS.play.message(companionName);
    animation = ACTION_DETAILS.play.animation;
    xp = canBenefit ? 25 : 0;
  } else if (action === "pet") {
    if (state.sleeping) {
      return { state, animation: "idle", message: `${companionName} schläft gerade tief und friedlich.`, leveledUp: false, accepted: false, rewardCandidate: 0 };
    }
    const canBenefit = state.stats.joy < 100 || state.stats.bond < 100;
    state.stats.joy = clamp(state.stats.joy + 9);
    state.stats.bond = clamp(state.stats.bond + 2.8);
    message = ACTION_DETAILS.pet.message;
    animation = ACTION_DETAILS.pet.animation;
    xp = canBenefit ? 16 : 0;
  } else if (action === "sleep") {
    if (state.sleeping) {
      return { state, animation: "idle", message: `${companionName} schläft bereits.`, leveledUp: false, accepted: false, rewardCandidate: 0 };
    }
    state.sleeping = true;
    message = ACTION_DETAILS.sleep.message(companionName);
    animation = ACTION_DETAILS.sleep.animation;
    xp = 0;
  } else {
    if (!state.sleeping) {
      return { state, animation: "idle", message: `${companionName} ist schon wach.`, leveledUp: false, accepted: false, rewardCandidate: 0 };
    }
    state.sleeping = false;
    message = ACTION_DETAILS.wake.message(companionName);
    animation = ACTION_DETAILS.wake.animation;
    xp = 0;
  }

  state.interactions += 1;
  // Only the server may grant XP after its durable per-account reward checks.
  const leveledUp = false;
  addJournalEntry(state, message, now);
  state.lastUpdatedAt = now;

  return { state, animation, message, leveledUp, accepted: true, rewardCandidate: xp };
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

export function moodPresentation(mood: Mood, companionName = "Asterion") {
  const presentations = {
    sleeping: { label: "Schläft", animation: "idle", message: `${companionName} träumt zwischen stillen Sternen.` },
    hungry: { label: "Hungrig", animation: "waiting", message: "Eine Sternenbeere wäre jetzt genau richtig." },
    tired: { label: "Müde", animation: "failed", message: `${companionName} braucht langsam eine Pause.` },
    lonely: { label: "Sehnsüchtig", animation: "waiting", message: "Er rückt ein kleines Stück näher und wartet auf dich." },
    radiant: { label: "Strahlend", animation: "waving", message: `${companionName} leuchtet heute besonders hell.` },
    attentive: { label: "Aufmerksam", animation: "review", message: `${companionName} beobachtet die Sterne und dich sehr genau.` },
    calm: { label: "Geborgen", animation: "idle", message: `Alles ist ruhig. ${companionName} bleibt einfach bei dir.` }
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
