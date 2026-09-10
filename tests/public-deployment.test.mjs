import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { inspectPublicEnvironment, renderPublicNginx } from "../deploy/public/public-config.mjs";
import { requestAccessSynchronization } from "../deploy/public/run-access-sync.mjs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const valid = () => ({
  NODE_ENV: "production", ASTERION_DEPLOYMENT_MODE: "public", ASTERION_INTERNAL_TEST_MODE: "false",
  HOSTNAME: "127.0.0.1", PORT: "3012", AUTH_TRUST_HOST: "true",
  AUTH_URL: "https://companions.test", ASTERION_ALTERNATE_ORIGIN: "https://alternate.test",
  ASTERION_TRUSTED_PROXY_IPS: "192.0.2.11,192.0.2.12",
  ASTERION_BACKEND_TLS_CERT_FILE: "/etc/nginx/tls/fixture/server.crt",
  ASTERION_BACKEND_TLS_KEY_FILE: "/etc/nginx/tls/fixture/server.key",
  ASTERION_BACKEND_TLS_CA_FILE: "/etc/ssl/certs/fixture-ca.pem",
  ASTERION_BACKEND_TLS_SERVER_NAME: "backend-node.test",
  AUTH_KEYCLOAK_ISSUER: "https://identity.test/realms/test-fixture",
  ASTERION_KEYCLOAK_ADMIN_ORIGIN: "https://identity-admin.test",
  AUTH_KEYCLOAK_ID: "public-test", AUTH_KEYCLOAK_SECRET: "oidc-test-fixture",
  AUTH_SECRET: "randomness-is-an-owner-duty-not-a-fixture-claim",
  ASTERION_KEYCLOAK_ADMIN_CLIENT_ID: "sync-test", ASTERION_KEYCLOAK_ADMIN_CLIENT_SECRET: "sync-test-fixture",
  ASTERION_KEYCLOAK_CLIENT_UUID: "00000000-0000-4000-8000-000000000001",
  ASTERION_MEMBER_ROLE: "member", ASTERION_ADMIN_ROLE: "administrator",
  ASTERION_ACCESS_SYNC_SECRET: "local-sync-worker-fixture-32-random-characters",
  DATABASE_URL: "postgresql://fixture_runtime:fixture_password@database.test:5432/public_fixture"
});

test("public preflight accepts the isolated profile without exposing secret values", () => {
  const result = inspectPublicEnvironment(valid());
  assert.deepEqual(result.errors, []);
  assert.equal(result.config.canonicalOrigin, "https://companions.test");
  assert.deepEqual(result.config.trustedProxyIps, ["192.0.2.11", "192.0.2.12"]);
  assert.doesNotMatch(JSON.stringify(result), /fixture_password|oidc-test-fixture|sync-test-fixture/);
});

test("public storage configuration is complete, separate and free of expansion paths", () => {
  const storage = {
    ASTERION_KEYCLOAK_STORAGE_CLIENT_ID: "storage-test",
    ASTERION_KEYCLOAK_STORAGE_CLIENT_SECRET: "storage-secret-fixture",
    ASTERION_CHAT_RECOVERY_KEY_FILE: "/run/credentials/fixture.service/chat-recovery.key"
  };
  assert.deepEqual(inspectPublicEnvironment({ ...valid(), ...storage }).errors, []);
  for (const key of Object.keys(storage)) {
    const partial = { ...storage };
    delete partial[key];
    assert.equal(inspectPublicEnvironment({ ...valid(), ...partial }).config, null, key);
  }
  for (const patch of [
    { ASTERION_KEYCLOAK_STORAGE_CLIENT_ID: "public-test" },
    { ASTERION_KEYCLOAK_STORAGE_CLIENT_ID: "sync-test" },
    { ASTERION_KEYCLOAK_STORAGE_CLIENT_ID: "bad/client" },
    { ASTERION_KEYCLOAK_STORAGE_CLIENT_SECRET: "replace-secret" },
    { ASTERION_CHAT_RECOVERY_KEY_FILE: "%d/chat-recovery.key" },
    { ASTERION_CHAT_RECOVERY_KEY_FILE: "/run/../key" }
  ]) {
    const result = inspectPublicEnvironment({ ...valid(), ...storage, ...patch });
    assert.equal(result.config, null);
    assert.doesNotMatch(JSON.stringify(result), /storage-secret-fixture/);
  }
});

