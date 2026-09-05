import test from "node:test";
import assert from "node:assert/strict";
import { formatJournalTime } from "../lib/journal-time.ts";

test("the initial journal label is deterministic before the browser timezone is known", () => {
  const at = Date.parse("2026-09-05T14:18:34.063Z");
  const previous = process.env.TZ;
  try {
    process.env.TZ = "Pacific/Honolulu";
    const server = formatJournalTime(at);
    process.env.TZ = "Europe/Berlin";
    assert.equal(formatJournalTime(at), server);
    assert.equal(server, "2026-09-05 14:18 UTC");
  } finally {
    if (previous === undefined) delete process.env.TZ;
    else process.env.TZ = previous;
  }
});

test("hydrated journal labels use the explicit browser timezone including daylight saving", () => {
  assert.match(formatJournalTime(Date.parse("2026-09-05T14:18:34Z"), "Europe/Berlin"), /16:18$/);
  assert.match(formatJournalTime(Date.parse("2026-01-05T14:18:34Z"), "Europe/Berlin"), /15:18$/);
  assert.match(formatJournalTime(Date.parse("2026-09-05T14:18:34Z"), "UTC"), /14:18$/);
});
