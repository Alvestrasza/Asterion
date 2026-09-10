import { fileURLToPath } from "node:url";
import { realpathSync } from "node:fs";

// Called only by the root-installed oneshot unit; never put the bearer in argv.
// The public Nginx listener rejects this route, including requests from the LB.
export async function requestAccessSynchronization(environment = process.env, request = fetch, report = () => {}) {
  const secret = environment.ASTERION_ACCESS_SYNC_SECRET;
  if (environment.ASTERION_DEPLOYMENT_MODE !== "public" ||
      environment.ASTERION_INTERNAL_TEST_MODE !== "false" ||
      !secret || !/^[A-Za-z0-9_+\/=\-]{32,256}$/.test(secret)) return false;
  try {
    const response = await request("http://127.0.0.1:3012/api/internal/access-sync", {
      method: "POST",
      headers: { Authorization: `Bearer ${secret}` },
      redirect: "error",
      signal: AbortSignal.timeout(110_000)
    });
    if (!response.ok) {
      await response.body?.cancel();
      return false;
    }
    const counts = await response.json();
    const fields = ["applied", "failed", "blocked", "skipped"];
    if (!counts || typeof counts !== "object" || fields.some((key) =>
      !Number.isSafeInteger(counts[key]) || counts[key] < 0 || counts[key] > 20) ||
      fields.reduce((sum, key) => sum + counts[key], 0) > 20) return false;
    // Only allowlisted integer counters may leave the protected API boundary.
    report(`applied=${counts.applied} failed=${counts.failed} blocked=${counts.blocked} skipped=${counts.skipped}`);
    return counts.failed === 0 && counts.blocked === 0;
  } catch {
    return false;
  }
}

// Node resolves the main module's URL, while argv retains deployment symlinks.
if (process.argv[1] && realpathSync(fileURLToPath(import.meta.url)) === realpathSync(process.argv[1])) {
  if (await requestAccessSynchronization(process.env, fetch, (summary) => process.stdout.write(`Permission synchronization: ${summary}\n`))) {
    process.stdout.write("Permission synchronization request completed.\n");
  } else {
    process.stderr.write("Permission synchronization did not complete; check protected configuration and service health.\n");
    process.exitCode = 1;
  }
}
