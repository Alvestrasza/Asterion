import type { AccessRole } from "./access-policy";
import { isIP } from "node:net";

type Environment = Record<string, string | undefined>;
export type KeycloakAccessConfig = {
  issuer: string;
  adminOrigin?: string;
  clientId: string;
  clientSecret: string;
  clientUuid: string;
  memberRole: string;
  adminRole: string;
};
type RoleRepresentation = { id: string; name: string; clientRole: true; containerId: string; composite?: boolean };
export type RemoteAccess = { enabled: boolean; role: AccessRole };

export class KeycloakAccessError extends Error {
  readonly code: string;

  constructor(code: string) {
    super(code);
    this.name = "KeycloakAccessError";
    this.code = code;
  }
}

export function keycloakAccessConfig(environment: Environment = process.env): KeycloakAccessConfig {
  const config = {
    issuer: environment.AUTH_KEYCLOAK_ISSUER?.trim() ?? "",
    adminOrigin: environment.ASTERION_KEYCLOAK_ADMIN_ORIGIN,
    clientId: environment.ASTERION_KEYCLOAK_ADMIN_CLIENT_ID?.trim() ?? "",
    clientSecret: environment.ASTERION_KEYCLOAK_ADMIN_CLIENT_SECRET?.trim() ?? "",
    clientUuid: environment.ASTERION_KEYCLOAK_CLIENT_UUID?.trim() ?? "",
    memberRole: environment.ASTERION_MEMBER_ROLE?.trim() ?? "",
    adminRole: environment.ASTERION_ADMIN_ROLE?.trim() ?? ""
  };
  validateConfig(config);
  return config;
}

function issuerEndpoints(issuer: string, adminOrigin?: string) {
  let url: URL;
  try { url = new URL(issuer); } catch { throw new KeycloakAccessError("sync_configuration_invalid"); }
  const path = /^(.*)\/realms\/([^/]+)$/.exec(url.pathname);
  if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash || !path ||
      issuer !== `${url.origin}${url.pathname}` || /%2f|%5c/i.test(path[2])) {
    throw new KeycloakAccessError("sync_configuration_invalid");
  }
  if (adminOrigin !== undefined) {
    let admin: URL;
    try { admin = new URL(adminOrigin); } catch { throw new KeycloakAccessError("sync_configuration_invalid"); }
    if (admin.protocol !== "https:" || admin.username || admin.password || admin.port ||
        adminOrigin !== admin.origin || isIP(admin.hostname.replace(/^\[|\]$/g, "")) ||
        !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(admin.hostname)) {
      throw new KeycloakAccessError("sync_configuration_invalid");
    }
  }
  return {
    token: `${issuer}/protocol/openid-connect/token`,
    // Preserve the issuer's context path and realm; only the admin host may differ.
    admin: `${adminOrigin ?? url.origin}${path[1]}/admin/realms/${path[2]}`
  };
}

function validateConfig(config: KeycloakAccessConfig) {
  issuerEndpoints(config.issuer, config.adminOrigin);
  if (!config.clientId || !config.clientSecret || !config.clientUuid ||
      !/^[\w.:-]{1,100}$/.test(config.memberRole) || !/^[\w.:-]{1,100}$/.test(config.adminRole) ||
      config.memberRole === config.adminRole) {
    throw new KeycloakAccessError("sync_configuration_invalid");
  }
}

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new KeycloakAccessError("sync_response_invalid");
  return value as Record<string, unknown>;
}

