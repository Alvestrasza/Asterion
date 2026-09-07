import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { AMENDMENT_PATH, PUBLICATION_ROOT, RUNTIME_MODELS, main, planRebindings, publishedHash, sha256, verifyPublishedAmendment } from "../scripts/asset-publication/rebind.mjs";

const source = "assets/3d/source/orc/sculpt-v004/orc-sculpt-v004.blend";
const validation = "assets/3d/reference/orc/sculpt-v004/validation.json";
const manifest = "assets/3d/source/orc/sculpt-v004/manifest.json";
const gallery = "assets/3d/reference/companions/sculpt-v004/gallery-manifest.json";
const json = value => Buffer.from(JSON.stringify(value, null, 2) + "\r\n");
const blendProof = candidate => {
  const after = {after_sha256: sha256(candidate), after_bytes: candidate.length};
  const intermediate = Buffer.from("intermediate RNA-only copy");
  const raw = {raw_intermediate_sha256: sha256(intermediate), raw_intermediate_bytes: intermediate.length};
  const semantic = "A".repeat(64), evidence = "B".repeat(64);
  const verifier = "E7FCFFA79AE04C96811B85E54E667198EB571F8CEDB68AD63152B2C4330176EE";
  return {semantic_sha256: semantic, evidence_sha256: evidence,
    source_bytes_unchanged: true, in_memory_semantics_equal: true, reopened_semantics_equal: true, reopened_metadata_portable: true,
    ...raw, raw_semantic_receipt_sha256: "C".repeat(64),
    frozen_semantic_implementation_sha256: "0390542E3A4C5F1B81414E7831716F97F04BBB1AF222CE56C06FD0D132D77175",
    tail_report_sha256: "4E9B1F428D94C7B36BEC60C10AF587105B7258FF3B126C55564C94249B039EE9",
    final_verifier_sha256: verifier,
    final_reopen: {...after, semantic_sha256: semantic, evidence_sha256: evidence, verifier_sha256: verifier, reopened_semantics_equal: true},
    independent_privacy_scan: {...after, verified: true, findings: 0, errors: 0,
      scanner_sha256: "F108F682F56C67FFE9CE23E661EBCB58A6B7B77E0E042437D4244CAC8D97E317"},
    independent_byte_delta: {...raw, ...after, verified: true, all_other_decompressed_bytes_identical: true, allowed_changed_byte_count: 5,
      checker_sha256: "B5C29FC595EEAFC5715EA464A5600AFEC537DC9D6239E24BDC9EDD644BCE4061"},
    tail_cleanup: {schema: "asterion.blender-cstring-tail-proof.v1", blender_header: "BLENDER17-01v0502",
      pointer_bytes: 8, bhead_bytes: 32, decompressed_bytes: 3000,
      sdna_sha256: "C".repeat(64), before_decompressed_sha256: "D".repeat(64), after_decompressed_sha256: "E".repeat(64),
      unchanged_decompressed_segments_sha256: "F".repeat(64),
      all_other_decompressed_bytes_identical: true, only_allowlisted_post_nul_bytes_zeroed: true, live_cstrings_unchanged: true,
      source_bytes_unchanged: true, candidate_readback_verified: true, independently_reopened_in_blender: false,
      code_sha256: "459B391060D86B6AF1262AC7F364B0576D3543AC936717BFB18AC6FC82D83F27",
      fields: [
        {field: "FileSelectParams.dir[1282]", start: 32, end: 1314, bytes: 1282, first_nul_offset: 40, nonzero_tail_bytes: 3, live_cstring_sha256: "A".repeat(64)},
        {field: "RenderData.pic[1024]", start: 1500, end: 2524, bytes: 1024, first_nul_offset: 1540, nonzero_tail_bytes: 2, live_cstring_sha256: "B".repeat(64)}],
      changed_ranges: [{field: "FileSelectParams.dir[1282]", start: 41, end: 44, bytes: 3}, {field: "RenderData.pic[1024]", start: 1541, end: 1543, bytes: 2}],
      zeroed_bytes: 5}};
};
const glbProof = () => ({original_source_unchanged_after_copy: true, candidate_readback_hash_verified: true,
  independent_privacy_scan: {verified: true, findings: 0, errors: 0, scanner_sha256: "A".repeat(64)},
  semantic_json_unchanged_except_allowed_values: true, all_non_json_chunks_byte_identical: true,
  geometry_materials_images_rig_actions_unchanged: true, binary_chunks_sha256: "B".repeat(64),
  interpreted_json_privacy_scan: {verified: true, findings: 0}});

