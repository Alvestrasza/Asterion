import test from "node:test";
import assert from "node:assert/strict";

import {
  COMPANIONS,
  COMPANION_KINDS,
  companionAnimationAsset,
  companionProfile,
  isCompanionKind
} from "../lib/companions.ts";

test("companion catalog contains four stable selectable kinds", () => {
  assert.deepEqual(COMPANION_KINDS, ["asterion", "rabbit", "cat", "orc"]);
  assert.equal(new Set(Object.values(COMPANIONS).map((entry) => entry.name)).size, 4);
});

test("unknown database values fall back to Asterion", () => {
  assert.equal(isCompanionKind("rabbit"), true);
  assert.equal(isCompanionKind("dragon"), false);
  assert.equal(companionProfile("dragon").kind, "asterion");
});

test("only Asterion selects state-specific animation files", () => {
  assert.equal(companionAnimationAsset("asterion", "jumping", false), "/assets/animations/jumping.gif");
  assert.equal(companionAnimationAsset("asterion", "jumping", true), "/assets/companions/asterion.png");
  assert.equal(companionAnimationAsset("cat", "jumping", false), "/assets/companions/cat.png");
});
