import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";

const root = new URL("../", import.meta.url);
const file = path => readFile(new URL(path, root));
const json = async path => JSON.parse(await file(path));
const sha = bytes => createHash("sha256").update(bytes).digest("hex").toUpperCase();
const kinds = ["asterion", "pony", "rabbit", "cat", "dog", "orc", "fairy", "elf"];

test("face comparison binds approved crops, matched old/new GLB views and delivered manifests", async () => {
  const gallery = await json("assets/3d/reference/companions/sculpt-v005/gallery-manifest.json");
  assert.equal(gallery.schema, "asterion-face-comparison-v1");
  assert.equal(gallery.source_files_modified, false);
  assert.equal(gallery.independent_framing, true);
  assert.equal(gallery.likeness_accepted, false);
  assert.equal(gallery.gallery, "assets/3d/reference/companions/sculpt-v005/face-comparison.jpg");
  assert.equal(sha(await file(gallery.gallery)), gallery.sha256);
  assert.equal(sha(await file("assets/3d/source/companions/sculpt-v005/gallery.py")), gallery.assembly_script_sha256);
  assert.deepEqual(gallery.figures.map(figure => figure.kind), kinds);
  for (const figure of gallery.figures) {
    const revision = figure.kind === "asterion" ? "sculpt-v006" : "sculpt-v005";
    assert.equal(figure.manifest, `assets/3d/source/${figure.kind}/${revision}/manifest.json`);
    for (const field of ["manifest", "reference", "previous", "current", "comparison"])
      assert.equal(sha(await file(figure[field])), figure[`${field}_sha256`], field);
    const manifest = await json(figure.manifest);
    assert.equal(figure.reference, manifest.reference);
    assert.equal(figure.reference_sha256, manifest.reference_sha256);
    assert.equal(figure.previous, manifest.baseline_renders["face-hero"].file);
    assert.equal(figure.previous_sha256, manifest.baseline_renders["face-hero"].sha256);
    assert.equal(figure.current, manifest.import_renders["face-hero"].file);
    assert.equal(figure.current_sha256, manifest.import_renders["face-hero"].sha256);
    for (const crop of [figure.reference_crop, figure.render_crop]) {
      assert.equal(crop.length, 4);
      assert.ok(crop.every(Number.isInteger));
      assert.ok(crop[0] >= 0 && crop[1] >= 0 && crop[0] < crop[2] && crop[1] < crop[3]);
    }
  }
});
