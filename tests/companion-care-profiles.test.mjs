import test from "node:test";
import assert from "node:assert/strict";

import { advanceState, applyCareAction, createInitialState } from "../lib/care-engine.ts";
import { COMPANION_KINDS } from "../lib/companions.ts";

const HOUR = 60 * 60 * 1000;

test("the eight companions have distinct, gentle offline need patterns", () => {
  const initial = createInitialState(1_000);
  const states = COMPANION_KINDS.map((kind) => advanceState(initial, 1_000 + 6 * HOUR, kind));
  const signatures = states.map(({ stats }) => [stats.satiety, stats.energy, stats.joy].join(":"));
  assert.equal(new Set(signatures).size, COMPANION_KINDS.length);
  assert.ok(states.every(({ stats }) => stats.satiety >= 60 && stats.energy >= 70 && stats.joy >= 60));
  assert.ok(states[COMPANION_KINDS.indexOf("rabbit")].stats.satiety < states[COMPANION_KINDS.indexOf("elf")].stats.satiety);
  assert.deepEqual(advanceState(initial, 1_000 + 6 * HOUR, "cat"), states[COMPANION_KINDS.indexOf("cat")]);
  assert.equal(initial.stats.satiety, 76, "advancing one companion must not mutate another snapshot");
});

test("preferences change meaningful care response without changing XP rewards", () => {
  const initial = createInitialState(1_000);
  const fenn = applyCareAction(initial, "pet", 1_000, "Fenn", "dog");
  const nyra = applyCareAction(initial, "pet", 1_000, "Nyra", "cat");
  assert.ok(fenn.state.stats.bond > nyra.state.stats.bond);
  assert.equal(fenn.rewardCandidate, nyra.rewardCandidate);
  const caelo = applyCareAction(initial, "play", 1_000, "Caelo", "pony");
  const asterion = applyCareAction(initial, "play", 1_000, "Asterion", "asterion");
  assert.ok(caelo.state.stats.joy > asterion.state.stats.joy);
  assert.equal(caelo.rewardCandidate, asterion.rewardCandidate);
});

test("long offline periods remain bounded and do not cause irreversible harm", () => {
  for (const kind of COMPANION_KINDS) {
    const initial = createInitialState(1_000);
    const later = advanceState(initial, 1_000 + 90 * 24 * HOUR, kind);
    assert.ok(Object.values(later.stats).every((value) => value >= 0 && value <= 100), kind);
    assert.equal(later.level, 1);
    assert.equal(later.sleeping, false);
    const fed = applyCareAction(later, "feed", later.lastUpdatedAt, kind, kind);
    assert.equal(fed.accepted, true, kind);
  }
});
