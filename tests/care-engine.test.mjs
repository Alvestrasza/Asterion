import test from "node:test";
import assert from "node:assert/strict";

import {
  advanceState,
  applyCareAction,
  bondTitle,
  createInitialState,
  deriveMood,
  normalizeState,
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
  assert.equal(advanced.stats.satiety, 73.9);
  assert.equal(advanced.stats.energy, 80.85);
  assert.equal(advanced.stats.joy, 73.35);
});

test("sleep restores energy while needs still change gently", () => {
  const initial = createInitialState(1_000);
  initial.sleeping = true;
  initial.stats.energy = 40;
  const advanced = advanceState(initial, 1_000 + 2 * HOUR);
  assert.equal(advanced.stats.energy, 55);
  assert.equal(advanced.stats.satiety, 73.4);
});

test("feeding clamps satiety and avoids over-rewarding a full companion", () => {
  const initial = createInitialState(1_000);
  initial.stats.satiety = 98;
  const result = applyCareAction(initial, "feed", 1_000);
  assert.equal(result.state.stats.satiety, 100);
  assert.equal(result.state.xp, 1);
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
  state = applyCareAction(state, "wake", 2_000).state;
  assert.equal(state.sleeping, false);
});

test("care actions level the bond without unbounded stats", () => {
  let state = createInitialState(1_000);
  for (let index = 0; index < 10; index += 1) {
    state = applyCareAction(state, "pet", 1_000 + index).state;
  }
  assert.equal(state.level, 2);
  assert.equal(state.xp, 0);
  assert.equal(state.stats.joy, 100);
  assert.equal(xpRequiredForLevel(state.level), 60);
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
  assert.equal(state.level, 10_000);
  assert.equal(state.xp, 1_000_000);
  assert.equal(state.interactions, 2_000_000_000);
});

test("bond titles communicate progression", () => {
  assert.equal(bondTitle(0), "Neuer Gefährte");
  assert.equal(bondTitle(50), "Vertrauter");
  assert.equal(bondTitle(95), "Seelenstern");
});