function fixture() {
  const originals = new Map(RUNTIME_MODELS.map((name, i) => [name, Buffer.from(`unchanged-runtime-${i}`)]));
  originals.set(source, Buffer.from("original mesh with workstation metadata"));
  const originalSource = sha256(originals.get(source));
  originals.set(validation, json({schema: "fixture-validation", source_sha256: originalSource,
    original_rig: {rest_sha256: originalSource, actions: {blink: {sha256: originalSource}}},
    face_scope: {protected_geometry_sha256: {chest: originalSource}},
    triangles: 12345, checks: {geometry: true}, passed: true, human_likeness_accepted: false}));
  originals.set(manifest, json({schema: "fixture-manifest", source, source_sha256: originalSource,
    validation, validation_sha256: sha256(originals.get(validation)),
    input_sha256: {[source]: originalSource}, triangles: 12345}));
  originals.set(gallery, json({schema: "fixture-gallery", figures: [{manifest, manifest_sha256: sha256(originals.get(manifest))}]}));
  const candidate = Buffer.from("original mesh with redacted metadata");
  const candidates = new Map([[source, candidate]]);
  const changes = [{path: source, before_sha256: originalSource, after_sha256: sha256(candidate),
    before_bytes: originals.get(source).length, after_bytes: candidate.length, proof: blendProof(candidate)}];
  const settings = () => ({snapshot: {schema: "fixture-originals", source_head: "d".repeat(40),
    files: [...originals].map(([name, bytes]) => ({path: name, bytes: bytes.length, sha256: sha256(bytes)}))},
    changes, readOriginal: name => originals.get(name), readCandidate: name => candidates.get(name)});
  return {originals, candidates, changes, settings};
}

function artifact(plan, name) { return JSON.parse(plan.artifacts.get(name).toString("utf8")); }

function numericFixture() {
  const f = fixture();
  f.originals.set(validation, Buffer.from(`{"source_sha256":"${f.changes[0].before_sha256}",` +
    `"measured_values":{"signed_zero":-0,"decimal_zero":-0.0,"exponent":1.2300e-04,` +
    `"integer":9007199254740993,"fraction":0.12345678901234567890123456789},` +
    `"ordinary_object":{"rawJSON":"-0"},"label":"-0 9007199254740993"}\r\n`));
  const m = JSON.parse(f.originals.get(manifest)); m.validation_sha256 = sha256(f.originals.get(validation)); f.originals.set(manifest, json(m));
  const g = JSON.parse(f.originals.get(gallery)); g.figures[0].manifest_sha256 = sha256(f.originals.get(manifest)); f.originals.set(gallery, json(g));
  return f;
}

test("Metadata rebinding retains exact original numeric tokens without sentinel collisions or signed-zero loss", () => {
  const f = numericFixture(), plan = planRebindings(f.settings());
  const bytes = plan.artifacts.get(validation), current = JSON.parse(bytes);
  assert.ok(Object.is(current.measured_values.signed_zero, -0));
  assert.ok(Object.is(current.measured_values.decimal_zero, -0));
  for (const token of ["-0", "-0.0", "1.2300e-04", "9007199254740993", "0.12345678901234567890123456789"]) {
    assert.ok(bytes.toString("utf8").includes(`: ${token}`), `Original numeric token ${token} must be retained`);
  }
  assert.deepEqual(current.ordinary_object, {rawJSON: "-0"}); assert.equal(current.label, "-0 9007199254740993");
  assert.ok(plan.artifacts.get(current.publication_amendment.authoring_record).equals(f.originals.get(validation)));
});

