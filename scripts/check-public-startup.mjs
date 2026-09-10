// Exercise the compiled artifact, not the source helper. No database or provider is contacted.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const server = resolve(process.argv[2] ?? ".next/standalone/start-asterion.mjs");
const environment = { ...process.env };
for (const key of Object.keys(environment)) {
  if (/^(AUTH_|NEXTAUTH_|ASTERION_)/.test(key)) delete environment[key];
}
Object.assign(environment, {
  NODE_ENV: "production", HOSTNAME: "127.0.0.1", PORT: "39889",
  DATABASE_URL: "postgresql://preview:preview@127.0.0.1:1/preview",
  ASTERION_DEPLOYMENT_MODE: "public", ASTERION_INTERNAL_TEST_MODE: "true"
});
const result = spawnSync(process.execPath, [server], { encoding: "utf8", timeout: 15_000, env: environment });
assert.equal(result.error, undefined, "The guard must exit, not merely time out");
assert.notEqual(result.status, 0);
assert.match(result.stdout + result.stderr, /Public deployment configuration rejected/);
console.log("PASS compiled artifact refuses unsafe public shared-user configuration at startup");