/** Server-only boundary: the caller never exposes credentials, responses, or bearer tokens. */
export function createKeycloakAccessClient(config: KeycloakAccessConfig, fetcher: typeof fetch = fetch) {
  validateConfig(config);
  const endpoints = issuerEndpoints(config.issuer, config.adminOrigin);
  const clientPath = `${endpoints.admin}/clients/${encodeURIComponent(config.clientUuid)}`;
  let bearer: string | undefined;
  const deadline = AbortSignal.timeout(12_000);

  async function request(url: string, init: RequestInit = {}, authenticate = true): Promise<unknown> {
    if (authenticate && !bearer) {
      const payload = object(await request(endpoints.token, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ grant_type: "client_credentials", client_id: config.clientId, client_secret: config.clientSecret })
      }, false));
      if (typeof payload.access_token !== "string" || !payload.access_token || payload.access_token.length > 32_768) {
        throw new KeycloakAccessError("sync_response_invalid");
      }
      bearer = payload.access_token;
    }
    const headers = new Headers(init.headers);
    headers.set("Accept", "application/json");
    if (authenticate) headers.set("Authorization", `Bearer ${bearer}`);
    let response: Response;
    try {
      response = await fetcher(url, { ...init, headers, signal: deadline, redirect: "error", cache: "no-store" });
    } catch {
      throw new KeycloakAccessError(deadline.aborted ? "sync_timeout" : "sync_unavailable");
    }
    if (!response.ok) {
      const code = response.status === 401 || response.status === 403 ? "sync_permission_denied"
        : response.status === 404 ? "sync_resource_missing"
          : response.status === 429 ? "sync_rate_limited" : "sync_unavailable";
      throw new KeycloakAccessError(code);
    }
    if (response.status === 204) return undefined;
    // Never retain or log an unexpected provider body. Bound JSON before decoding.
    const reader = response.body?.getReader();
    if (!reader) throw new KeycloakAccessError("sync_response_invalid");
    const chunks: Uint8Array[] = [];
    let size = 0;
    try {
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        size += chunk.value.length;
        if (size > 131_072) {
          await reader.cancel();
          throw new KeycloakAccessError("sync_response_invalid");
        }
        chunks.push(chunk.value);
      }
      const buffer = new Uint8Array(size);
      let offset = 0;
      for (const chunk of chunks) { buffer.set(chunk, offset); offset += chunk.length; }
      return JSON.parse(new TextDecoder().decode(buffer));
    } catch (error) {
      if (error instanceof KeycloakAccessError) throw error;
      throw new KeycloakAccessError(deadline.aborted ? "sync_timeout" : "sync_response_invalid");
    } finally {
      reader.releaseLock();
    }
  }

  function mappingPath(subject: string) {
    if (!subject || subject.length > 255 || /[\u0000-\u0020\u007f]/.test(subject)) throw new KeycloakAccessError("sync_identity_invalid");
    return `${endpoints.admin}/users/${encodeURIComponent(subject)}/role-mappings/clients/${encodeURIComponent(config.clientUuid)}`;
  }

  function roles(value: unknown): RoleRepresentation[] {
    if (!Array.isArray(value)) throw new KeycloakAccessError("sync_response_invalid");
    return value.map((entry) => {
      const role = object(entry);
      if (typeof role.id !== "string" || typeof role.name !== "string" || role.clientRole !== true || role.containerId !== config.clientUuid) {
        throw new KeycloakAccessError("sync_response_invalid");
      }
      return role as RoleRepresentation;
    });
  }

  async function userEnabled(subject: string): Promise<boolean> {
    mappingPath(subject);
    const user = object(await request(`${endpoints.admin}/users/${encodeURIComponent(subject)}`));
    if (user.id !== subject || typeof user.enabled !== "boolean") throw new KeycloakAccessError("sync_identity_invalid");
    return user.enabled;
  }

  async function read(subject: string): Promise<RemoteAccess> {
    if (!await userEnabled(subject)) return { enabled: false, role: "none" };
    const mapped = roles(await request(`${mappingPath(subject)}/composite`));
    const names = new Set(mapped.map((role) => role.name));
    return { enabled: true, role: names.has(config.adminRole) ? "admin" : names.has(config.memberRole) ? "member" : "none" };
  }

  async function roleByName(name: string): Promise<RoleRepresentation> {
    const role = roles([await request(`${clientPath}/roles/${encodeURIComponent(name)}`)])[0];
    if (role.name !== name || role.composite === true) throw new KeycloakAccessError("sync_role_configuration_invalid");
    return role;
  }

  async function reconcile(subject: string, desired: AccessRole): Promise<RemoteAccess> {
    if (desired !== "none" && desired !== "member" && desired !== "admin") throw new KeycloakAccessError("sync_role_invalid");
    // Never enable an account or edit identities, groups, realm roles, or other clients.
    if (!await userEnabled(subject)) return { enabled: false, role: "none" };
    const path = mappingPath(subject);
    const current = roles(await request(path));
    const wantedNames = desired === "admin" ? [config.memberRole, config.adminRole] : desired === "member" ? [config.memberRole] : [];
    const remove = current.filter((role) => [config.memberRole, config.adminRole].includes(role.name) && !wantedNames.includes(role.name));
    if (remove.length) await request(path, { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify(remove) });
    const add: RoleRepresentation[] = [];
    for (const name of wantedNames) {
      // Validate the owned definitions even when already present: no composite privileges.
      const definition = await roleByName(name);
      if (!current.some((role) => role.id === definition.id)) add.push(definition);
    }
    if (add.length) await request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(add) });
    const result = await read(subject);
    if (result.enabled && result.role !== desired) throw new KeycloakAccessError("sync_mapping_conflict");
    return result;
  }

  return { read, reconcile };
}