test("Clean-clone conservation rejects numeric-token normalization even with a rebound document hash", () => {
  const f = numericFixture(), plan = planRebindings(f.settings());
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "asterion-publication-numbers-"));
  try {
    for (const [name, bytes] of new Map([...f.originals, ...f.candidates, ...plan.artifacts])) {
      const target = path.join(temp, name); fs.mkdirSync(path.dirname(target), {recursive: true}); fs.writeFileSync(target, bytes);
    }
    assert.deepEqual(verifyPublishedAmendment(temp), {files: 1, documents: 3, unchanged_runtime_glbs: 8});
    for (const [before, after] of [["\"signed_zero\": -0,", "\"signed_zero\": 0,"],
      ["-0.0,", "-0,"], ["1.2300e-04,", "0.000123,"], ["9007199254740993,", "9007199254740992,"],
      ["0.12345678901234567890123456789", "0.12345678901234568"]]) {
      const text = plan.artifacts.get(validation).toString("utf8"), changedBytes = Buffer.from(text.replace(before, after));
      assert.notEqual(changedBytes.toString("utf8"), text, "The intended numeric mutation occurred");
      fs.writeFileSync(path.join(temp, validation), changedBytes);
      const amended = structuredClone(plan.amendment), entry = amended.documents.find(r => r.path === validation);
      entry.after_sha256 = sha256(changedBytes); entry.after_bytes = changedBytes.length;
      fs.writeFileSync(path.join(temp, AMENDMENT_PATH), json(amended));
      assert.throws(() => verifyPublishedAmendment(temp), /Unchanged authoring evidence was modified/);
    }
  } finally {
    assert.ok(fs.realpathSync(temp).startsWith(fs.realpathSync(os.tmpdir()) + path.sep));
    assert.ok(path.basename(temp).startsWith("asterion-publication-numbers-")); fs.rmSync(temp, {recursive: true});
  }
});

test("Publication receipt DAG rebinds leaf, validation, manifest and gallery without reauthoring evidence", () => {
  const f = fixture(), before = new Map([...f.originals].map(([p, b]) => [p, Buffer.from(b)]));
  const result = planRebindings(f.settings());
  const v = artifact(result, validation), m = artifact(result, manifest), g = artifact(result, gallery);
  const originalValidation = JSON.parse(before.get(validation));
  assert.equal(v.source_sha256, f.changes[0].after_sha256);
  assert.deepEqual(v.original_rig, originalValidation.original_rig);
  assert.deepEqual(v.face_scope, originalValidation.face_scope);
  assert.equal(v.triangles, 12345); assert.equal(v.passed, true); assert.equal(v.human_likeness_accepted, false);
  assert.equal(m.validation_sha256, sha256(result.artifacts.get(validation)));
  assert.equal(m.input_sha256[source], f.changes[0].after_sha256);
  assert.equal(g.figures[0].manifest_sha256, sha256(result.artifacts.get(manifest)));
  assert.match(v.publication_amendment.notice, /not a rerun/);
  assert.equal(v.publication_amendment.original_document_sha256, sha256(before.get(validation)));
  for (const entry of result.amendment.documents) {
    assert.equal(entry.before_sha256, sha256(before.get(entry.path)));
    assert.equal(entry.after_sha256, sha256(result.artifacts.get(entry.path)));
    assert.equal(entry.archive_status, "exact-public-safe-original");
    assert.ok(result.artifacts.get(entry.authoring_record).equals(before.get(entry.path)), "Archive preserves exact CRLF bytes");
    assert.ok(entry.bindings.every(binding => !/original_rig|face_scope/.test(binding.pointer)));
  }
  for (const [p, bytes] of before) assert.ok(bytes.equals(f.originals.get(p)), "Planner never writes original bytes");
  assert.equal(result.amendment.preserved_runtime_glbs.length, 8);
  assert.ok(result.amendment.preserved_runtime_glbs.every(r => sha256(before.get(r.path)) === r.sha256));
  assert.ok([...result.artifacts.keys()].every(p => p.startsWith("assets/3d/")));
  assert.ok(!result.artifacts.has(source), "Receipt planner cannot promote or rewrite source binaries");
});

