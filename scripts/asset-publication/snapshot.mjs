/** Preserve the pre-publication working bytes in a fresh, ignored mirror. */
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";

const args = process.argv.slice(2);
if (args.length !== 2 || args[0] !== "--output") throw new Error("Usage: node snapshot.mjs --output .private/<fresh-directory>");
const repo = fs.realpathSync(process.cwd());
const destination = path.resolve(repo, args[1]);
const privateRoot = path.join(repo, ".private");
if (!destination.startsWith(privateRoot + path.sep) || fs.existsSync(destination)) throw new Error("A fresh ignored destination is required");
const paths = [...new Set(execFileSync("git", ["ls-files", "--cached", "--others", "--exclude-standard", "-z"], {cwd: repo}).toString().split("\0").filter(Boolean))]
  .filter(file => !file.startsWith("scripts/asset-publication/") && !file.startsWith("tests/asset-publication") && !file.startsWith(".private/"))
  .sort();
if (!paths.length) throw new Error("No repository inputs found");
for (const file of paths) {
  const target = path.resolve(repo, file);
  if (!target.startsWith(repo + path.sep) || !fs.realpathSync(target).startsWith(repo + path.sep) || !fs.lstatSync(target).isFile()) throw new Error(`Not an ordinary repository file: ${file}`);
}
const digest = buffer => createHash("sha256").update(buffer).digest("hex").toUpperCase();
fs.mkdirSync(path.dirname(destination), {recursive: true});
if (!fs.realpathSync(path.dirname(destination)).startsWith(privateRoot + path.sep)) throw new Error("Unexpected destination ancestor");
fs.mkdirSync(destination);
const entries = [];
for (const file of paths) {
  const source = path.join(repo, file), target = path.join(destination, file);
  const before = fs.readFileSync(source);
  fs.mkdirSync(path.dirname(target), {recursive: true});
  fs.copyFileSync(source, target, fs.constants.COPYFILE_EXCL);
  const after = fs.readFileSync(target);
  if (!before.equals(after) || digest(fs.readFileSync(source)) !== digest(before)) throw new Error(`Snapshot race or copy mismatch: ${file}`);
  entries.push({path: file, sha256: digest(after), bytes: after.length});
}
const receipt = {
  schema: "asterion-private-publication-backup-v1",
  source_head: execFileSync("git", ["rev-parse", "HEAD"], {cwd: repo, encoding: "utf8"}).trim(),
  snapshot_script_sha256: digest(fs.readFileSync(new URL(import.meta.url))),
  files: entries,
};
fs.writeFileSync(path.join(destination, "snapshot.json"), JSON.stringify(receipt, null, 2) + "\n", {flag: "wx"});
console.log(JSON.stringify({files: entries.length, bytes: entries.reduce((n, f) => n + f.bytes, 0), copies_byte_identical: true}));