test("public preflight refuses absent fields, placeholders, shared mode and internal port", () => {
  for (const key of Object.keys(valid())) {
    const environment = valid();
    delete environment[key];
    assert.ok(inspectPublicEnvironment(environment).errors.length > 0, key);
  }
  for (const patch of [
    { ASTERION_INTERNAL_TEST_MODE: "true" }, { ASTERION_INTERNAL_TEST_MODE: "False" },
    { ASTERION_DEPLOYMENT_MODE: "internal" }, { PORT: "3011" }, { HOSTNAME: "0.0.0.0" },
    { AUTH_KEYCLOAK_SECRET: "replace-me" }, { AUTH_SECRET: "short" },
    { AUTH_KEYCLOAK_ISSUER: "https://identity.example.invalid/realms/example" }
  ]) assert.equal(inspectPublicEnvironment({ ...valid(), ...patch }).config, null);
});

test("public origins and forwarding peers reject proxy configuration injection", () => {
  for (const patch of [
    { AUTH_URL: "http://companions.test" }, { AUTH_URL: "https://companions.test/" },
    { AUTH_URL: "https://companions.test/path" }, { AUTH_URL: "https://user:password@companions.test" },
    { AUTH_URL: "https://companions.test?return=other" }, { AUTH_URL: "https://127.0.0.1" },
    { AUTH_URL: "https://companions.test;" }, { AUTH_URL: "https://companions.test$variable" },
    { ASTERION_ALTERNATE_ORIGIN: "https://companions.test" },
    { ASTERION_TRUSTED_PROXY_IPS: "192.0.2.0/24" }, { ASTERION_TRUSTED_PROXY_IPS: "all" },
    { ASTERION_TRUSTED_PROXY_IPS: "192.0.2.11; allow all;" },
    { ASTERION_TRUSTED_PROXY_IPS: "192.0.2.11\nallow all" },
    { ASTERION_TRUSTED_PROXY_IPS: "fe80::1%eth0" },
    { ASTERION_TRUSTED_PROXY_IPS: "2001:db8::11" },
    { ASTERION_KEYCLOAK_ADMIN_CLIENT_ID: "public-test" }, { ASTERION_ADMIN_ROLE: "member" },
    { AUTH_REDIRECT_PROXY_URL: "https://unexpected.test" }
  ]) assert.equal(inspectPublicEnvironment({ ...valid(), ...patch }).config, null);
});

test("public admin origin is explicit HTTPS and is not exposed in the browser proxy", () => {
  const environment = valid();
  assert.doesNotMatch(renderPublicNginx(inspectPublicEnvironment(environment).config), /identity-admin/);
  for (const origin of ["", "http://identity-admin.test", "https://identity-admin.test/",
    "https://identity-admin.test/admin", "https://identity-admin.test?secret=fixture",
    "https://user:fixture@identity-admin.test", "https://identity-admin.test#fragment",
    "https://127.0.0.1", "https://[::1]", "https://identity-admin.test:443"]) {
    const result = inspectPublicEnvironment({ ...environment, ASTERION_KEYCLOAK_ADMIN_ORIGIN: origin });
    assert.equal(result.config, null, origin);
    assert.ok(result.errors.some(error => error.startsWith("ASTERION_KEYCLOAK_ADMIN_ORIGIN")));
    assert.doesNotMatch(JSON.stringify(result), /secret=fixture|user:fixture/);
  }
});