test("Stale before-hash, changed snapshot bytes and mismatched candidate bytes fail closed", () => {
  const f = fixture();
  f.changes[0].before_sha256 = "F".repeat(64);
  assert.throws(() => planRebindings(f.settings()), /Stale before-hash/);
  const g = fixture(), config = g.settings();
  g.originals.set(source, Buffer.from("changed after snapshot"));
  assert.throws(() => planRebindings(config), /Stale or mismatched bytes/);
  const h = fixture(); h.candidates.set(source, Buffer.from("different output"));
  assert.throws(() => planRebindings(h.settings()), /Stale or mismatched bytes/);
});

test("Ambiguous original SHA with divergent publication outputs is rejected", () => {
  const f = fixture(), other = "assets/3d/source/orc/sculpt-v003/orc-sculpt-v003.blend";
  f.originals.set(other, f.originals.get(source)); f.candidates.set(other, Buffer.from("different redaction"));
  f.changes.push({...f.changes[0], path: other, after_sha256: sha256(f.candidates.get(other)), after_bytes: f.candidates.get(other).length, proof: blendProof(f.candidates.get(other))});
  assert.throws(() => planRebindings(f.settings()), /Ambiguous old SHA mapping/);
});

test("Unexpected absolute/private receipt strings and private proof text cannot enter public archives", () => {
  for (const value of ["Z:/private-machine/asset.blend", "see .private/review/evidence.json", "/home/operator/model.blend"]) {
    const f = fixture(), v = JSON.parse(f.originals.get(validation)); v.note = value; f.originals.set(validation, json(v));
    const m = JSON.parse(f.originals.get(manifest)); m.validation_sha256 = sha256(f.originals.get(validation)); f.originals.set(manifest, json(m));
    const g = JSON.parse(f.originals.get(gallery)); g.figures[0].manifest_sha256 = sha256(f.originals.get(manifest)); f.originals.set(gallery, json(g));
    assert.throws(() => planRebindings(f.settings()), /Unexpected absolute\/private text/);
  }
  const f = fixture(); f.changes[0].proof.path = ".private/raw-evidence.json";
  assert.throws(() => planRebindings(f.settings()), /Unexpected absolute\/private text/);
});

test("Known unsafe legacy receipt is honestly omitted, with hash-bound redaction not a fabricated original archive", () => {
  const f = fixture(), legacy = "assets/3d/source/asterion/asterion-canonical-highpoly-v001-likeness-validation.json";
  const privateOriginal = json({canonical: "Z:/workstation/art/canonical.png", render: "Z:/workstation/work/not-published.png",
    comparison: "Z:/workstation/work/comparison.png", alpha_iou_at_127: 0.875, checks: {registered: true}});
  f.originals.set(legacy, privateOriginal);
  const result = planRebindings(f.settings()), entry = result.amendment.documents.find(r => r.path === legacy), current = artifact(result, legacy);
  assert.equal(entry.before_sha256, sha256(privateOriginal)); assert.equal(entry.authoring_record, null);
  assert.equal(entry.archive_status, "private-original-retained-not-published");
  assert.equal(entry.redactions.length, 3); assert.ok(entry.redactions.every(r => /^[A-F0-9]{64}$/.test(r.before_value_sha256)));
  assert.equal(current.canonical, null); assert.equal(current.render, null); assert.equal(current.alpha_iou_at_127, 0.875);
  assert.equal(current.publication_amendment.authoring_record, null);
  for (const bytes of result.artifacts.values()) assert.doesNotMatch(bytes.toString("utf8"), /Z:\/workstation/);
  assert.ok(!result.artifacts.has(`${PUBLICATION_ROOT}/authoring-records/${legacy}`));
  assert.ok(f.originals.get(legacy).equals(privateOriginal));
});

