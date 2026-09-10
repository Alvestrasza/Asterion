import { canonicalOrigin, isPublicDeployment } from "./deployment-config.ts";

export function hasSameOrigin(request: Request, environment: Record<string, string | undefined> = process.env) {
  const origin = request.headers.get("origin");
  if (!origin) return false;

  try {
    const supplied = new URL(origin);
    if (supplied.origin !== origin || supplied.username || supplied.password) return false;
    if (isPublicDeployment(environment)) return origin === canonicalOrigin(environment);
    // The internal proxy replaces Host and forwards the original origin. Public
    // traffic never uses this branch and never trusts request-supplied hosts.
    const host = request.headers.get("host");
    const forwarded = request.headers.get("x-forwarded-host");
    const local = new URL(request.url);
    return origin === local.origin || (
      environment.ASTERION_INTERNAL_TEST_MODE === "true" &&
      supplied.protocol === "http:" && Boolean(host) &&
      !forwarded?.includes(",") && supplied.host === (forwarded ?? host)
    );
  } catch {
    return false;
  }
}

export async function readBoundedJson(request: Request, limit = 16_384): Promise<unknown> {
  if (request.headers.get("content-type")?.split(";")[0].trim().toLowerCase() !== "application/json") throw new Error("invalid_json");
  const reader = request.body?.getReader();
  if (!reader) throw new Error("invalid_json");
  const chunks: Uint8Array[] = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.byteLength;
      if (length > limit) { await reader.cancel(); throw new Error("body_too_large"); }
      chunks.push(value);
    }
  } finally { reader.releaseLock(); }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
}
