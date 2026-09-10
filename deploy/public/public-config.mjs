import { isIP } from "node:net";
import { pathToFileURL } from "node:url";
import { constants } from "node:fs";
import { lstat, open } from "node:fs/promises";

const dnsName = (value) => typeof value === "string" && value.length <= 253 &&
  /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(value) && !isIP(value);
const safeAbsoluteFile = (value) => typeof value === "string" && value.length <= 4096 &&
  /^\/(?:[A-Za-z0-9_-][A-Za-z0-9._-]*\/)*[A-Za-z0-9_-][A-Za-z0-9._-]*$/.test(value);

// This module never reads an environment file or includes its values in errors.
// systemd supplies the same EnvironmentFile to preflight and the application.
export function inspectPublicEnvironment(environment = process.env) {
  const errors = [];
  const values = {};
  const requireText = (key) => {
    const value = environment[key]?.trim() ?? "";
    if (!value || value !== environment[key] || /[\u0000-\u001f\u007f]/.test(value) || /^(?:replace[-_]|change[-_]|your[-_]|<)/i.test(value)) {
      errors.push(`${key} must be set to a non-placeholder value.`);
    }
    values[key] = value;
    return value;
  };
  const exact = (key, expected) => {
    if (environment[key] !== expected) errors.push(`${key} must explicitly equal ${expected}.`);
  };
  const httpsUrl = (key, originOnly) => {
    const raw = requireText(key);
    try {
      const url = new URL(raw);
      if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash ||
          url.port || !url.hostname.includes(".") || isIP(url.hostname.replace(/^\[|\]$/g, "")) ||
          url.hostname.length > 253 || !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(url.hostname) ||
          /(?:^|\.)(?:localhost|invalid)$/.test(url.hostname) ||
          /(?:^|\.)example\.(?:com|org|net)$/.test(url.hostname) ||
          (originOnly && url.pathname !== "/")) throw new Error("Invalid URL");
      if (originOnly && raw !== url.origin) throw new Error("Origin must be canonical");
      return url;
    } catch {
      errors.push(`${key} must be an exact non-placeholder HTTPS ${originOnly ? "origin without a path or trailing slash" : "URL"}.`);
      return null;
    }
  };

  exact("NODE_ENV", "production");
  exact("ASTERION_DEPLOYMENT_MODE", "public");
  exact("ASTERION_INTERNAL_TEST_MODE", "false");
  exact("HOSTNAME", "127.0.0.1");
  exact("PORT", "3012");
  exact("AUTH_TRUST_HOST", "true");

  const canonical = httpsUrl("AUTH_URL", true);
  const alternate = httpsUrl("ASTERION_ALTERNATE_ORIGIN", true);
  if (canonical && alternate && canonical.origin === alternate.origin) {
    errors.push("ASTERION_ALTERNATE_ORIGIN must differ from AUTH_URL.");
  }
  const issuer = httpsUrl("AUTH_KEYCLOAK_ISSUER", false);
  httpsUrl("ASTERION_KEYCLOAK_ADMIN_ORIGIN", true);
  if (issuer && !/^(?:\/[A-Za-z0-9._~-]+)*\/realms\/[A-Za-z0-9._~-]+$/.test(issuer.pathname)) {
    errors.push("AUTH_KEYCLOAK_ISSUER must identify exactly one Keycloak realm without a trailing slash.");
  }
  for (const key of ["ASTERION_BACKEND_TLS_CERT_FILE", "ASTERION_BACKEND_TLS_KEY_FILE", "ASTERION_BACKEND_TLS_CA_FILE"]) {
    if (!safeAbsoluteFile(requireText(key))) {
      errors.push(`${key} must be an absolute POSIX file path using plain ASCII segments without traversal or expansion characters.`);
    }
  }
  const backendTlsServerName = requireText("ASTERION_BACKEND_TLS_SERVER_NAME");
  if (!dnsName(backendTlsServerName) || /(?:^|\.)(?:localhost|invalid)$/.test(backendTlsServerName) ||
      /(?:^|\.)example\.(?:com|org|net)$/.test(backendTlsServerName)) {
    errors.push("ASTERION_BACKEND_TLS_SERVER_NAME must be an exact non-placeholder DNS certificate name without a scheme, path, wildcard or port.");
  }

  for (const key of ["AUTH_SECRET", "AUTH_KEYCLOAK_ID", "AUTH_KEYCLOAK_SECRET",
    "ASTERION_KEYCLOAK_ADMIN_CLIENT_ID", "ASTERION_KEYCLOAK_ADMIN_CLIENT_SECRET",
    "ASTERION_KEYCLOAK_CLIENT_UUID", "ASTERION_MEMBER_ROLE", "ASTERION_ADMIN_ROLE",
    "ASTERION_ACCESS_SYNC_SECRET"]) requireText(key);
  if (values.AUTH_SECRET.length < 32) errors.push("AUTH_SECRET must contain at least 32 randomly generated characters.");
  if (!/^[A-Za-z0-9_+\/=\-]{32,256}$/.test(values.ASTERION_ACCESS_SYNC_SECRET)) {
    errors.push("ASTERION_ACCESS_SYNC_SECRET must contain 32 to 256 random base64 or URL-safe characters.");
  }
  if (values.AUTH_KEYCLOAK_ID === values.ASTERION_KEYCLOAK_ADMIN_CLIENT_ID) {
    errors.push("The browser OIDC client and permission-sync service client must be separate clients.");
  }
  const storageKeys = ["ASTERION_KEYCLOAK_STORAGE_CLIENT_ID", "ASTERION_KEYCLOAK_STORAGE_CLIENT_SECRET", "ASTERION_CHAT_RECOVERY_KEY_FILE"];
  if (storageKeys.some(key => Boolean(environment[key]))) {
    for (const key of storageKeys) requireText(key);
    if (!/^[A-Za-z0-9_.-]{1,100}$/.test(values.ASTERION_KEYCLOAK_STORAGE_CLIENT_ID) ||
        [values.AUTH_KEYCLOAK_ID, values.ASTERION_KEYCLOAK_ADMIN_CLIENT_ID].includes(values.ASTERION_KEYCLOAK_STORAGE_CLIENT_ID)) {
      errors.push("ASTERION_KEYCLOAK_STORAGE_CLIENT_ID must be a separate plain client identifier.");
    }
    if (values.ASTERION_KEYCLOAK_STORAGE_CLIENT_SECRET.length > 4096) errors.push("ASTERION_KEYCLOAK_STORAGE_CLIENT_SECRET exceeds the supported length.");
    if (!safeAbsoluteFile(values.ASTERION_CHAT_RECOVERY_KEY_FILE)) errors.push("ASTERION_CHAT_RECOVERY_KEY_FILE must be an absolute POSIX path without expansion or traversal.");
  }
  if (values.ASTERION_MEMBER_ROLE === values.ASTERION_ADMIN_ROLE) {
    errors.push("The member and administrator client roles must be distinct.");
  }
  for (const key of ["ASTERION_MEMBER_ROLE", "ASTERION_ADMIN_ROLE"]) {
    if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$/.test(values[key])) errors.push(`${key} must be a plain client-role name.`);
  }

  const database = requireText("DATABASE_URL");
  if (environment.ASTERION_DATABASE_IPV4_ONLY !== undefined &&
      !["true", "false"].includes(environment.ASTERION_DATABASE_IPV4_ONLY)) {
    errors.push("ASTERION_DATABASE_IPV4_ONLY must be exactly true or false when set.");
  }
  try {
    const url = new URL(database);
    if (!["postgres:", "postgresql:"].includes(url.protocol) || !url.username || !url.password ||
        !url.hostname || /(?:^|\.)invalid$/.test(url.hostname) || !/^\/[^/]+$/.test(url.pathname) ||
        [url.username, url.password, url.pathname.slice(1)].some((value) => /^(?:replace[-_]|change[-_]|your[-_]|<)/i.test(decodeURIComponent(value)))) {
      throw new Error("Invalid database URL");
    }
    if (environment.ASTERION_DATABASE_IPV4_ONLY === "true" && isIP(url.hostname) !== 4) {
      errors.push("DATABASE_URL must use a literal IPv4 address when ASTERION_DATABASE_IPV4_ONLY is true.");
    }
  } catch {
    errors.push("DATABASE_URL must identify the dedicated public database and its runtime credentials.");
  }
  if (environment.AUTH_REDIRECT_PROXY_URL || environment.NEXTAUTH_URL || environment.NEXTAUTH_URL_INTERNAL) {
    errors.push("Legacy or preview authentication URL overrides must be unset in this public profile.");
  }
  const peers = requireText("ASTERION_TRUSTED_PROXY_IPS").split(",").map((value) => value.trim());
  if (!peers.length || peers.length > 16 || peers.some((value) => isIP(value) !== 4)) {
    errors.push("ASTERION_TRUSTED_PROXY_IPS must contain 1 to 16 exact IPv4 addresses, not networks, IPv6 addresses or hostnames.");
  }
  if (environment.ASTERION_BOOTSTRAP_ADMIN_SUB &&
      (/[\u0000-\u001f\u007f]/.test(environment.ASTERION_BOOTSTRAP_ADMIN_SUB) ||
       /^(?:replace[-_]|change[-_]|your[-_]|<)/i.test(environment.ASTERION_BOOTSTRAP_ADMIN_SUB))) {
    errors.push("ASTERION_BOOTSTRAP_ADMIN_SUB must be one verified non-placeholder subject without control characters.");
  }
  return {
    errors,
    config: errors.length ? null : {
      canonicalOrigin: canonical.origin,
      canonicalHost: canonical.hostname,
      alternateOrigin: alternate.origin,
      alternateHost: alternate.hostname,
      trustedProxyIps: [...new Set(peers)],
      backendTlsCertFile: values.ASTERION_BACKEND_TLS_CERT_FILE,
      backendTlsKeyFile: values.ASTERION_BACKEND_TLS_KEY_FILE,
      backendTlsCaFile: values.ASTERION_BACKEND_TLS_CA_FILE,
      backendTlsServerName
    }
  };
}