test("Latest eight runtime GLBs and authoring builders cannot be change-map targets", () => {
  for (const name of [...RUNTIME_MODELS, "assets/3d/source/companions/sculpt-v005/build.py", "public/assets/companions/orc.png"]) {
    const f = fixture(); f.changes[0].path = name;
    assert.throws(() => planRebindings(f.settings()), /Forbidden binary mutation/);
  }
});

test("Only the changed file byte count changes, never geometry or action measurements", () => {
  const f = fixture(), glb = "public/assets/3d/asterion/asterion-highpoly-v001.glb";
  const report = "assets/3d/source/asterion/legacy-file-report.json";
  f.originals.set(glb, Buffer.from("legacy GLB extras")); f.candidates.set(glb, Buffer.from("legacy GLB"));
  f.changes.push({path: glb, before_sha256: sha256(f.originals.get(glb)), before_bytes: f.originals.get(glb).length,
    after_sha256: sha256(f.candidates.get(glb)), after_bytes: f.candidates.get(glb).length, proof: glbProof()});
  f.originals.set(report, json({asset: glb, sha256: sha256(f.originals.get(glb)), file_size_bytes: f.originals.get(glb).length,
    triangles: 100, key_count: 200, mesh: {bytes: 64}, actions_sha256: {blink: sha256(f.originals.get(glb))}}));
  const result = planRebindings(f.settings()), current = artifact(result, report);
  assert.equal(current.file_size_bytes, f.candidates.get(glb).length); assert.equal(current.triangles, 100);
  assert.equal(current.key_count, 200); assert.equal(current.mesh.bytes, 64);
  assert.equal(current.actions_sha256.blink, sha256(f.originals.get(glb)));
});

test("Array collection receipts retain their schema shape and exact complete historical document", () => {
  const f = fixture(), collection = "assets/3d/reference/companions/sculpt-v001/collection-manifest.json";
  f.originals.set(collection, json([{source, source_sha256: f.changes[0].before_sha256, triangles: 42}]));
  const result = planRebindings(f.settings()), candidate = artifact(result, collection);
  assert.ok(Array.isArray(candidate)); assert.equal(candidate.length, 1); assert.equal(candidate[0].triangles, 42);
  assert.equal(candidate[0].source_sha256, f.changes[0].after_sha256);
  assert.ok(result.artifacts.get(candidate[0].publication_amendment.authoring_record).equals(f.originals.get(collection)));
});

test("Immutable hash literal helper requires an exact before-to-after binding and actual published bytes", () => {
  const f = fixture(), result = planRebindings(f.settings()), temp = fs.mkdtempSync(path.join(os.tmpdir(), "asterion-publication-binding-"));
  try {
    fs.mkdirSync(path.dirname(path.join(temp, source)), {recursive: true}); fs.writeFileSync(path.join(temp, source), f.originals.get(source));
    assert.equal(publishedHash(temp, source, f.changes[0].before_sha256), f.changes[0].before_sha256);
    fs.mkdirSync(path.dirname(path.join(temp, AMENDMENT_PATH)), {recursive: true});
    fs.writeFileSync(path.join(temp, AMENDMENT_PATH), result.artifacts.get(AMENDMENT_PATH));
    fs.writeFileSync(path.join(temp, source), f.candidates.get(source));
    assert.equal(publishedHash(temp, source, f.changes[0].before_sha256), f.changes[0].after_sha256);
    assert.throws(() => publishedHash(temp, source, "E".repeat(64)), /authoring anchor/);
    fs.writeFileSync(path.join(temp, source), Buffer.from("tampered"));
    assert.throws(() => publishedHash(temp, source, f.changes[0].before_sha256), /mismatched bytes/);
  } finally {
    // Only this test's independently created, resolved temporary directory is removed.
    assert.ok(fs.realpathSync(temp).startsWith(fs.realpathSync(os.tmpdir()) + path.sep));
    assert.ok(path.basename(temp).startsWith("asterion-publication-binding-"));
    fs.rmSync(temp, {recursive: true});
  }
});

