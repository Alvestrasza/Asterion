import { isIP } from "node:net";
import { createCipheriv, createDecipheriv, createHash, randomBytes } from "node:crypto";
import { constants } from "node:fs";
import { lstat, open } from "node:fs/promises";
import { isAbsolute } from "node:path";
import { z } from "zod";
import type { ChatRegistration } from "./chat-crypto.ts";
import type { StorageAttribute, StorageJournal } from "./keycloak-storage-journal.ts";
import { FRIEND_CODE_ALPHABET, FRIEND_CODE_PATTERN } from "./friend-code-policy.ts";

/** Phase 1 escrow is operator-accessible. Never expose this client or its credentials to a browser. */
export class KeycloakStorageError extends Error {
  readonly code: string;
  constructor(code: string) { super(code); this.code = code; this.name = "KeycloakStorageError"; }
}
export type KeycloakStorageConfig = { issuer: string; privateOrigin: string; clientId: string; clientSecret: string; masterKeyFile: string };
export type RecoveryRecord = { subject: string; actorId: string; fingerprint: string; recoveryCode: string; registration: ChatRegistration };
const opaque = (min: number, max: number) => z.string().min(min).max(max).regex(/^[A-Za-z0-9_-]+$/);
const recoverySchema = z.object({
  subject: z.string().min(1).max(255), actorId: z.string().min(1).max(128), fingerprint: opaque(43, 43), recoveryCode: opaque(43, 43),
  registration: z.object({
    identity: z.object({ version: z.literal(1), encryptionKey: opaque(512, 2048), signingKey: opaque(100, 256), fingerprint: opaque(43, 43) }).strict(),
    backup: z.object({ iv: opaque(16, 16), ciphertext: opaque(100, 16384) }).strict(), proof: opaque(86, 86)
  }).strict()
}).strict();

export function keycloakStorageConfigured(environment: NodeJS.ProcessEnv = process.env): boolean {
  return Boolean(environment.ASTERION_KEYCLOAK_STORAGE_CLIENT_ID || environment.ASTERION_KEYCLOAK_STORAGE_CLIENT_SECRET || environment.ASTERION_CHAT_RECOVERY_KEY_FILE);
}
export function keycloakStorageConfig(environment: NodeJS.ProcessEnv = process.env): KeycloakStorageConfig {
  const config = { issuer: environment.AUTH_KEYCLOAK_ISSUER ?? "", privateOrigin: environment.ASTERION_KEYCLOAK_ADMIN_ORIGIN ?? "",
    clientId: environment.ASTERION_KEYCLOAK_STORAGE_CLIENT_ID ?? "", clientSecret: environment.ASTERION_KEYCLOAK_STORAGE_CLIENT_SECRET ?? "",
    masterKeyFile: environment.ASTERION_CHAT_RECOVERY_KEY_FILE ?? "" };
  endpoints(config);
  return config;
}
function endpoints(config: KeycloakStorageConfig) {
  try {
    const issuer = new URL(config.issuer), origin = new URL(config.privateOrigin);
    const hostname = (url: URL) => !isIP(url.hostname.replace(/^\[|\]$/g, "")) && /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(url.hostname);
    if (issuer.protocol !== "https:" || issuer.username || issuer.password || issuer.search || issuer.hash || issuer.port ||
      config.issuer !== `${issuer.origin}${issuer.pathname}` || !hostname(issuer) || !/\/realms\/[^/]+$/.test(issuer.pathname) || /%2f|%5c|\.{2}/i.test(issuer.pathname) ||
      origin.protocol !== "https:" || origin.username || origin.password || origin.port || config.privateOrigin !== origin.origin || !hostname(origin) ||
      !/^[A-Za-z0-9_.-]{1,100}$/.test(config.clientId) || !config.clientSecret || config.clientSecret.length > 4096 ||
      !config.masterKeyFile || !isAbsolute(config.masterKeyFile)) throw new Error();
    return { token: `${config.issuer}/protocol/openid-connect/token`, storage: `${origin.origin}${issuer.pathname.replace(/\/realms\//, "/admin/realms/")}` };
  } catch { throw new KeycloakStorageError("storage_configuration_invalid"); }
}

