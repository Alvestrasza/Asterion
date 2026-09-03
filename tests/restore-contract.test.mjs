import test from "node:test";
import assert from "node:assert/strict";

import { applyCareAction, createInitialState, normalizeState } from "../lib/care-engine.ts";

test("legacy local saves normalize into the server state contract", () => {
  const legacy = createInitialState(1_000);
  const fed = applyCareAction(legacy, "feed", 2_000).state;
  const normalized = normalizeState(JSON.parse(JSON.stringify(fed)), 3_000);

  assert.equal(normalized.schemaVersion, 1);
  assert.equal(normalized.interactions, 1);
  assert.equal(normalized.stats.satiety, fed.stats.satiety);
});