test("Duplicate map entries and escaping paths fail before any candidate write", () => {
  const f = fixture(); f.changes.push({...f.changes[0]}); assert.throws(() => planRebindings(f.settings()), /Duplicate binary mutation/);
  const g = fixture(); g.changes[0].path = "assets/3d/../outside.blend"; assert.throws(() => planRebindings(g.settings()), /Unsafe repository-relative path/);
});

test("A failed or missing reopened Blender equivalence proof cannot be rebound into accepted evidence", () => {
  const f = fixture(); f.changes[0].proof.reopened_semantics_equal = false;
  assert.throws(() => planRebindings(f.settings()), /failed metadata equivalence/);
  const g = fixture(); delete g.changes[0].proof.evidence_sha256;
  assert.throws(() => planRebindings(g.settings()), /Invalid equivalence fingerprint/);
});

test("Final Blender rows reject a raw RNA-only report even when its old semantic checks pass", () => {
  const f = fixture(), p = f.changes[0].proof;
  f.changes[0].proof = Object.fromEntries(["semantic_sha256", "evidence_sha256", "source_bytes_unchanged", "in_memory_semantics_equal", "reopened_semantics_equal", "reopened_metadata_portable"].map(k => [k, p[k]]));
  assert.throws(() => planRebindings(f.settings()), /final Blender|tail|final.*proof/i);
});

for (const [label, mutate] of [
  ["unverified tail bytes", p => { p.tail_cleanup.all_other_decompressed_bytes_identical = false; }],
  ["a false historical stage reopen claim", p => { p.tail_cleanup.independently_reopened_in_blender = true; }],
  ["unknown tail code", p => { p.tail_cleanup.code_sha256 = "F".repeat(64); }],
  ["a live-string write", p => { p.tail_cleanup.changed_ranges[0].start = p.tail_cleanup.fields[0].first_nul_offset; }],
  ["an unapproved SDNA field", p => { p.tail_cleanup.fields[0].field = "Mesh.vertex_data"; }],
  ["a mismatched byte total", p => { p.tail_cleanup.zeroed_bytes++; }],
  ["missing raw intermediate binding", p => { delete p.raw_intermediate_bytes; }],
  ["a stale final reopen", p => { p.final_reopen.after_sha256 = p.raw_intermediate_sha256; }],
  ["a different final semantic fingerprint", p => { p.final_reopen.semantic_sha256 = "F".repeat(64); }],
  ["an unrecognized final verifier", p => { p.final_verifier_sha256 = "F".repeat(64); }],
  ["a stale final privacy scan", p => { p.independent_privacy_scan.after_sha256 = p.raw_intermediate_sha256; }],
  ["nonzero privacy findings", p => { p.independent_privacy_scan.findings = 1; }],
  ["an unknown independent scanner", p => { p.independent_privacy_scan.scanner_sha256 = "F".repeat(64); }],
  ["a stale independent byte delta", p => { p.independent_byte_delta.after_sha256 = p.raw_intermediate_sha256; }],
]) test(`Final Blender publication rejects ${label}`, () => {
  const f = fixture(); mutate(f.changes[0].proof);
  assert.throws(() => planRebindings(f.settings()), /final Blender|tail|final.*proof/i);
});

