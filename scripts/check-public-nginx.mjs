import { spawnSync } from "node:child_process";
import { chmod, mkdtemp, mkdir, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve, sep } from "node:path";
import { renderPublicNginx } from "../deploy/public/public-config.mjs";

const requireNginx = process.argv.includes("--require-nginx");
const unknownArguments = process.argv.slice(2).filter((argument) => argument !== "--require-nginx");

if (unknownArguments.length) {
  process.stderr.write("Usage: node scripts/check-public-nginx.mjs [--require-nginx]\n");
  process.exitCode = 1;
} else if (process.platform === "win32") {
  if (requireNginx) {
    process.stderr.write("FAIL: Required Nginx syntax verification needs the target Linux environment; no configuration was read or changed.\n");
    process.exitCode = 1;
  } else {
    process.stdout.write("SKIP: Nginx syntax verification requires the target Linux environment; no configuration was read or changed.\n");
  }
} else {
  await checkNginx();
}

async function checkNginx() {
  const candidates = ["nginx", "/usr/sbin/nginx", "/usr/local/sbin/nginx"];
  const executable = candidates.find((candidate) => {
    const result = spawnSync(candidate, ["-v"], { encoding: "utf8", shell: false, timeout: 10_000 });
    return !result.error && result.status === 0;
  });
  if (!executable) {
    const message = "Nginx is unavailable; no syntax acceptance was established.\n";
    if (requireNginx) {
      process.stderr.write(`FAIL: ${message}`);
      process.exitCode = 1;
    } else {
      process.stdout.write(`SKIP: ${message}`);
    }
    return;
  }
  const openssl = ["openssl", "/usr/bin/openssl", "/usr/local/bin/openssl"].find((candidate) => {
    const result = spawnSync(candidate, ["version"], { encoding: "utf8", shell: false, timeout: 10_000 });
    return !result.error && result.status === 0;
  });
  if (!openssl) {
    process.stderr.write("FAIL: OpenSSL is required to create an isolated disposable certificate; no TLS syntax acceptance was established.\n");
    process.exitCode = 1;
    return;
  }

  const temporaryParent = resolve(tmpdir());
  const prefix = "asterion-nginx-check-";
  let temporaryRoot;
  try {
    temporaryRoot = await mkdtemp(join(temporaryParent, prefix));
    if (/[\u0000-\u001f\u007f$*?\[\]{}]/.test(temporaryRoot)) {
      throw new Error("The temporary directory contains Nginx expansion characters; no syntax check was attempted.");
    }
    const ownedPath = (name) => join(temporaryRoot, name);
    const quoted = (value) => `"${value.replaceAll("\\", "\\\\").replaceAll('"', '\\"')}"`;
    for (const directory of ["body", "proxy", "fastcgi", "uwsgi", "scgi"]) await mkdir(ownedPath(directory));

    // Create fixture-only TLS material in the private temporary tree. No installed
    // keys, CA bundles or OpenSSL/Nginx configuration are consumed or replaced.
    await writeFile(ownedPath("openssl.cnf"), `[req]
prompt = no
distinguished_name = fixture_name
x509_extensions = fixture_extensions
[fixture_name]
CN = backend-node.example.com
[fixture_extensions]
subjectAltName = DNS:backend-node.example.com
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
`, { encoding: "utf8", mode: 0o600 });
    const certificate = spawnSync(openssl, [
      "req", "-x509", "-newkey", "rsa:2048", "-sha256", "-nodes", "-days", "1",
      "-config", ownedPath("openssl.cnf"), "-keyout", ownedPath("fixture.key"), "-out", ownedPath("fixture.crt")
    ], { encoding: "utf8", shell: false, timeout: 20_000, maxBuffer: 256 * 1024 });
    if (certificate.error || certificate.status !== 0) {
      throw new Error("Could not generate the isolated disposable TLS certificate; no syntax check was attempted.");
    }
    await chmod(ownedPath("fixture.key"), 0o600);
    await chmod(ownedPath("fixture.crt"), 0o600);

    // Reserved documentation domains and TEST-NET addresses only. Do not consume
    // the operator's environment, real topology, or any installed Nginx includes.
    const generated = renderPublicNginx({
      canonicalOrigin: "https://asterion.example.com",
      canonicalHost: "asterion.example.com",
      alternateOrigin: "https://starfriend.example.net",
      alternateHost: "starfriend.example.net",
      trustedProxyIps: ["192.0.2.10", "192.0.2.11"],
      backendTlsCertFile: ownedPath("fixture.crt"),
      backendTlsKeyFile: ownedPath("fixture.key"),
      backendTlsCaFile: ownedPath("fixture.crt"),
      backendTlsServerName: "backend-node.example.com"
    });
    const expectedErrorLog = "error_log /var/log/nginx/asterion-public-error.log crit;";
    if (generated.split(expectedErrorLog).length !== 2) {
      throw new Error("The generated error-log contract changed; review this isolated checker before running it.");
    }
    // Some Nginx versions attempt socket binds during -t. Map only the two
    // expected production listeners to an unprivileged IPv4 loopback fixture.
    // This verifies syntax/certificate loading, not production port admission.
    const expectedListen = "listen 0.0.0.0:443 ssl;";
    if (generated.split(expectedListen).length !== 3) {
      throw new Error("The two-listener production contract changed; no port-mapped syntax check was attempted.");
    }
    const snippet = generated
      .replaceAll(expectedListen, "listen 127.0.0.1:39891 ssl;")
      .replace(expectedErrorLog, `error_log ${quoted(ownedPath("public-error.log"))} crit;`);
    const wrapper = `worker_processes 1;
pid ${quoted(ownedPath("nginx.pid"))};
error_log ${quoted(ownedPath("error.log"))} crit;
events { worker_connections 16; }
http {
    access_log off;
    client_body_temp_path ${quoted(ownedPath("body"))};
    proxy_temp_path ${quoted(ownedPath("proxy"))};
    fastcgi_temp_path ${quoted(ownedPath("fastcgi"))};
    uwsgi_temp_path ${quoted(ownedPath("uwsgi"))};
    scgi_temp_path ${quoted(ownedPath("scgi"))};
    # An unrelated existing default must coexist with the named Asterion hosts.
    server {
        listen 127.0.0.1:39891 ssl default_server;
        server_name existing-site.example.org;
        ssl_certificate ${quoted(ownedPath("fixture.crt"))};
        ssl_certificate_key ${quoted(ownedPath("fixture.key"))};
        ssl_protocols TLSv1.2 TLSv1.3;
        return 404;
    }
    include ${quoted(ownedPath("public.conf"))};
}
`;
    await writeFile(ownedPath("public.conf"), snippet, { encoding: "utf8", mode: 0o600 });
    await writeFile(ownedPath("nginx.conf"), wrapper, { encoding: "utf8", mode: 0o600 });
    // -t can transiently bind the mapped loopback socket while checking config.
    // It does not start a persistent service. -e keeps early logs in our tree.
    const result = spawnSync(executable, [
      "-t", "-p", `${temporaryRoot}${sep}`, "-c", ownedPath("nginx.conf"), "-e", ownedPath("startup-error.log")
    ], { encoding: "utf8", shell: false, timeout: 20_000, maxBuffer: 256 * 1024 });
    if (result.stdout) process.stdout.write(result.stdout);
    if (result.stderr) process.stderr.write(result.stderr);
    if (result.error || result.status !== 0) {
      process.stderr.write("FAIL: Port-mapped isolated Nginx syntax/certificate check did not pass nginx -t.\n");
      process.exitCode = 1;
    } else {
      process.stdout.write("PASS: Port-mapped isolated IPv4 HTTPS syntax/certificate check passed nginx -t alongside a fixture default on 127.0.0.1:39891. Socket checks may transiently bind loopback; no persistent service or installed configuration was changed. Production port 443 and actual certificates still require owner-run nginx -t and runtime acceptance.\n");
    }
  } catch (error) {
    process.stderr.write(`FAIL: ${error instanceof Error ? error.message : "Isolated Nginx verification failed."}\n`);
    process.exitCode = 1;
  } finally {
    if (temporaryRoot) {
      const target = resolve(temporaryRoot);
      if (dirname(target) !== temporaryParent || !basename(target).startsWith(prefix)) {
        process.stderr.write("FAIL: Temporary cleanup target validation failed; no removal was attempted.\n");
        process.exitCode = 1;
      } else {
        await rm(target, { recursive: true, force: true });
      }
    }
  }
}
