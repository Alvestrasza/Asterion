import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { applyPromotion, planPromotion } from "../scripts/asset-publication/promote.mjs";

const sha = value => createHash("sha256").update(value).digest("hex").toUpperCase();
function fixture(t) {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), "asterion-promotion-test-"));
  t.after(() => fs.rmSync(repo, { recursive: true, force: true }));
  const backupRoot = path.join(repo, ".private", "originals");
  const candidateRoot = path.join(repo, ".private", "candidate");
  const file = "assets/3d/source/example.blend";
  const put = (root, relative, data) => {
    const output = path.join(root, relative);
    fs.mkdirSync(path.dirname(output), { recursive: true });
    fs.writeFileSync(output, data);
  };
  put(repo, file, "original");
  put(backupRoot, file, "original");
  put(candidateRoot, file, "clean-copy");
  put(backupRoot, "snapshot.json", JSON.stringify({ schema: "asterion-private-publication-backup-v1", files: [{path: file, sha256: sha("original"), bytes: 8}] }));
  return { repo, backupRoot, candidateRoot, file, put };
}

test("publication preflight is read-only; explicit promotion preserves the original", t => {
  const f = fixture(t), plan = planPromotion(f);
  assert.equal(fs.readFileSync(path.join(f.repo, f.file), "utf8"), "original");
  assert.deepEqual(applyPromotion(plan), { files: 1, changed: 1, originals_preserved: true });
  assert.equal(fs.readFileSync(path.join(f.repo, f.file), "utf8"), "clean-copy");
  assert.equal(fs.readFileSync(path.join(f.backupRoot, f.file), "utf8"), "original");
});

test("publication refuses stale working files and stale originals", t => {
  const f = fixture(t);
  f.put(f.repo, f.file, "user-edit");
  assert.throws(() => planPromotion(f), /Working source changed/);
  f.put(f.repo, f.file, "original");
  f.put(f.backupRoot, f.file, "corrupt");
  assert.throws(() => planPromotion(f), /Backup changed/);
});

test("publication fails before writing if candidates change after preflight", t => {
  const f = fixture(t), plan = planPromotion(f);
  f.put(f.candidateRoot, f.file, "changed-again");
  assert.throws(() => applyPromotion(plan), /Candidate changed after review/);
  assert.equal(fs.readFileSync(path.join(f.repo, f.file), "utf8"), "original");
});

test("publication permits new receipt assets, not unrelated paths or unbacked replacements", t => {
  const f = fixture(t), receipt = "assets/3d/publication/example/receipt.json";
  f.put(f.candidateRoot, receipt, "{}");
  assert.equal(planPromotion(f).entries.length, 2);
  f.put(f.repo, receipt, "existing");
  assert.throws(() => planPromotion(f), /Unbacked destination/);
  f.put(f.candidateRoot, "app/unrelated.ts", "not-an-asset");
  assert.throws(() => planPromotion(f), /Outside publication asset scope/);
});

test("publication backup and candidates must be separate private mirrors", t => {
  const f = fixture(t);
  assert.throws(() => planPromotion({ ...f, candidateRoot: f.backupRoot }), /Separate private/);
  assert.throws(() => planPromotion({ ...f, backupRoot: f.repo }), /Separate private/);
});

test("publication refuses directory links in a candidate mirror", t => {
  const f = fixture(t), linked = path.join(f.candidateRoot, "assets", "3d", "linked");
  fs.symlinkSync(f.backupRoot, linked, process.platform === "win32" ? "junction" : "dir");
  assert.throws(() => planPromotion(f), /Candidate links/);
  assert.equal(fs.readFileSync(path.join(f.repo, f.file), "utf8"), "original");
});