test("Clean-clone verification detects modified measurements even if the candidate receipt file hash is rebound", () => {
  const f = fixture(), plan = planRebindings(f.settings()), temp = fs.mkdtempSync(path.join(os.tmpdir(), "asterion-publication-verify-"));
  try {
    const overlay = new Map([...f.originals, ...f.candidates, ...plan.artifacts]);
    for (const [name, bytes] of overlay) { const target = path.join(temp, name); fs.mkdirSync(path.dirname(target), {recursive: true}); fs.writeFileSync(target, bytes); }
    assert.deepEqual(verifyPublishedAmendment(temp), {files: 1, documents: 3, unchanged_runtime_glbs: 8});
    const modified = artifact(plan, validation); modified.original_rig.actions.blink.sha256 = "B".repeat(64);
    const changedBytes = json(modified); fs.writeFileSync(path.join(temp, validation), changedBytes);
    const amendment = cloneReceipt(plan.amendment), changed = amendment.documents.find(r => r.path === validation);
    changed.after_sha256 = sha256(changedBytes); changed.after_bytes = changedBytes.length;
    fs.writeFileSync(path.join(temp, AMENDMENT_PATH), json(amendment));
    assert.throws(() => verifyPublishedAmendment(temp), /Unchanged authoring evidence was modified/);
  } finally {
    assert.ok(fs.realpathSync(temp).startsWith(fs.realpathSync(os.tmpdir()) + path.sep));
    assert.ok(path.basename(temp).startsWith("asterion-publication-verify-")); fs.rmSync(temp, {recursive: true});
  }
});

function cloneReceipt(value) { return JSON.parse(JSON.stringify(value)); }

test("An escaping private-directory junction is rejected before mkdir can write through it", () => {
  const f = fixture(), temp = fs.mkdtempSync(path.join(os.tmpdir(), "asterion-publication-junction-"));
  const repo = path.join(temp, "repository"), outside = path.join(temp, "outside"), priorCwd = process.cwd();
  const put = (base, name, bytes) => { const target = path.join(base, name); fs.mkdirSync(path.dirname(target), {recursive: true}); fs.writeFileSync(target, bytes); };
  try {
    const originals = path.join(repo, ".private", "originals"), candidates = path.join(repo, ".private", "binary-candidates");
    for (const [name, bytes] of f.originals) { put(originals, name, bytes); if (RUNTIME_MODELS.includes(name)) put(repo, name, bytes); }
    for (const [name, bytes] of f.candidates) put(candidates, name, bytes);
    put(originals, "snapshot.json", json(f.settings().snapshot));
    put(repo, ".private/report.json", json({schema: "fixture-sanitizer", files: f.changes}));
    fs.mkdirSync(outside);
    fs.symlinkSync(outside, path.join(repo, ".private", "escaping-link"), process.platform === "win32" ? "junction" : "dir");
    process.chdir(repo);
    assert.throws(() => main(["--originals", originals, "--map", path.join(repo, ".private/report.json"),
      "--binary-root", candidates, "--output", path.join(repo, ".private/escaping-link/new/receipt-candidates")]), /Escaping private destination ancestor/);
    assert.deepEqual(fs.readdirSync(outside), [], "Not even a parent directory may be created outside the private root");
  } finally {
    process.chdir(priorCwd);
    assert.ok(fs.realpathSync(temp).startsWith(fs.realpathSync(os.tmpdir()) + path.sep));
    assert.ok(path.basename(temp).startsWith("asterion-publication-junction-")); fs.rmSync(temp, {recursive: true});
  }
});

test("The checkout has untouched authoring receipts or a fully verified publication DAG", () => {
  const root = new URL("../", import.meta.url);
  if (fs.existsSync(new URL(AMENDMENT_PATH, root))) {
    const result = verifyPublishedAmendment(root);
    assert.equal(result.files, 293, "The approved scope is 45 Blender, 246 PNG and two legacy GLB files");
    assert.equal(result.unchanged_runtime_glbs, 8);
  } else {
    assert.equal(fs.existsSync(new URL(PUBLICATION_ROOT, root)), false, "No partial publication directory without its amendment");
    for (const model of RUNTIME_MODELS) {
      const [kind, filename] = model.split("/").slice(-2), version = filename.match(/sculpt-v\d+/)[0];
      const manifest = JSON.parse(fs.readFileSync(new URL(`assets/3d/source/${kind}/${version}/manifest.json`, root)));
      assert.equal(Object.hasOwn(manifest, "publication_amendment"), false, "No amended receipt without the root amendment");
    }
  }
});
