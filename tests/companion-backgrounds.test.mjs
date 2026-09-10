import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { COMPANION_KINDS } from "../lib/companions.ts";
import { COMPANION_BACKGROUNDS } from "../lib/companion-backgrounds.ts";

test("every selectable companion has its own approved, versioned background", async () => {
  assert.deepEqual(Object.keys(COMPANION_BACKGROUNDS).sort(), [...COMPANION_KINDS].sort());
  assert.equal(new Set(Object.values(COMPANION_BACKGROUNDS)).size, 8);

  for (const kind of COMPANION_KINDS) {
    const asset = COMPANION_BACKGROUNDS[kind];
    assert.equal(asset, `/assets/backgrounds/${kind}-background-v1.png`);
    const bytes = await readFile(new URL(`../public${asset}`, import.meta.url));
    assert.deepEqual([...bytes.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
    assert.equal(bytes.readUInt32BE(16), 1672);
    assert.equal(bytes.readUInt32BE(20), 941);
  }
});