/** The journal grants at most ONE HTTP PUT per immutable field, across all web nodes.
 * A missing value after an uncertain write is intentionally unavailable, not recreated.
 * Keycloak has no attribute CAS: other profile writers must not overlap provisioning.
 */
export function createKeycloakStorageClient(config: KeycloakStorageConfig, fetcher: typeof fetch = fetch, journal?: StorageJournal) {
  const urls = endpoints(config);
  let bearer: string | undefined;
  async function request(url: string, method = "GET", body?: unknown, auth = true): Promise<unknown | null> {
    if (auth && !bearer) {
      const token = await request(urls.token, "POST", new URLSearchParams({ grant_type: "client_credentials", client_id: config.clientId, client_secret: config.clientSecret }), false);
      if (!token || typeof token !== "object" || !("access_token" in token) || typeof token.access_token !== "string" || !token.access_token || token.access_token.length > 32768)
        throw new KeycloakStorageError("storage_response_invalid");
      bearer = token.access_token;
    }
    const headers = new Headers({ Accept: "application/json" });
    if (auth) headers.set("Authorization", `Bearer ${bearer}`);
    if (body !== undefined) headers.set("Content-Type", auth ? "application/json" : "application/x-www-form-urlencoded");
    const signal = AbortSignal.timeout(6000);
    let response: Response;
    try {
      response = await fetcher(url, { method, headers, body: body === undefined ? undefined : auth ? JSON.stringify(body) : body as URLSearchParams,
        redirect: "error", cache: "no-store", signal });
    } catch { throw new KeycloakStorageError(signal.aborted ? "storage_timeout" : "storage_unavailable"); }
    if (auth && method === "GET" && response.status === 404) {
      await response.body?.cancel().catch(() => {});
      throw new KeycloakStorageError("storage_identity_invalid");
    }
    if (!response.ok) {
      const code = response.status === 409 ? "storage_conflict" : [401, 403].includes(response.status) ? "storage_permission_denied" : response.status === 429 ? "storage_rate_limited" : "storage_unavailable";
      // Never decode, retain or log error bodies from the identity system.
      await response.body?.cancel().catch(() => {});
      throw new KeycloakStorageError(code);
    }
    if (auth && method === "PUT" && response.status === 204) return null;
    const reader = response.body?.getReader();
    if (!reader) throw new KeycloakStorageError("storage_response_invalid");
    const chunks: Uint8Array[] = []; let size = 0;
    try {
      while (true) {
        const chunk = await reader.read(); if (chunk.done) break;
        size += chunk.value.length;
        if (size > 131072) { await reader.cancel(); throw new Error(); }
        chunks.push(chunk.value);
      }
      const bytes = new Uint8Array(size); let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
      return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
    } catch { throw new KeycloakStorageError(signal.aborted ? "storage_timeout" : "storage_response_invalid"); }
    finally { reader.releaseLock(); }
  }
  function userPath(subject: string) {
    if (!/^[A-Za-z0-9:_-]{1,255}$/.test(subject)) throw new KeycloakStorageError("storage_identity_invalid");
    return `${urls.storage}/users/${encodeURIComponent(subject)}`;
  }
  function record(value: unknown, subject: string): RecoveryRecord {
    const parsed = recoverySchema.safeParse(value);
    if (!parsed.success || parsed.data.subject !== subject || parsed.data.fingerprint !== parsed.data.registration.identity.fingerprint)
      throw new KeycloakStorageError("storage_response_invalid");
    return parsed.data;
  }
  const userSchema = z.object({
    id: z.string(), username: z.string().min(1).max(255), email: z.string().max(320).nullable().optional(),
    firstName: z.string().max(1024).nullable().optional(), lastName: z.string().max(1024).nullable().optional(),
    attributes: z.record(z.string().max(255), z.array(z.string().max(40000)).max(128)).optional()
  });
  type User = z.infer<typeof userSchema>;
  function ledger() { if (!journal) throw new KeycloakStorageError("storage_configuration_invalid"); return journal; }
  const digest = (value: string) => createHash("sha256").update(value, "utf8").digest("hex");
  async function user(subject: string): Promise<User> {
    const parsed = userSchema.safeParse(await request(userPath(subject)));
    if (!parsed.success || parsed.data.id !== subject) throw new KeycloakStorageError("storage_response_invalid");
    // GET /users/{id} can omit unmanaged attributes. Omitting them from PUT
    // would remove data belonging to another integration.
    const unmanaged = z.record(z.string().max(255), z.array(z.string().max(40000)).max(128)).safeParse(
      await request(`${userPath(subject)}/unmanagedAttributes`));
    if (!unmanaged.success) throw new KeycloakStorageError("storage_response_invalid");
    const attributes = { ...unmanaged.data, ...parsed.data.attributes };
    for (const [name, values] of Object.entries(unmanaged.data)) {
      const managed = parsed.data.attributes?.[name];
      if (managed && JSON.stringify(managed) !== JSON.stringify(values)) throw new KeycloakStorageError("storage_conflict");
    }
    if (Object.keys(attributes).length > 128) throw new KeycloakStorageError("storage_response_invalid");
    parsed.data.attributes = attributes;
    return parsed.data;
  }
  function attribute(snapshot: User, name: StorageAttribute): string | null {
    const values = snapshot.attributes?.[name];
    if (values === undefined) return null;
    if (values.length !== 1 || !values[0]) throw new KeycloakStorageError("storage_response_invalid");
    return values[0];
  }
  async function observed(subject: string, name: StorageAttribute, snapshot: User): Promise<string | null> {
    const entry = await ledger().get(subject, name), value = attribute(snapshot, name);
    if (!entry) {
      if (value !== null) throw new KeycloakStorageError("storage_conflict");
      return null;
    }
    if (value === null) throw new KeycloakStorageError(entry.confirmed ? "storage_conflict" : "storage_write_pending");
    if (entry.digest !== digest(value)) throw new KeycloakStorageError("storage_conflict");
    if (!entry.confirmed) await ledger().confirm(subject, name, entry.digest);
    return value;
  }
  async function create(subject: string, name: StorageAttribute, value: string, snapshot: User): Promise<string> {
    const existing = await observed(subject, name, snapshot);
    if (existing !== null) return existing;
    if (name === "starfriends_chat_recovery") {
      // Check the actual GET snapshot as well as the DB prerequisite. Otherwise a
      // GET started before friend-code confirmation could erase that new field.
      const friend = await observed(subject, "starfriends_friend_code", snapshot);
      if (!friend || !FRIEND_CODE_PATTERN.test(friend)) throw new KeycloakStorageError("storage_write_pending");
    }
    const hash = digest(value);
    const reservation = await ledger().reserve(subject, name, hash, name === "starfriends_friend_code" ? hash : undefined);
    if (!reservation.owned) {
      const winner = await observed(subject, name, await user(subject));
      if (winner === null) throw new KeycloakStorageError("storage_write_pending");
      return winner;
    }
    // Preserve all visible attributes and profile fields required by USER_API
    // validation, but never echo roles, enabled, credentials or required actions.
    const { id: _id, attributes, ...profile } = snapshot;
    try {
      await request(userPath(subject), "PUT", { ...profile, attributes: { ...attributes, [name]: [value] } });
    } catch {
      // An error/timeout is NOT proof that the PUT did not commit. Never retry it.
      // A read can acknowledge the single attempt; absence keeps the durable gate.
      const committed = await observed(subject, name, await user(subject));
      if (committed === null) throw new KeycloakStorageError("storage_write_pending");
      return committed;
    }
    const committed = await observed(subject, name, await user(subject));
    if (committed === null) throw new KeycloakStorageError("storage_write_pending");
    return committed;
  }
  async function masterKey(): Promise<Buffer> {
    let handle;
    try {
      if (!(await lstat(config.masterKeyFile)).isFile()) throw new Error();
      handle = await open(config.masterKeyFile, constants.O_RDONLY | (constants.O_NOFOLLOW ?? 0));
      const info = await handle.stat();
      if (!info.isFile() || info.size < 43 || info.size > 45 || (process.platform !== "win32" && (info.mode & 0o027) !== 0)) throw new Error();
      const raw = await handle.readFile();
      const encoded = raw.toString("utf8").replace(/\r?\n$/, ""); raw.fill(0);
      const key = Buffer.from(encoded, "base64url");
      if (!/^[A-Za-z0-9_-]{43}$/.test(encoded) || key.length !== 32 || key.toString("base64url") !== encoded) { key.fill(0); throw new Error(); }
      return key;
    } catch { throw new KeycloakStorageError("storage_key_unavailable"); }
    finally { await handle?.close().catch(() => {}); }
  }
  const aad = (subject: string, actorId: string) => Buffer.from(JSON.stringify(["starfriends-chat-recovery", 1, config.issuer, subject, actorId]), "utf8");
  async function seal(subject: string, candidate: RecoveryRecord): Promise<string> {
    const key = await masterKey();
    try {
      const iv = randomBytes(12), cipher = createCipheriv("aes-256-gcm", key, iv);
      cipher.setAAD(aad(subject, candidate.actorId));
      const plaintext = Buffer.from(JSON.stringify(candidate), "utf8");
      try {
        const data = Buffer.concat([cipher.update(plaintext), cipher.final()]);
        return JSON.stringify({ v: 1, actorId: candidate.actorId, iv: iv.toString("base64url"), tag: cipher.getAuthTag().toString("base64url"), data: data.toString("base64url") });
      } finally { plaintext.fill(0); }
    } finally { key.fill(0); }
  }
  async function unseal(subject: string, value: string): Promise<RecoveryRecord> {
    const key = await masterKey();
    try {
      const envelope = z.object({ v: z.literal(1), actorId: z.string().min(1).max(128), iv: opaque(16, 16), tag: opaque(22, 22), data: opaque(100, 39000) }).strict().parse(JSON.parse(value));
      const decipher = createDecipheriv("aes-256-gcm", key, Buffer.from(envelope.iv, "base64url"));
      decipher.setAAD(aad(subject, envelope.actorId)); decipher.setAuthTag(Buffer.from(envelope.tag, "base64url"));
      const plaintext = Buffer.concat([decipher.update(Buffer.from(envelope.data, "base64url")), decipher.final()]);
      try {
        const result = record(JSON.parse(plaintext.toString("utf8")), subject);
        if (result.actorId !== envelope.actorId) throw new Error();
        return result;
      }
      finally { plaintext.fill(0); }
    } catch { throw new KeycloakStorageError("storage_response_invalid"); }
    finally { key.fill(0); }
  }
  return {
    async ensureFriendCode(subject: string): Promise<string> {
      userPath(subject); ledger();
      const snapshot = await user(subject), previous = await observed(subject, "starfriends_friend_code", snapshot);
      const symbols = Array.from(randomBytes(13), byte => FRIEND_CODE_ALPHABET[byte & 31]).join("");
      const candidate = `${symbols.slice(0, 5)}-${symbols.slice(5, 8)}-${symbols.slice(8)}`;
      const value = previous ?? await create(subject, "starfriends_friend_code", candidate, snapshot);
      if (!FRIEND_CODE_PATTERN.test(value)) throw new KeycloakStorageError("storage_response_invalid");
      return value;
    },
    async readRecovery(subject: string): Promise<RecoveryRecord | null> {
      userPath(subject); ledger();
      const value = await observed(subject, "starfriends_chat_recovery", await user(subject));
      return value === null ? null : unseal(subject, value);
    },
    async createRecovery(subject: string, candidate: Omit<RecoveryRecord, "subject">): Promise<RecoveryRecord> {
      userPath(subject); ledger();
      const parsed = record({ ...candidate, subject }, subject), snapshot = await user(subject);
      const previous = await observed(subject, "starfriends_chat_recovery", snapshot);
      const value = previous ?? await create(subject, "starfriends_chat_recovery", await seal(subject, parsed), snapshot);
      return unseal(subject, value);
    }
  };
}
