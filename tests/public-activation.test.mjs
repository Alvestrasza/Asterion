import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("activation verifies IPv4 HTTPS identity, readiness, redirect and the private route", async () => {
  const source = await readFile(new URL("../deploy/public/activate-public.sh", import.meta.url), "utf8");
  assert.match(source, /--backend-tls-server-name/);
  assert.match(source, /--backend-tls-ca-file/);
  assert.match(source, /curl -4 --noproxy/);
  assert.match(source, /--cacert "\$\{TLS_CA_FILE\}" --resolve "\$\{TLS_SERVER_NAME\}:443:127\.0\.0\.1"/);
  assert.match(source, /-H "Host: \$\{CANONICAL_HOST\}"/);
  assert.match(source, /308 https:\/\/\$\{CANONICAL_HOST\}\/api\/health/);
  assert.match(source, /\[\[ \$\{PRIVATE_STATUS\} == 404 \]\]/);
  assert.match(source, /JSON\.parse\(body\)/);
  assert.doesNotMatch(source, /8089|--insecure|curl[^\n]*\s-k(?:\s|$)/);
  assert.doesNotMatch(source, /systemctl .*asterion-internal|prisma migrate/);
  assert.ok(source.indexOf("flock -n 9") < source.indexOf("CURRENT_DIR=$(readlink"));
});

test("stopped candidate refresh preserves prior state and refuses active or mismatched installations", async () => {
  const source = await readFile(new URL("../deploy/public/refresh-prepared-public.sh", import.meta.url), "utf8");
  assert.match(source, /\$# -ne 3/);
  assert.match(source, /readlink -f -- "\$\{SITE_ROOT\}\/current"\) == "\$\{EXPECTED_DIR\}"/);
  assert.match(source, /\$\{state\} == inactive/);
  assert.match(source, /\$\{enabled\} == disabled \|\| \$\{enabled\} == static/);
  assert.match(source, /sites-enabled\/asterion-public\.conf/);
  assert.match(source, /cmp -s -- "\$\{SCRIPT_DIR\}\/\$\{unit\}"/);
  assert.match(source, /cmp -s -- "\$\{SCRIPT_DIR\}\/public-config\.mjs"/);
  assert.match(source, /resolved.*==.*ARTIFACT_DIR/);
  assert.match(source, /readlink -- "\$\{link\}"\) != \/\*/);
  assert.match(source, /realpath -e -- "\$\{link\}"\) == "\$\{RELEASE_DIR\}\/"\*/);
  assert.ok(source.indexOf("The copied artifact contains a link") < source.indexOf("chown -R root:root"));
  assert.match(source, /mv -Tf -- "\$\{NEXT_LINK\}" "\$\{SITE_ROOT\}\/current"/);
  assert.doesNotMatch(source, /systemctl (?:enable|start|restart|stop)|prisma migrate|rm -rf|cp .*ENV_FILE|install .*ENV_FILE/);
  assert.ok(source.indexOf("${state} == inactive") < source.indexOf('cp -a -- "${ARTIFACT_DIR}/."'));
});