// Version 1.0.0 (2026-09-09), Alice Endelgard. Read-only startup acceptance.
// Run as the actual service user, including inside a systemd credential namespace.
// Never expose key bytes, paths or raw filesystem exceptions in diagnostic output.
export async function verifyPublicStorageKey(environment = process.env) {
  if (!["ASTERION_KEYCLOAK_STORAGE_CLIENT_ID", "ASTERION_KEYCLOAK_STORAGE_CLIENT_SECRET", "ASTERION_CHAT_RECOVERY_KEY_FILE"].some(key => Boolean(environment[key]))) return;
  let handle, raw, key;
  try {
    const path = environment.ASTERION_CHAT_RECOVERY_KEY_FILE;
    if (!safeAbsoluteFile(path) || !(await lstat(path)).isFile()) throw new Error();
    handle = await open(path, constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0));
    const info = await handle.stat();
    if (!info.isFile() || info.size < 43 || info.size > 45 ||
        (process.platform !== "win32" && (info.mode & 0o027) !== 0)) throw new Error();
    raw = Buffer.alloc(46);
    const { bytesRead } = await handle.read(raw, 0, raw.length, 0);
    const encoded = raw.subarray(0, bytesRead).toString("utf8").replace(/\r?\n$/, "");
    key = Buffer.from(encoded, "base64url");
    if (!/^[A-Za-z0-9_-]{43}$/.test(encoded) || key.length !== 32 || key.toString("base64url") !== encoded) throw new Error();
  } catch {
    throw new Error("Public chat recovery key is unavailable or invalid.");
  } finally {
    raw?.fill(0); key?.fill(0);
    await handle?.close().catch(() => {});
  }
}

