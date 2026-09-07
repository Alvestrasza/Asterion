/** Promote reviewed publication copies only when their immutable backup agrees. */
import { createHash, randomUUID } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

const sha = bytes => createHash("sha256").update(bytes).digest("hex").toUpperCase();
const within = (root, target) => target.startsWith(root + path.sep);
const permitted = file => /^(assets\/3d|public\/assets\/3d)\//.test(file);

function ordinaryPath(root, relative, { missing = false } = {}) {
  if (!relative || relative.includes("\\") || path.posix.isAbsolute(relative)
      || relative.split("/").some(part => !part || part === "." || part === ".." || part.includes(":"))) {
    throw new Error("Non-canonical relative path");
  }
  let current = root;
  for (const part of relative.split("/")) {
    current = path.join(current, part);
    const status = fs.lstatSync(current, { throwIfNoEntry: false });
    if (status) {
      if (status.isSymbolicLink() || !within(root, fs.realpathSync(current))) {
        throw new Error(`Linked or escaped path: ${relative}`);
      }
    } else if (!missing) throw new Error(`Missing input: ${relative}`);
  }
  const finalStatus = fs.lstatSync(current, { throwIfNoEntry: false });
  if (finalStatus && !finalStatus.isFile()) throw new Error(`Not a file: ${relative}`);
  return current;
}

function filesBelow(root, prefix = "") {
  return fs.readdirSync(path.join(root, prefix), { withFileTypes: true }).flatMap(entry => {
    const relative = prefix + entry.name;
    if (entry.isSymbolicLink()) throw new Error("Candidate links are forbidden");
    if (entry.isDirectory()) return filesBelow(root, relative + "/");
    if (!entry.isFile()) throw new Error("Non-file candidate");
    return [relative];
  });
}

export function planPromotion({ repo, backupRoot, candidateRoot }) {
  repo = fs.realpathSync(repo);
  backupRoot = fs.realpathSync(backupRoot);
  candidateRoot = fs.realpathSync(candidateRoot);
  const privateRoot = path.join(repo, ".private");
  if (!within(privateRoot, backupRoot) || !within(privateRoot, candidateRoot)
      || backupRoot === candidateRoot || within(backupRoot, candidateRoot) || within(candidateRoot, backupRoot)) {
    throw new Error("Separate private backup and candidate mirrors are required");
  }
  const snapshot = JSON.parse(fs.readFileSync(ordinaryPath(backupRoot, "snapshot.json"), "utf8"));
  if (snapshot.schema !== "asterion-private-publication-backup-v1" || !Array.isArray(snapshot.files)) {
    throw new Error("Invalid original snapshot");
  }
  const originals = new Map(snapshot.files.map(item => [item.path, item]));
  if (originals.size !== snapshot.files.length) throw new Error("Duplicate snapshot path");
  const entries = filesBelow(candidateRoot).sort().map(file => {
    if (!permitted(file)) throw new Error(`Outside publication asset scope: ${file}`);
    const candidate = ordinaryPath(candidateRoot, file);
    const destination = ordinaryPath(repo, file, { missing: true });
    const original = originals.get(file);
    let before = null;
    if (original) {
      const backup = fs.readFileSync(ordinaryPath(backupRoot, file));
      before = sha(backup);
      if (before !== original.sha256 || backup.length !== original.bytes) throw new Error(`Backup changed: ${file}`);
      if (!fs.existsSync(destination) || sha(fs.readFileSync(destination)) !== before) throw new Error(`Working source changed: ${file}`);
    } else if (fs.existsSync(destination)) throw new Error(`Unbacked destination exists: ${file}`);
    const afterBytes = fs.readFileSync(candidate);
    return { path: file, before_sha256: before, after_sha256: sha(afterBytes), after_bytes: afterBytes.length };
  });
  if (!entries.length) throw new Error("No publication candidates");
  return { repo, backupRoot, candidateRoot, entries };
}

export function applyPromotion(plan) {
  // Repeat the entire preflight immediately before the first write.
  const fresh = planPromotion(plan);
  if (JSON.stringify(fresh.entries) !== JSON.stringify(plan.entries)) throw new Error("Candidate changed after review");
  for (const entry of fresh.entries) {
    if (entry.before_sha256 === entry.after_sha256) continue;
    const source = ordinaryPath(fresh.candidateRoot, entry.path);
    const destination = ordinaryPath(fresh.repo, entry.path, { missing: true });
    const bytes = fs.readFileSync(source);
    if (sha(bytes) !== entry.after_sha256) throw new Error(`Candidate race: ${entry.path}`);
    if (entry.before_sha256 ? sha(fs.readFileSync(destination)) !== entry.before_sha256 : fs.existsSync(destination)) {
      throw new Error(`Destination race: ${entry.path}`);
    }
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    ordinaryPath(fresh.repo, entry.path, { missing: true });
    const temporary = path.join(path.dirname(destination), `.publication-${randomUUID()}.tmp`);
    fs.writeFileSync(temporary, bytes, { flag: "wx" });
    fs.renameSync(temporary, destination);
    if (sha(fs.readFileSync(destination)) !== entry.after_sha256) throw new Error(`Promotion verification failed: ${entry.path}`);
    if (entry.before_sha256 && sha(fs.readFileSync(ordinaryPath(fresh.backupRoot, entry.path))) !== entry.before_sha256) {
      throw new Error(`Original backup changed: ${entry.path}`);
    }
  }
  return { files: fresh.entries.length, changed: fresh.entries.filter(entry => entry.before_sha256 !== entry.after_sha256).length, originals_preserved: true };
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const argv = process.argv.slice(2), options = { repo: process.cwd() };
  let apply = false;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--apply") { apply = true; continue; }
    const key = { "--backup": "backupRoot", "--candidates": "candidateRoot" }[argv[i]];
    if (!key || !argv[i + 1] || options[key]) throw new Error("Usage: promote.mjs --backup <private-mirror> --candidates <private-mirror> [--apply]");
    options[key] = path.resolve(argv[++i]);
  }
  const plan = planPromotion(options);
  console.log(JSON.stringify(apply ? applyPromotion(plan) : { dry_run: true, files: plan.entries.length, entries: plan.entries }, null, 2));
}