test("public proxy adds only named IPv4 TLS hosts and preserves the separate internal profile", () => {
  const rendered = renderPublicNginx(inspectPublicEnvironment(valid()).config);
  assert.equal((rendered.match(/listen 0\.0\.0\.0:443 ssl;/g) ?? []).length, 2);
  assert.doesNotMatch(rendered, /default_server|listen \[|8089|server_name _/);
  assert.equal((rendered.match(/ssl_certificate "\/etc\/nginx\/tls\/fixture\/server\.crt";/g) ?? []).length, 2);
  assert.equal((rendered.match(/ssl_certificate_key "\/etc\/nginx\/tls\/fixture\/server\.key";/g) ?? []).length, 2);
  assert.equal((rendered.match(/ssl_protocols TLSv1\.2 TLSv1\.3;/g) ?? []).length, 2);
  assert.match(rendered, /server 127\.0\.0\.1:3012;/);
  assert.doesNotMatch(rendered, /3011|8088/);
  assert.match(rendered, /return 444;/);
  assert.match(rendered, /return 308 https:\/\/companions\.test\$request_uri;/);
  assert.match(rendered, /192\.0\.2\.11 1;/);
  assert.match(rendered, /geo \$realip_remote_addr \$asterion_public_peer_allowed/);
  assert.match(rendered, /if \(\$asterion_public_peer_allowed = 0\) \{ return 403; \}/);
  assert.match(rendered, /proxy_set_header Host companions\.test;/);
  assert.match(rendered, /proxy_set_header X-Forwarded-Host companions\.test;/);
  assert.match(rendered, /proxy_set_header X-Forwarded-Proto https;/);
  assert.match(rendered, /proxy_set_header Forwarded "";/);
  assert.match(rendered, /proxy_set_header X-Forwarded-For \$realip_remote_addr;/);
  assert.doesNotMatch(rendered, /\$http_x_forwarded_proto/);
  assert.doesNotMatch(rendered, /proxy_add_x_forwarded_for|set_real_ip_from|proxy_cache\s+(?!off)/);
  assert.match(rendered, /proxy_buffering off;/);
  assert.match(rendered, /proxy_next_upstream off;/);
  assert.match(rendered, /location \^~ \/api\/internal\/ \{ return 404; \}/);
});

test("public proxy checks the actual peer and exact Host before the alternate redirect or proxy", () => {
  const rendered = renderPublicNginx(inspectPublicEnvironment(valid()).config);
  assert.match(rendered, /geo \$realip_remote_addr \$asterion_public_peer_allowed \{\s+default 0;/);
  for (const [kind, host] of [["alternate", "alternate.test"], ["canonical", "companions.test"]]) {
    const hostMap = rendered.split(`map $http_host $asterion_public_${kind}_host_allowed {`)[1]?.split("}")[0];
    assert.ok(hostMap, kind);
    assert.match(hostMap, /default 0;/);
    assert.ok(hostMap.includes(`    ${host} 1;`));
    assert.ok(hostMap.includes(`    ${host}:443 1;`));
    const server = rendered.split(`    server_name ${host};`)[1]?.split("\nserver {")[0];
    assert.ok(server, kind);
    const peer = server.indexOf("if ($asterion_public_peer_allowed = 0) { return 403; }");
    const hostGuard = server.indexOf(`if ($asterion_public_${kind}_host_allowed = 0) { return 444; }`);
    const response = server.indexOf(kind === "alternate" ? "return 308" : "proxy_pass");
    assert.ok(peer >= 0 && peer < hostGuard && hostGuard < response, kind);
  }
});

test("backend certificate paths and verification name reject placeholders, traversal and configuration injection", () => {
  for (const key of ["ASTERION_BACKEND_TLS_CERT_FILE", "ASTERION_BACKEND_TLS_KEY_FILE", "ASTERION_BACKEND_TLS_CA_FILE"]) {
    for (const value of ["relative/file.pem", "/", "/etc/tls/../server.pem", "/etc/tls/./server.pem", "/etc//server.pem",
      "/etc/tls/server.pem; allow all;", "/etc/tls/$file.pem", "/etc/tls/server*.pem", "/etc/tls/server\n.pem",
      "/etc/tls/server\".pem", "/etc/tls/server'.pem", "/etc/tls/server .pem", "C:\\tls\\server.pem", "/etc/tls/\\server.pem"]) {
      const result = inspectPublicEnvironment({ ...valid(), [key]: value });
      assert.equal(result.config, null, `${key} accepted an unsafe path`);
      assert.ok(result.errors.some((error) => error.startsWith(key)));
    }
  }
  for (const value of ["https://backend-node.test", "backend-node.test:443", "*.test", "backend-node.test;", "backend-node.test\n",
    "127.0.0.1", "backend-node.example.invalid", "backend-node.test/path", "user@backend-node.test", "[2001:db8::1]"]) {
    assert.equal(inspectPublicEnvironment({ ...valid(), ASTERION_BACKEND_TLS_SERVER_NAME: value }).config, null);
  }
});

test("the exported proxy renderer cannot bypass host, peer or TLS-path validation", () => {
  const config = inspectPublicEnvironment(valid()).config;
  for (const patch of [{ canonicalHost: "companions.test; return 200;" }, { alternateOrigin: "https://attacker.test" },
    { trustedProxyIps: ["0.0.0.0/0"] }, { trustedProxyIps: ["2001:db8::11"] }, { trustedProxyIps: [] },
    { backendTlsCertFile: "/etc/tls/server.pem\"; include /tmp/untrusted; #" },
    { backendTlsKeyFile: "/etc/tls/$key.pem" }, { backendTlsCaFile: "/etc/tls/../ca.pem" },
    { backendTlsServerName: "backend-node.test:443" }]) {
    assert.throws(() => renderPublicNginx({ ...config, ...patch }), /Cannot render an unvalidated public proxy configuration/);
  }
});

test("an explicit IPv4-only database policy rejects hostnames and IPv6 without changing the default contract", () => {
  assert.deepEqual(inspectPublicEnvironment(valid()).errors, []);
  for (const host of ["database.test", "[2001:db8::20]"]) {
    const result = inspectPublicEnvironment({ ...valid(), ASTERION_DATABASE_IPV4_ONLY: "true",
      DATABASE_URL: `postgresql://fixture_runtime:fixture_password@${host}:5432/public_fixture` });
    assert.equal(result.config, null);
    assert.ok(result.errors.some((error) => error.includes("literal IPv4")));
  }
  assert.deepEqual(inspectPublicEnvironment({ ...valid(), ASTERION_DATABASE_IPV4_ONLY: "true",
    DATABASE_URL: "postgresql://fixture_runtime:fixture_password@192.0.2.20:5432/public_fixture" }).errors, []);
  assert.equal(inspectPublicEnvironment({ ...valid(), ASTERION_DATABASE_IPV4_ONLY: "False" }).config, null);
});

test("backend verification CLI returns only the reviewed non-secret target fields", () => {
  const file = fileURLToPath(new URL("../deploy/public/public-config.mjs", import.meta.url));
  for (const [option, expected] of [["--canonical-host", "companions.test"], ["--alternate-host", "alternate.test"],
    ["--backend-tls-server-name", "backend-node.test"], ["--backend-tls-ca-file", "/etc/ssl/certs/fixture-ca.pem"]]) {
    const result = spawnSync(process.execPath, [file, option], { env: { ...process.env, ...valid() }, encoding: "utf8" });
    assert.equal(result.status, 0, option);
    assert.equal(result.stdout, `${expected}\n`, option);
    assert.equal(result.stderr, "", option);
  }
});

test("the isolated TLS checker maps exactly two production listeners to an unprivileged IPv4 loopback fixture", async () => {
  const checker = await readFile(new URL("../scripts/check-public-nginx.mjs", import.meta.url), "utf8");
  assert.match(checker, /"req", "-x509", "-newkey", "rsa:2048"/);
  assert.match(checker, /"-config", ownedPath\("openssl\.cnf"\)/);
  assert.match(checker, /chmod\(ownedPath\("fixture\.key"\), 0o600\)/);
  assert.match(checker, /const expectedListen = "listen 0\.0\.0\.0:443 ssl;";/);
  assert.match(checker, /generated\.split\(expectedListen\)\.length !== 3/);
  assert.match(checker, /replaceAll\(expectedListen, "listen 127\.0\.0\.1:39891 ssl;"\)/);
  assert.match(checker, /listen 127\.0\.0\.1:39891 ssl default_server;/);
  assert.doesNotMatch(checker, /listen 0\.0\.0\.0:443 ssl default_server;/);
  assert.match(checker, /server_name existing-site\.example\.org;/);
  assert.match(checker, /"-t", "-p",/);
  assert.doesNotMatch(checker, /"-s", "(?:reload|reopen|stop)"|systemctl|\/etc\/nginx\/nginx\.conf|listen \[/);
  assert.match(checker, /dirname\(target\) !== temporaryParent/);
  assert.match(checker, /port-mapped.*syntax\/certificate check/i);
  assert.match(checker, /Production port 443.*owner-run nginx -t/);
  if (process.platform === "win32") {
    const file = fileURLToPath(new URL("../scripts/check-public-nginx.mjs", import.meta.url));
    const result = spawnSync(process.execPath, [file, "--require-nginx"], { encoding: "utf8" });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /FAIL: Required Nginx syntax verification needs the target Linux environment/);
  }
});

test("public service always runs preflight and never uses the internal environment", async () => {
  const service = await readFile(new URL("../deploy/public/asterion-public.service", import.meta.url), "utf8");
  assert.match(service, /ExecStartPre=.*public-config\.mjs --check/);
  assert.match(service, /ExecStart=\/usr\/bin\/node \/opt\/sites\/asterion-public\/current\/start-asterion\.mjs/);
  assert.doesNotMatch(service, /ExecStart=.*\/server\.js/);
  assert.match(service, /EnvironmentFile=\/etc\/asterion-public\/asterion.env/);
  assert.doesNotMatch(service, /asterion-internal/);
  assert.match(service, /ProtectSystem=strict/);
});

test("public preparation remains stopped and activation does not migrate or touch internal units", async () => {
  const prepare = await readFile(new URL("../deploy/public/prepare-public.sh", import.meta.url), "utf8");
  const activate = await readFile(new URL("../deploy/public/activate-public.sh", import.meta.url), "utf8");
  assert.doesNotMatch(prepare, /systemctl (?:enable|start|restart)|ln -s.*sites-enabled/);
  assert.match(prepare, /install -m 0600 -o root -g root/);
  assert.match(prepare, /chown -R root:root/);
  assert.match(prepare, /-f \$\{ARTIFACT_DIR\}\/start-asterion\.mjs/);
  assert.match(prepare, /-f \$\{ARTIFACT_DIR\}\/\.asterion-operations\/public-config\.mjs/);
  assert.match(prepare, /cmp -s -- "\$\{SCRIPT_DIR\}\/public-config\.mjs" "\$\{ARTIFACT_DIR\}\/\.asterion-operations\/public-config\.mjs"/);
  assert.doesNotMatch(prepare, /install -m.*"\$\{SCRIPT_DIR\}\/public-config\.mjs"/);
  assert.match(activate, /nginx -t/);
  assert.match(activate, /trap rollback ERR/);
  assert.match(activate, /systemd-run --quiet --pipe --wait --collect/);
  for (const script of [prepare, activate]) {
    assert.doesNotMatch(script, /systemctl .*asterion-internal/);
    assert.doesNotMatch(script, /prisma migrate|ufw |iptables |source .*env/);
  }
});

test("the synchronization worker does not place credentials in process arguments or logs", async () => {
  const worker = await readFile(new URL("../deploy/public/run-access-sync.mjs", import.meta.url), "utf8");
  const service = await readFile(new URL("../deploy/public/asterion-public-access-sync.service", import.meta.url), "utf8");
  const timer = await readFile(new URL("../deploy/public/asterion-public-access-sync.timer", import.meta.url), "utf8");
  assert.match(worker, /http:\/\/127\.0\.0\.1:3012\/api\/internal\/access-sync/);
  assert.match(worker, /redirect: "error"/);
  assert.doesNotMatch(service, /ExecStart=.*SECRET|ExecStart=.*Bearer/);
  assert.doesNotMatch(worker, /write\([^)]*secret|console\./);
  assert.match(timer, /OnUnitInactiveSec=60s/);
});

test("the worker calls only loopback with its header, rejects redirects, and reports request failures", async () => {
  let calls = 0;
  assert.equal(await requestAccessSynchronization(valid(), async (url, options) => {
    calls += 1;
    assert.equal(url, "http://127.0.0.1:3012/api/internal/access-sync");
    assert.equal(options.method, "POST");
    assert.equal(options.redirect, "error");
    assert.equal(options.headers.Authorization, `Bearer ${valid().ASTERION_ACCESS_SYNC_SECRET}`);
    return Response.json({ applied: 1, failed: 0, blocked: 0, skipped: 0 });
  }), true);
  assert.equal(calls, 1);
  assert.equal(await requestAccessSynchronization({ ...valid(), ASTERION_DEPLOYMENT_MODE: "internal" }, async () => {
    throw new Error("No network request is allowed for internal mode.");
  }), false);
  assert.equal(await requestAccessSynchronization(valid(), async () => new Response(null, { status: 401 })), false);
  assert.equal(await requestAccessSynchronization(valid(), async () => { throw new Error("private-network-detail"); }), false);
});

test("worker success requires validated batch results and never exposes response details", async () => {
  for (const body of [null, {}, { applied: 21, failed: 0, blocked: 0, skipped: 0 },
    { applied: 20, failed: 0, blocked: 0, skipped: 1 },
    { applied: 0, failed: 1, blocked: 0, skipped: 0 },
    { applied: 0, failed: 0, blocked: 1, skipped: 0 }]) {
    assert.equal(await requestAccessSynchronization(valid(), async () => Response.json(body)), false);
  }
  const reports = [];
  assert.equal(await requestAccessSynchronization(valid(), async () => Response.json({
    applied: 1, failed: 0, blocked: 0, skipped: 0, privateDetail: "must-not-be-printed"
  }), (summary) => reports.push(summary)), true);
  assert.deepEqual(reports, ["applied=1 failed=0 blocked=0 skipped=0"]);
  assert.equal(await requestAccessSynchronization(valid(), async () => new Response("invalid-json")), false);
});

test("preflight CLI refuses unsafe configuration without printing connection or client secrets", () => {
  const file = fileURLToPath(new URL("../deploy/public/public-config.mjs", import.meta.url));
  const result = spawnSync(process.execPath, [file, "--check"], {
    env: { ...process.env, ...valid(), ASTERION_INTERNAL_TEST_MODE: "true" }, encoding: "utf8"
  });
  assert.equal(result.status, 1);
  assert.match(result.stderr, /Public deployment refused/);
  assert.doesNotMatch(`${result.stdout}${result.stderr}`, /fixture_password|oidc-test-fixture|sync-test-fixture|randomness-is-an-owner/);
});

test("public database provisioning requires fresh quoted targets and keeps credentials interactive", async () => {
  const wrapper = await readFile(new URL("../deploy/public/provision-public-database.sh", import.meta.url), "utf8");
  const sql = await readFile(new URL("../deploy/public/public-database.sql", import.meta.url), "utf8");
  assert.match(wrapper, /\[\[ \$# -ne 3 \]\]/);
  assert.match(wrapper, /\^\[a-z\]\[a-z0-9_\]\{0,62\}\$/);
  assert.match(wrapper, /\(internal\|test\|testing\|dev\|development\)/);
  assert.match(wrapper, /--host=\/var\/run\/postgresql --port=5432/);
  assert.match(wrapper, /--username=postgres --dbname=postgres --set=ON_ERROR_STOP=1/);
  assert.match(sql, /NOT pg_is_in_recovery\(\)/);
  assert.ok(sql.indexOf("AS targets_absent") < sql.indexOf('CREATE ROLE :"owner_role"'));
  assert.match(sql, /CREATE ROLE :"owner_role" NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS/);
  assert.match(sql, /CREATE ROLE :"runtime_role" NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS/);
  assert.match(sql, /\\password :"owner_role"/);
  assert.match(sql, /\\password :"runtime_role"/);
  assert.match(sql, /rolpassword LIKE 'SCRAM-SHA-256\$%'/);
  assert.match(sql, /COMMIT;[\s\S]*CREATE DATABASE :"database_name" OWNER :"owner_role" TEMPLATE template0 ALLOW_CONNECTIONS false;/);
  assert.ok(sql.indexOf('REVOKE ALL PRIVILEGES ON DATABASE :"database_name" FROM PUBLIC') < sql.indexOf('ALTER DATABASE :"database_name" ALLOW_CONNECTIONS true'));
  assert.match(sql, /GRANT CONNECT ON DATABASE :"database_name" TO :"owner_role", :"runtime_role"/);
  assert.match(sql, /REVOKE ALL PRIVILEGES ON SCHEMA public FROM PUBLIC/);
  assert.match(sql, /GRANT USAGE ON SCHEMA public TO :"runtime_role"/);
  assert.match(sql, /ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_role" IN SCHEMA public\s+GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"runtime_role"/);
  assert.match(sql, /ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_role" IN SCHEMA public\s+GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"runtime_role"/);
  assert.ok(sql.indexOf('ALTER DEFAULT PRIVILEGES FOR ROLE :"owner_role"') < sql.indexOf('ALTER ROLE :"runtime_role" LOGIN'));
  for (const contents of [wrapper, sql]) {
    assert.doesNotMatch(contents, /DROP (?:DATABASE|ROLE)|CREATE OR REPLACE|PASSWORD\s+'|GRANT ALL.*runtime_role|prisma migrate|patronictl|pg_hba\.conf/);
  }
});

test("database wrapper rejects unsafe names before inspecting an account or connecting", (context) => {
  const bash = process.env.ASTERION_TEST_BASH ?? "bash";
  const available = spawnSync(bash, ["--version"], { encoding: "utf8" });
  if (available.error || available.status !== 0) {
    context.skip("No Bash runtime; SQL/database execution is a separate Linux acceptance gate.");
    return;
  }
  const wrapper = fileURLToPath(new URL("../deploy/public/provision-public-database.sh", import.meta.url));
  for (const name of ["postgres", "template0", "pg_catalog", "shared_internal", "shared_test", "asterion_dev", "name;DROP", "MixedCase", "a".repeat(64)]) {
    const result = spawnSync(bash, [wrapper, name, "public_owner_fixture", "public_runtime_fixture"], { encoding: "utf8" });
    assert.equal(result.status, 1, name);
    assert.match(result.stderr, /Use new public identifiers/, name);
    assert.doesNotMatch(result.stdout, /Preparing|Password/);
  }
});
