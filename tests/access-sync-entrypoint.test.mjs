import test from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, mkdir, copyFile, symlink, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

test("sync CLI executes through a release-directory link and remains inert when imported", async () => {
  const root = await mkdtemp(join(tmpdir(), "access-sync-entry-"));
  try {
    const release = join(root, "release with spaces");
    await mkdir(release);
    await copyFile(new URL("../deploy/public/run-access-sync.mjs", import.meta.url), join(release, "worker.mjs"));
    await symlink(release, join(root, "current"), process.platform === "win32" ? "junction" : "dir");
    for (const directory of [join(root, "current"), release]) {
      const result = spawnSync(process.execPath, [join(directory, "worker.mjs")], { env: {}, encoding: "utf8" });
      assert.equal(result.status, 1, `${directory}: missing configuration must not silently succeed`);
      assert.match(result.stderr, /synchronization did not complete/);
      const fixture = 'globalThis.fetch = async () => new Response(JSON.stringify({applied:1,failed:0,blocked:0,skipped:0}));';
      const success = spawnSync(process.execPath, ["--import", `data:text/javascript,${encodeURIComponent(fixture)}`, join(directory, "worker.mjs")], {
        env: { ASTERION_DEPLOYMENT_MODE: "public", ASTERION_INTERNAL_TEST_MODE: "false", ASTERION_ACCESS_SYNC_SECRET: "s".repeat(40) }, encoding: "utf8"
      });
      assert.equal(success.status, 0, success.stderr);
      assert.match(success.stdout, /applied=1 failed=0 blocked=0 skipped=0/);
      assert.doesNotMatch(success.stdout + success.stderr, /ssssssss/);
    }
    const imported = spawnSync(process.execPath, ["--input-type=module", "-e", `await import(${JSON.stringify(new URL("../deploy/public/run-access-sync.mjs", import.meta.url).href)})`], { env: {}, encoding: "utf8" });
    assert.equal(imported.status, 0, imported.stderr);
    assert.equal(imported.stdout + imported.stderr, "");
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
