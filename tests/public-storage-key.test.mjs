// Asterion startup key acceptance, v1.0.0, 2026-09-09; Alice Endelgard.
// Synthetic fixtures only. Never read a real environment or master key.
import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, writeFile, chmod, symlink, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { verifyPublicStorageKey } from "../deploy/public/public-config.mjs";

test("storage-off startup does not require a key", async () => {
  await verifyPublicStorageKey({});
});

test("startup key check accepts canonical bytes and rejects absent or malformed files without details", { skip: process.platform === "win32" }, async () => {
  // Production accepts POSIX paths; exercise the real filesystem contract on Linux.
  const dir = await mkdtemp(join(tmpdir(), "asterion-startup-key-"));
  const path = join(dir, "key");
  const env = { ASTERION_CHAT_RECOVERY_KEY_FILE: path };
  const encoded = Buffer.alloc(32, 7).toString("base64url");
  try {
    await assert.rejects(verifyPublicStorageKey(env), { message: "Public chat recovery key is unavailable or invalid." });
    for (const suffix of ["", "\n", "\r\n"]) {
      await writeFile(path, encoded + suffix, { mode: 0o600 });
      await verifyPublicStorageKey(env);
    }
    for (const malformed of ["", encoded + "=", encoded + "x", "!".repeat(43), "A".repeat(42) + "B"]) {
      await writeFile(path, malformed);
      await assert.rejects(verifyPublicStorageKey(env), { message: "Public chat recovery key is unavailable or invalid." });
    }
    await writeFile(path, encoded);
    await chmod(path, 0o644);
    await assert.rejects(verifyPublicStorageKey(env));
    await chmod(path, 0o640);
    await verifyPublicStorageKey(env);
    const link = join(dir, "link");
    await symlink(path, link);
    await assert.rejects(verifyPublicStorageKey({ ASTERION_CHAT_RECOVERY_KEY_FILE: link }));
    await assert.rejects(verifyPublicStorageKey({ ASTERION_CHAT_RECOVERY_KEY_FILE: dir }));
  } finally { await rm(dir, { recursive: true, force: true }); }
});
