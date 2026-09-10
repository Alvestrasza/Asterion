// Copied to the artifact root by prepare-standalone.mjs. This check runs before
// Next.js can open a listener; instrumentation may initialize lazily.
import { inspectPublicEnvironment, verifyPublicStorageKey } from "./.asterion-operations/public-config.mjs";

if (process.env.ASTERION_DEPLOYMENT_MODE === "public") {
  const { errors } = inspectPublicEnvironment();
  if (errors.length) {
    console.error(`Public deployment configuration rejected:\n${errors.join("\n")}`);
    process.exit(1);
  }
  try { await verifyPublicStorageKey(); }
  catch {
    console.error("Public chat recovery key is unavailable or invalid.");
    process.exit(1);
  }
}

await import("./server.js");
