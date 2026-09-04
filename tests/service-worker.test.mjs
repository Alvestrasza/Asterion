import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const packageJson = JSON.parse(
  await readFile(new URL("../package.json", import.meta.url), "utf8")
);
const serviceWorker = await readFile(
  new URL("../public/sw.js", import.meta.url),
  "utf8"
);

test("service-worker cache follows the application version", () => {
  assert.match(
    serviceWorker,
    new RegExp(`const CACHE_NAME = "asterion-static-v${packageJson.version.replaceAll(".", "\\.")}";`)
  );
});