export function renderPublicNginx(config) {
  // Keep the exported renderer safe even when used without the environment CLI.
  if (!config || !dnsName(config.canonicalHost) || !dnsName(config.alternateHost) ||
      config.canonicalHost === config.alternateHost ||
      config.canonicalOrigin !== `https://${config.canonicalHost}` ||
      config.alternateOrigin !== `https://${config.alternateHost}` ||
      ![config.backendTlsCertFile, config.backendTlsKeyFile, config.backendTlsCaFile].every(safeAbsoluteFile) ||
      !dnsName(config.backendTlsServerName) || !Array.isArray(config.trustedProxyIps) ||
      !config.trustedProxyIps.length || config.trustedProxyIps.length > 16 ||
      config.trustedProxyIps.some((address) => isIP(address) !== 4)) {
    throw new Error("Cannot render an unvalidated public proxy configuration.");
  }
  const allowed = ["127.0.0.1", ...config.trustedProxyIps];
  const peers = [...new Set(allowed)].map((address) => `    ${address} 1;`).join("\n");
  const tls = `    ssl_certificate "${config.backendTlsCertFile}";
    ssl_certificate_key "${config.backendTlsKeyFile}";
    ssl_protocols TLSv1.2 TLSv1.3;`;
  return `# Generated by the reviewed public deployment preflight. No secrets.
# Named IPv4 TLS hosts coexist with the owner's existing default and other sites.
# Requires ngx_http_realip_module: inspect the original TCP peer, not rewritten IPs.
geo $realip_remote_addr $asterion_public_peer_allowed {
    default 0;
${peers}
}

map $http_host $asterion_public_alternate_host_allowed {
    default 0;
    ${config.alternateHost} 1;
    ${config.alternateHost}:443 1;
}

map $http_host $asterion_public_canonical_host_allowed {
    default 0;
    ${config.canonicalHost} 1;
    ${config.canonicalHost}:443 1;
}

upstream asterion_public_app {
    server 127.0.0.1:3012;
    keepalive 16;
}

server {
    listen 0.0.0.0:443 ssl;
    server_name ${config.alternateHost};
${tls}
    access_log off;
    if ($asterion_public_peer_allowed = 0) { return 403; }
    if ($asterion_public_alternate_host_allowed = 0) { return 444; }
    location / {
        # The server-level peer check runs before this redirect.
        return 308 ${config.canonicalOrigin}$request_uri;
    }
}

server {
    listen 0.0.0.0:443 ssl;
    server_name ${config.canonicalHost};
${tls}
    if ($asterion_public_peer_allowed = 0) { return 403; }
    if ($asterion_public_canonical_host_allowed = 0) { return 444; }
    client_max_body_size 1m;
    access_log off;
    error_log /var/log/nginx/asterion-public-error.log crit;
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy no-referrer always;
    add_header X-Frame-Options DENY always;
    add_header X-Robots-Tag "noindex, nofollow, noarchive" always;

    location = /api/internal { return 404; }
    location ^~ /api/internal/ { return 404; }

    location / {
        # The backend is HTTPS-only; never trust a caller-supplied scheme or host.
        proxy_pass http://asterion_public_app;
        proxy_http_version 1.1;
        proxy_set_header Host ${config.canonicalHost};
        proxy_set_header X-Forwarded-Host ${config.canonicalHost};
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-Port 443;
        proxy_set_header Forwarded "";
        proxy_set_header X-Forwarded-For $realip_remote_addr;
        proxy_set_header X-Real-IP $realip_remote_addr;
        proxy_set_header Connection "";
        proxy_cache off;
        proxy_buffering off;
        proxy_read_timeout 60s;
        proxy_connect_timeout 5s;
        # Never retry mutations implicitly on a different upstream.
        proxy_next_upstream off;
    }
}
`;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const { errors, config } = inspectPublicEnvironment();
  if (errors.length) {
    process.stderr.write(`Public deployment refused:\n${errors.map((error) => `- ${error}`).join("\n")}\n`);
    process.exitCode = 1;
  } else if (process.argv[2] === "--render-nginx") {
    process.stdout.write(renderPublicNginx(config));
  } else if (process.argv[2] === "--canonical-host") {
    process.stdout.write(`${config.canonicalHost}\n`);
  } else if (process.argv[2] === "--alternate-host") {
    process.stdout.write(`${config.alternateHost}\n`);
  } else if (process.argv[2] === "--backend-tls-server-name") {
    process.stdout.write(`${config.backendTlsServerName}\n`);
  } else if (process.argv[2] === "--backend-tls-ca-file") {
    process.stdout.write(`${config.backendTlsCaFile}\n`);
  } else if (!process.argv[2] || process.argv[2] === "--check") {
    try {
      await verifyPublicStorageKey();
      process.stdout.write("Public deployment configuration passed local preflight; identity and database acceptance are still required.\n");
    } catch {
      process.stderr.write("Public chat recovery key is unavailable or invalid.\n");
      process.exitCode = 1;
    }
  } else {
    process.stderr.write("Unknown public preflight action.\n");
    process.exitCode = 1;
  }
}
