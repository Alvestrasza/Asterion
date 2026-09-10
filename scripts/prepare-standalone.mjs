import { cp, mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve(import.meta.dirname, "..");
const standalone = resolve(root, ".next", "standalone");

await mkdir(resolve(standalone, ".next"), { recursive: true });
await cp(resolve(root, ".next", "static"), resolve(standalone, ".next", "static"), { recursive: true });
await cp(resolve(root, "public"), resolve(standalone, "public"), { recursive: true });
await mkdir(resolve(standalone, ".asterion-operations"), { recursive: true });
await cp(resolve(root, "deploy", "public", "public-config.mjs"),
  resolve(standalone, ".asterion-operations", "public-config.mjs"));
await cp(resolve(root, "deploy", "public", "run-access-sync.mjs"),
  resolve(standalone, ".asterion-operations", "run-access-sync.mjs"));
await cp(resolve(root, "scripts", "start-standalone.mjs"), resolve(standalone, "start-asterion.mjs"));
