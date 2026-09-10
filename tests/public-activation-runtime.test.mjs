import test from "node:test";
import assert from "node:assert/strict";
import { readFile, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

// Run the actual activation tail, with OS/network boundaries replaced by fakes.
// No sudo, real service, live listener, certificate or protected file is used.
const source = (await readFile(new URL("../deploy/public/activate-public.sh", import.meta.url), "utf8")).replaceAll("\r\n", "\n");
const tail = source.slice(source.indexOf("backend_request() {"));
const linux = process.platform === "linux";

async function runActivation(scenario) {
  const fixture = await mkdtemp(join(tmpdir(), "asterion-activation-test-"));
  try {
    const harness = String.raw`
set -Eeuo pipefail
ACTIVATION_PID=$BASHPID
WORKER_MODE=--sync-worker
CANONICAL_HOST=app.example.com
ALTERNATE_HOST=alternate.example.com
TLS_SERVER_NAME=backend.example.com
TLS_CA_FILE=/unused/test-ca
TEMP_CONFIG=/unused/test-config
NGINX_FILE=/unused/test-available
NGINX_LINK=/unused/test-enabled
record() { printf '%s\n' "$*" >> "$FIXTURE/events"; }
install() { record install; }
ln() { record link; }
rm() { record remove-proxy; }
nginx() { record nginx-test; }
sleep() { :; }
systemctl() { record "systemctl $*"; }
curl() {
  local args="$*" count=0 kind=local
  [[ $args != *https://* ]] || kind=https
  if [[ $args == *redirect_url* ]]; then
    record redirect
    [[ $SCENARIO != redirect-network ]] || return 7
    if [[ $SCENARIO == wrong-redirect ]]; then printf '308 https://wrong.example.com/api/health';
    else printf '308 https://app.example.com/api/health'; fi
    return 0
  fi
  if [[ $args == *api/internal/access-sync* ]]; then
    record private-route
    if [[ $SCENARIO == private-exposed ]]; then printf 200; else printf 404; fi
    return 0
  fi
  [[ ! -f "$FIXTURE/$kind" ]] || read -r count < "$FIXTURE/$kind"
  count=$((count + 1))
  printf '%s\n' "$count" > "$FIXTURE/$kind"
  record "probe-$kind"
  if [[ $SCENARIO == local-offline && $kind == local ]]; then return 7; fi
  if [[ $SCENARIO == tls-error && $kind == https ]]; then return 60; fi
  if [[ $kind == https && ( $SCENARIO == always-wrong || ( $SCENARIO == delayed && $count -le 2 ) ) ]]; then
    printf '{"status":"ok","private_fixture":"DO_NOT_LOG_RESPONSE"}'
  elif [[ $kind == https && $SCENARIO == malformed ]]; then
    printf 'DO_NOT_LOG_RESPONSE'
  else
    printf '{"status":"healthy","database":"reachable"}'
  fi
  if [[ $args == *http_code* ]]; then
    if [[ $kind == https && $SCENARIO == redirect-health ]]; then printf '\n302'; else printf '\n200'; fi
  fi
}
`;
    const result = spawnSync("bash", ["-s"], {
      input: harness + "\n" + tail,
      env: { ...process.env, FIXTURE: fixture, SCENARIO: scenario },
      encoding: "utf8", timeout: 20000,
    });
    assert.ifError(result.error);
    const events = (await readFile(join(fixture, "events"), "utf8")).trim().split("\n");
    return { ...result, events };
  } finally {
    await rm(fixture, { recursive: true, force: true });
  }
}

test("activation tolerates a delayed HTTPS vhost without accepting the old host", { skip: !linux }, async () => {
  const result = await runActivation("delayed");
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.events.filter(e => e === "probe-https").length, 3);
  assert.equal(result.events.filter(e => e === "remove-proxy").length, 0);
  assert.ok(result.events.includes("systemctl start asterion-public-access-sync.service"));
});

for (const scenario of ["always-wrong", "malformed", "redirect-health", "tls-error", "local-offline", "redirect-network", "wrong-redirect", "private-exposed"]) {
  test(`activation fails closed and rolls back once: ${scenario}`, { skip: !linux }, async () => {
    const result = await runActivation(scenario);
    assert.notEqual(result.status, 0);
    assert.equal(result.events.filter(e => e === "remove-proxy").length, 1, result.stderr);
    assert.equal((result.stderr.match(/Public activation failed and was deactivated/g) || []).length, 1);
    assert.ok(!result.events.includes("systemctl start asterion-public-access-sync.service"));
    assert.ok(!result.events.includes("systemctl enable asterion-public.service"));
    assert.doesNotMatch(result.stdout + result.stderr, /DO_NOT_LOG_RESPONSE/);
    if (["always-wrong", "malformed", "redirect-health", "tls-error"].includes(scenario)) {
      assert.equal(result.events.filter(e => e === "probe-https").length, 20);
      assert.match(result.stderr, /HTTPS readiness failed/);
    }
    if (scenario === "local-offline") {
      assert.equal(result.events.filter(e => e === "probe-local").length, 20);
      assert.ok(!result.events.includes("probe-https"));
      assert.match(result.stderr, /Local readiness failed/);
    }
  });
}

test("immediate readiness passes all gates before enabling the worker", { skip: !linux }, async () => {
  const result = await runActivation("ready");
  assert.equal(result.status, 0, result.stderr);
  assert.ok(result.events.indexOf("private-route") < result.events.indexOf("systemctl start asterion-public-access-sync.service"));
});
