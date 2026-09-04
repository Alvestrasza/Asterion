import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const config = await readFile(
  new URL("../deploy/internal/asterion-internal.nginx.conf", import.meta.url),
  "utf8"
);

test("internal proxy preserves the browser-visible host and port", () => {
  assert.match(config, /proxy_set_header Host \$http_host;/);
  assert.match(config, /proxy_set_header X-Forwarded-Host \$http_host;/);
  assert.doesNotMatch(config, /proxy_set_header (?:Host|X-Forwarded-Host) \$host;/);
});
