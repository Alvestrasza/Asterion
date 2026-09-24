import test from "node:test";
import assert from "node:assert/strict";

import {
  advanceState,
  applyCareAction,
  bondTitle,
  createInitialState,
  deriveMood,
  grantExperience,
  MAX_LEVEL,
  normalizeState,
  totalXpForLevel,
  xpRequiredForLevel
} from "../lib/care-engine.ts";

const HOUR = 60 * 60 * 1000;

test("creates a healthy initial companion", () => {
  const state = createInitialState(1_000);
  assert.equal(state.schemaVersion, 1);
  assert.equal(state.level, 1);
  assert.equal(state.sleeping, false);
  assert.equal(state.journal.length, 1);
  assert.ok(state.stats.satiety > 70);
});

test("advances awake needs by elapsed real time", () => {
  const initial = createInitialState(1_000);
  const advanced = advanceState(initial, 1_000 + HOUR);
  assert.equal(advanced.stats.satiety, 74.65);
  assert.equal(advanced.stats.energy, 81.55);
  assert.equal(advanced.stats.joy, 73.6);
});

test("sleep restores energy while needs still change gently", () => {
  const initial = createInitialState(1_000);
  initial.sleeping = true;
  initial.stats.energy = 40;
  const advanced = advanceState(initial, 1_000 + 2 * HOUR);
  assert.equal(advanced.stats.energy, 58);
  assert.equal(advanced.stats.satiety, 74.5);
});

test("feeding a full companion is refused without XP or interaction", () => {
  const initial = createInitialState(1_000);
  initial.stats.satiety = 98;
  const result = applyCareAction(initial, "feed", 1_000);
  assert.equal(result.state.stats.satiety, 98);
  assert.equal(result.state.xp, 0);
  assert.equal(result.state.interactions, 0);
  assert.equal(result.rewardCandidate, 0);
  assert.equal(result.accepted, false);
});

test("play is refused when energy is too low", () => {
  const initial = createInitialState(1_000);
  initial.stats.energy = 5;
  const result = applyCareAction(initial, "play", 1_000);
  assert.equal(result.state.interactions, 0);
  assert.equal(result.accepted, false);
  assert.match(result.message, /Schlaf/);
});

test("sleep and wake are explicit reversible actions", () => {
  let state = createInitialState(1_000);
  state = applyCareAction(state, "sleep", 1_000).state;
  assert.equal(state.sleeping, true);
  assert.equal(state.xp, 0);
  state = applyCareAction(state, "wake", 2_000).state;
  assert.equal(state.sleeping, false);
  assert.equal(state.xp, 0);
});

test("sleeping blocks feeding, playing and petting without state gains", () => {
  const sleeping = applyCareAction(createInitialState(1_000), "sleep", 1_000).state;
  for (const action of ["feed", "play", "pet"]) {
    const result = applyCareAction(sleeping, action, 1_000);
    assert.equal(result.accepted, false);
    assert.equal(result.rewardCandidate, 0);
    assert.equal(result.state.interactions, 1);
    assert.equal(result.state.level, 1);
    assert.deepEqual(result.state.stats, sleeping.stats);
  }
  assert.equal(applyCareAction(sleeping, "sleep", 1_000).accepted, false);
  assert.equal(applyCareAction(createInitialState(1_000), "wake", 1_000).accepted, false);
});

test("progression curve has a hard cap and preserves level thresholds", () => {
  assert.equal(MAX_LEVEL, 99);
  assert.equal(totalXpForLevel(5), 268);
  assert.equal(totalXpForLevel(10), 1_008);
  assert.ok(totalXpForLevel(99) > 100_000);
  assert.equal(xpRequiredForLevel(99), 0);
  const progress = { level: 98, xp: xpRequiredForLevel(98) - 1 };
  assert.equal(grantExperience(progress, 50), true);
  assert.deepEqual(progress, { level: 99, xp: 0 });
  assert.equal(grantExperience(progress, 500), false);
  assert.deepEqual(progress, { level: 99, xp: 0 });
});

test("care at full joy and bond remains expressive but gives no XP", () => {
  const full = createInitialState(1_000);
  full.stats.joy = 100;
  full.stats.bond = 100;
  for (const action of ["play", "pet"]) {
    const result = applyCareAction(full, action, 1_000);
    assert.equal(result.accepted, true);
    assert.equal(result.rewardCandidate, 0);
  }
});

test("mood priorities sleeping and urgent needs", () => {
  const state = createInitialState(1_000);
  state.sleeping = true;
  state.stats.satiety = 0;
  assert.equal(deriveMood(state), "sleeping");
  state.sleeping = false;
  assert.equal(deriveMood(state), "hungry");
});

test("normalization repairs malformed persisted values", () => {
  const state = normalizeState(
    {
      createdAt: -1e100,
      stats: { satiety: 999, energy: -4, joy: "nope" },
      level: 1e100,
      xp: 1e100,
      interactions: 1e100
    },
    2_000
  );
  assert.equal(state.stats.satiety, 100);
  assert.equal(state.stats.energy, 0);
  assert.equal(state.stats.joy, 74);
  assert.equal(state.createdAt, 0);
  assert.equal(state.level, 99);
  assert.equal(state.xp, 0);
  assert.equal(state.interactions, 2_000_000_000);
});

test("bond titles communicate progression", () => {
  assert.equal(bondTitle(0), "Neuer Gefährte");
  assert.equal(bondTitle(50), "Vertrauter");
  assert.equal(bondTitle(95), "Seelenstern");
});
