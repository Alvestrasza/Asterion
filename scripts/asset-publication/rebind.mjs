/** Offline, evidence-preserving metadata publication. Never promotes production files. */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const PUBLICATION_ROOT = "assets/3d/publication/2026-09-07";
export const AMENDMENT_PATH = `${PUBLICATION_ROOT}/amendment.json`;
export const RUNTIME_MODELS = ["asterion", "pony", "rabbit", "cat", "dog", "orc", "fairy", "elf"]
  .map(kind => `public/assets/3d/${kind}/${kind}-sculpt-v00${kind === "asterion" ? 6 : 5}.glb`);
const ID = "metadata-clean-2026-09-07";
const NOTICE = "Metadata-only publication derivative, not a rerun of the historical builder or validator. File digest and size bindings identify publication copies; all measured geometry, materials, rig, action, motion and acceptance evidence remains historical and unchanged. Consult the original authoring record and amendment binding log.";
const DIGEST = /^[A-Fa-f0-9]{64}$/;
const FILE_HASH_KEYS = new Set(["source_sha256", "master_sha256", "glb_sha256", "model_sha256",
  "reference_sha256", "baseline_sha256", "baseline_master_sha256", "baseline_glb_sha256",
  "baseline_source_sha256", "baseline_model_sha256", "manifest_sha256", "validation_sha256",
  "previous_sha256", "current_sha256", "canonical_sha256", "render_sha256", "blend_sha256", "comparison_sha256"]);
const HASH_MAP_KEYS = new Set(["input_sha256", "builder_sha256", "dependency_sha256"]);
const PROTECTED = /(?:^|_)(?:rig|rest|action|animation|geometry|material|fingerprint|behavior|strand|ocular)(?:_|$)/i;
const LEGACY = "assets/3d/source/asterion/asterion-canonical-highpoly-v001";
const REDACTIONS = new Map([
  [`${LEGACY}-report.json`, new Set(["/canonical/path", "/outputs/blend", "/outputs/glb",
    ...["canonical-side", "hero", "front", "rear-three-quarter", "blink", "happy", "sleep", "walk", "canonical-registration"].map(v => `/outputs/renders/${v}`)])],
  [`${LEGACY}-glb-validation.json`, new Set(["/asset", "/renders/idle", "/renders/blink", "/renders/walk"])],
  [`${LEGACY}-likeness-validation.json`, new Set(["/canonical", "/render", "/comparison"])],
]);

export const sha256 = bytes => createHash("sha256").update(bytes).digest("hex").toUpperCase();
const jsonBytes = value => Buffer.from(JSON.stringify(value, null, 2) + "\n");
const pointer = parts => "/" + parts.map(s => String(s).replaceAll("~", "~0").replaceAll("/", "~1")).join("/");
const clone = value => structuredClone(value);
// Node 22 preserves each numeric source token explicitly: -0, exponents and integers
// beyond Number.MAX_SAFE_INTEGER must not be normalized by a metadata-only amendment.
const losslessNumbers = bytes => JSON.parse(bytes.toString("utf8"), (_key, value, context) =>
  typeof value === "number" ? JSON.rawJSON(context.source) : value);
const assetPath = value => /^(?:assets\/3d\/|public\/assets\/3d\/)/.test(value);

export function relativePath(value) {
  if (typeof value !== "string" || !value || value.includes("\\") || value.includes("\0") ||
      value.startsWith("/") || value.includes(":") || value.split("/").some(p => !p || p === "." || p === "..")) {
    throw new Error("Unsafe repository-relative path");
  }
  return value;
}

function unsafeText(value) {
  return typeof value === "string" && (/(?:\b[A-Za-z]:[\\/]|\.private[\\/]|(?:^|[\s"'])\/(?:Users|home|tmp|mnt|private)\/|\\\\[^\s\\]+\\)/i.test(value) || /(?:^|\/)\.\.(?:\/|$)/.test(value));
}

function publicSafe(value, context) {
  if (typeof value === "string" && unsafeText(value)) throw new Error(`Unexpected absolute/private text: ${context}`);
  if (value && typeof value === "object") {
    for (const [key, item] of Object.entries(value)) {
      if (unsafeText(key)) throw new Error(`Unexpected absolute/private key: ${context}`);
      publicSafe(item, `${context}/${key}`);
    }
  }
}

function fileBinding(parts, parent) {
  const key = parts.at(-1);
  // Digests of evaluated data are not digests of files, even if equal by coincidence.
  if (parts.slice(0, -1).some(p => PROTECTED.test(p)) || PROTECTED.test(key) && !FILE_HASH_KEYS.has(key)) return false;
  if (HASH_MAP_KEYS.has(parts.at(-2))) return true;
  if (FILE_HASH_KEYS.has(key)) return true;
  return key === "sha256" && ["file", "path", "asset", "gallery"].some(k => typeof parent[k] === "string");
}

function explicitTarget(parts, parent) {
  const key = parts.at(-1);
  if (HASH_MAP_KEYS.has(parts.at(-2))) return key;
  const candidates = key === "sha256" ? ["file", "path", "asset", "gallery"] : [key.replace(/_sha256$/, "")];
  for (const k of candidates) {
    const v = parent[k];
    if (typeof v === "string" && /^(?:assets\/|public\/)/.test(v)) return relativePath(v);
  }
  return null;
}

function verifyBytes(bytes, expected, label) {
  if (!Buffer.isBuffer(bytes) || bytes.length !== expected.bytes || sha256(bytes) !== expected.sha256.toUpperCase()) {
    throw new Error(`Stale or mismatched bytes: ${label}`);
  }
}

// This is one approved, frozen migration, not an extensible sanitizer trust policy.
const BLENDER_FINAL_TOOLS = Object.freeze({
  semantic: "0390542E3A4C5F1B81414E7831716F97F04BBB1AF222CE56C06FD0D132D77175",
  tails: "459B391060D86B6AF1262AC7F364B0576D3543AC936717BFB18AC6FC82D83F27",
  reopen: "E7FCFFA79AE04C96811B85E54E667198EB571F8CEDB68AD63152B2C4330176EE",
  scanner: "F108F682F56C67FFE9CE23E661EBCB58A6B7B77E0E042437D4244CAC8D97E317",
  byteDelta: "B5C29FC595EEAFC5715EA464A5600AFEC537DC9D6239E24BDC9EDD644BCE4061",
  tailReport: "4E9B1F428D94C7B36BEC60C10AF587105B7258FF3B126C55564C94249B039EE9",
});

function validateFinalBlenderProof(row) {
  const p = row.proof, tail = p.tail_cleanup, reopened = p.final_reopen;
  const check = (condition, label) => {
    if (!condition) throw new Error(`Invalid final Blender publication proof: ${label} (${row.path})`);
  };
  const hash = value => typeof value === "string" && DIGEST.test(value);
  const count = value => Number.isSafeInteger(value) && value >= 0;
  check(tail && reopened, "tail cleanup and final reopen are required");
  check(p.frozen_semantic_implementation_sha256 === BLENDER_FINAL_TOOLS.semantic &&
    p.final_verifier_sha256 === BLENDER_FINAL_TOOLS.reopen && p.tail_report_sha256 === BLENDER_FINAL_TOOLS.tailReport,
  "unrecognized frozen implementation or tail report");
  check(hash(p.raw_semantic_receipt_sha256) && hash(p.raw_intermediate_sha256) && count(p.raw_intermediate_bytes) &&
    p.raw_intermediate_bytes > 0 && p.raw_intermediate_sha256 !== row.before_sha256 &&
    p.raw_intermediate_sha256 !== row.after_sha256, "missing or substituted original/intermediate/final chain");
  check(reopened.after_sha256 === row.after_sha256 && reopened.after_bytes === row.after_bytes &&
    reopened.semantic_sha256 === p.semantic_sha256 && reopened.verifier_sha256 === p.final_verifier_sha256 &&
    reopened.evidence_sha256 === p.evidence_sha256 && reopened.reopened_semantics_equal === true,
  "final reopen does not bind the final file and original semantic fingerprint");
  check(tail.schema === "asterion.blender-cstring-tail-proof.v1" && tail.blender_header === "BLENDER17-01v0502" &&
    tail.pointer_bytes === 8 && tail.bhead_bytes === 32 && tail.code_sha256 === BLENDER_FINAL_TOOLS.tails,
  "unrecognized SDNA format or tail implementation");
  check(["all_other_decompressed_bytes_identical", "only_allowlisted_post_nul_bytes_zeroed", "live_cstrings_unchanged",
    "source_bytes_unchanged", "candidate_readback_verified"].every(key => tail[key] === true), "missing tail byte-preservation assertion");
  // The byte-only stage did not use Blender. Its historical false value must never be rewritten.
  check(tail.independently_reopened_in_blender === false, "tail-stage history falsely claims an independent Blender reopen");
  check(["sdna_sha256", "before_decompressed_sha256", "after_decompressed_sha256", "unchanged_decompressed_segments_sha256"]
    .every(key => hash(tail[key])) && tail.before_decompressed_sha256 !== tail.after_decompressed_sha256,
  "missing or contradictory decompressed byte fingerprints");
  check(count(tail.decompressed_bytes) && tail.decompressed_bytes > 0 && count(tail.zeroed_bytes) && tail.zeroed_bytes > 0,
    "missing decompressed byte counts");
  const expected = new Map([["FileSelectParams.dir[1282]", 1282], ["RenderData.pic[1024]", 1024]]);
  check(Array.isArray(tail.fields) && tail.fields.length === 2 && new Set(tail.fields.map(f => f.field)).size === 2 &&
    tail.fields.every(f => expected.has(f.field)), "unexpected SDNA metadata field scope");
  const fields = new Map(); let previousFieldEnd = -1;
  for (const field of tail.fields) {
    check(["start", "end", "bytes", "first_nul_offset", "nonzero_tail_bytes"].every(k => count(field[k])) &&
      field.bytes === expected.get(field.field) && field.end - field.start === field.bytes && field.start >= previousFieldEnd &&
      field.start <= field.first_nul_offset && field.first_nul_offset < field.end && field.end <= tail.decompressed_bytes &&
      field.nonzero_tail_bytes <= field.end - field.first_nul_offset - 1 && hash(field.live_cstring_sha256),
    "invalid field interval, live string or NUL boundary");
    previousFieldEnd = field.end; fields.set(field.field, {field, changed: 0});
  }
  check(Array.isArray(tail.changed_ranges) && tail.changed_ranges.length > 0, "missing exact post-NUL ranges");
  let changed = 0, previousRangeEnd = -1;
  for (const range of tail.changed_ranges) {
    const owner = fields.get(range.field), field = owner?.field;
    check(field && ["start", "end", "bytes"].every(k => count(range[k])) &&
      field.first_nul_offset < range.start && range.start < range.end && range.end <= field.end &&
      range.start >= previousRangeEnd && range.bytes === range.end - range.start,
    "tail write touches a live string, escapes its field or overlaps");
    previousRangeEnd = range.end; changed += range.bytes; owner.changed += range.bytes;
  }
  check(changed === tail.zeroed_bytes && [...fields.values()].every(f => f.changed === f.field.nonzero_tail_bytes),
    "post-NUL write totals do not reconcile");
  const privacy = p.independent_privacy_scan;
  check(privacy?.verified === true && privacy.findings === 0 && privacy.errors === 0 &&
    privacy.scanner_sha256 === BLENDER_FINAL_TOOLS.scanner && privacy.after_sha256 === row.after_sha256 &&
    privacy.after_bytes === row.after_bytes, "missing, stale or failed independent final raw privacy scan");
  const delta = p.independent_byte_delta;
  check(delta?.verified === true && delta.all_other_decompressed_bytes_identical === true &&
    delta.checker_sha256 === BLENDER_FINAL_TOOLS.byteDelta && delta.raw_intermediate_sha256 === p.raw_intermediate_sha256 &&
    delta.raw_intermediate_bytes === p.raw_intermediate_bytes && delta.after_sha256 === row.after_sha256 &&
    delta.after_bytes === row.after_bytes && delta.allowed_changed_byte_count === tail.zeroed_bytes,
  "missing, stale or failed independent final byte delta");
}

function validateProof(row) {
  const p = row.proof;
  if (!p || typeof p !== "object" || Array.isArray(p)) throw new Error(`Missing metadata equivalence proof: ${row.path}`);
  publicSafe(p, row.path);
  const requireTrue = keys => {
    if (keys.some(key => p[key] !== true)) throw new Error(`Missing or failed metadata equivalence proof: ${row.path}`);
  };
  const requireHashes = keys => {
    if (keys.some(key => typeof p[key] !== "string" || !DIGEST.test(p[key]))) throw new Error(`Invalid equivalence fingerprint: ${row.path}`);
  };
  if (row.path.endsWith(".blend")) {
    requireTrue(["source_bytes_unchanged", "in_memory_semantics_equal", "reopened_semantics_equal", "reopened_metadata_portable"]);
    requireHashes(["evidence_sha256", "semantic_sha256"]);
    validateFinalBlenderProof(row);
  } else {
    requireTrue(["original_source_unchanged_after_copy", "candidate_readback_hash_verified"]);
    if (p.independent_privacy_scan?.verified !== true || p.independent_privacy_scan.findings !== 0 ||
        p.independent_privacy_scan.errors !== 0 || !DIGEST.test(p.independent_privacy_scan.scanner_sha256 ?? "")) throw new Error("Missing independent privacy scan");
    if (row.path.endsWith(".png")) {
      requireTrue(["only_path_bearing_file_text_removed", "rendering_chunks_unchanged", "decoded_rgba_independently_verified"]);
      requireHashes(["retained_chunk_sha256", "idat_sha256"]);
      const rgba = p.independent_rgba;
      if (rgba?.identical !== true || rgba.decoder !== "Pillow" || !Number.isSafeInteger(rgba.width) || rgba.width <= 0 ||
          !Number.isSafeInteger(rgba.height) || rgba.height <= 0 || rgba.rgba_bytes !== rgba.width * rgba.height * 4 ||
          !DIGEST.test(rgba.rgba_sha256 ?? "")) throw new Error("Missing independent pixel equivalence");
    } else {
      requireTrue(["semantic_json_unchanged_except_allowed_values", "all_non_json_chunks_byte_identical", "geometry_materials_images_rig_actions_unchanged"]);
      requireHashes(["binary_chunks_sha256"]);
      if (p.interpreted_json_privacy_scan?.verified !== true || p.interpreted_json_privacy_scan.findings !== 0) throw new Error("Missing decoded GLB privacy scan");
    }
  }
}

function pointerSlot(document, location, allowMissingLeaf = false) {
  if (typeof location !== "string" || !location.startsWith("/")) throw new Error("Invalid JSON pointer");
  const parts = location.slice(1).split("/").map(k => k.replaceAll("~1", "/").replaceAll("~0", "~"));
  let parent = document;
  for (const key of parts.slice(0, -1)) {
    if (!parent || !Object.hasOwn(parent, key)) throw new Error("Missing JSON pointer parent");
    parent = parent[key];
  }
  const key = parts.at(-1);
  if (!parent || !allowMissingLeaf && !Object.hasOwn(parent, key)) throw new Error("Missing JSON pointer leaf");
  return {parent, key, parts};
}

function conservedEvidence(bytes, bindings, redactions, metadataPointers = []) {
  const result = losslessNumbers(bytes);
  for (const p of [...bindings.map(b => b.pointer), ...redactions.map(r => r.pointer), ...metadataPointers]) {
    const {parent, key} = pointerSlot(result, p); delete parent[key];
  }
  const sort = value => JSON.isRawJSON(value) ? value : Array.isArray(value) ? value.map(sort) : value && typeof value === "object"
    ? Object.fromEntries(Object.keys(value).sort().map(k => [k, sort(value[k])])) : value;
  return sha256(jsonBytes(sort(result)));
}

function amendedDocumentBytes(originalBytes, candidate, bindings, redactions, metadataPointers) {
  const exact = losslessNumbers(originalBytes);
  for (const change of [...bindings, ...redactions]) {
    const {parent, key} = pointerSlot(exact, change.pointer); parent[key] = change.after;
  }
  for (const marker of metadataPointers) {
    const {parent, key} = pointerSlot(exact, marker, true), expected = pointerSlot(candidate, marker);
    parent[key] = expected.parent[expected.key];
  }
  const bytes = jsonBytes(exact);
  assert.deepEqual(JSON.parse(bytes), candidate, "Lossless amendment differs from its accounted-for changes");
  return bytes;
}

/** Pure planner. Readers must return exact original/candidate bytes, not normalized text. */
export function planRebindings({ snapshot, snapshotBytes = jsonBytes(snapshot), changes, readOriginal, readCandidate,
  sourceReceipts = [], rebinderBytes = fs.readFileSync(fileURLToPath(import.meta.url)) }) {
  if (!Array.isArray(snapshot?.files) || !snapshot.files.length) throw new Error("Missing original snapshot");
  assert.deepEqual(JSON.parse(snapshotBytes), snapshot, "Snapshot digest must bind the actual snapshot input");
  if (!Array.isArray(changes) || !changes.length) throw new Error("Missing metadata change map");
  const originals = new Map(), hashPaths = new Map(), originalBytes = new Map();
  for (const row of snapshot.files) {
    relativePath(row.path);
    if (originals.has(row.path) || !DIGEST.test(row.sha256) || !Number.isSafeInteger(row.bytes) || row.bytes < 0) throw new Error("Invalid or duplicate snapshot entry");
    originals.set(row.path, row);
    const same = hashPaths.get(row.sha256.toUpperCase()) ?? [];
    same.push(row.path); hashPaths.set(row.sha256.toUpperCase(), same);
  }
  const read = name => {
    const expected = originals.get(name);
    if (!expected) throw new Error(`Missing immutable input: ${name}`);
    if (!originalBytes.has(name)) {
      const bytes = readOriginal(name); verifyBytes(bytes, expected, name); originalBytes.set(name, bytes);
    }
    return originalBytes.get(name);
  };
  const published = new Map(), binaryRecords = [];
  for (const row of changes) {
    relativePath(row.path);
    if (!assetPath(row.path) || !/\.(blend|png|glb)$/.test(row.path) || RUNTIME_MODELS.includes(row.path)) throw new Error(`Forbidden binary mutation: ${row.path}`);
    if (published.has(row.path)) throw new Error(`Duplicate binary mutation: ${row.path}`);
    const before = originals.get(row.path);
    if (!before || row.before_sha256 !== before.sha256 || row.before_bytes !== before.bytes) throw new Error(`Stale before-hash or size: ${row.path}`);
    if (!DIGEST.test(row.after_sha256) || row.after_sha256 === row.before_sha256 || !Number.isSafeInteger(row.after_bytes) || row.after_bytes <= 0) throw new Error(`Invalid after-binding: ${row.path}`);
    validateProof(row);
    read(row.path);
    verifyBytes(readCandidate(row.path), {sha256: row.after_sha256, bytes: row.after_bytes}, row.path);
    const record = {path: row.path, before_sha256: row.before_sha256, after_sha256: row.after_sha256,
      before_bytes: row.before_bytes, after_bytes: row.after_bytes, proof: clone(row.proof)};
    published.set(row.path, {sha256: row.after_sha256, bytes: row.after_bytes}); binaryRecords.push(record);
  }
  const preserved = RUNTIME_MODELS.map(name => {
    read(name); const row = originals.get(name); return {path: name, sha256: row.sha256, bytes: row.bytes};
  });
  sourceReceipts.forEach((r, i) => publicSafe(r, `source_receipts/${i}`));
  const docs = new Map(snapshot.files.filter(r => r.path.startsWith("assets/3d/") && r.path.endsWith(".json"))
    .map(r => [r.path, {original: JSON.parse(read(r.path).toString("utf8")), status: "pending"}]));
  const artifacts = new Map(), documents = [];

  function resolveBinding(value, parts, parent, document) {
    if (typeof value !== "string" || !DIGEST.test(value) || !fileBinding(parts, parent)) return null;
    const explicit = explicitTarget(parts, parent);
    let targets = explicit ? [explicit] : (hashPaths.get(value.toUpperCase()) ?? []);
    if (explicit && originals.get(explicit)?.sha256.toUpperCase() !== value.toUpperCase()) throw new Error(`Stale explicit file binding: ${document}${pointer(parts)}`);
    if (!targets.length) return null; // A historical unpublished diagnostic is not fabricated into a current file.
    for (const target of targets) if (docs.has(target)) resolveDocument(target);
    if (!targets.some(t => published.has(t))) return null;
    const outcomes = targets.map(t => published.get(t) ?? originals.get(t));
    if (new Set(outcomes.map(r => `${r.sha256.toUpperCase()}:${r.bytes}`)).size !== 1) throw new Error(`Ambiguous old SHA mapping: ${document}${pointer(parts)}`);
    const after = outcomes[0];
    if (after.sha256.toUpperCase() === value.toUpperCase()) return null;
    return {targets, before: value, after: after.sha256.toUpperCase(), after_bytes: after.bytes};
  }

  function redact(value, document, parts) {
    if (!unsafeText(value)) return null;
    const p = pointer(parts);
    if (!REDACTIONS.get(document)?.has(p)) throw new Error(`Unexpected absolute/private text: ${document}${p}`);
    const basename = value.replaceAll("\\", "/").split("/").at(-1);
    const matches = [...originals.keys()].filter(f => f.split("/").at(-1) === basename && /^(?:assets\/3d\/|public\/assets\/)/.test(f));
    if (matches.length > 1) throw new Error(`Ambiguous redaction destination: ${document}${p}`);
    return {pointer: p, kind: "redact-authoring-path", before_value_sha256: sha256(Buffer.from(value)),
      after: matches[0] ?? null, reason: matches.length ? "Workstation path replaced by existing repository-relative publication path." : "Private authoring output path omitted; no corresponding published artifact exists."};
  }

  function resolveDocument(name) {
    const doc = docs.get(name);
    if (doc.status === "done") return;
    if (doc.status === "active") throw new Error(`Cyclic receipt dependency: ${name}`);
    doc.status = "active";
    const bindings = [], redactions = [];
    function visit(value, parts, parent) {
      if (typeof value === "string") {
        const redaction = redact(value, name, parts);
        if (redaction) { redactions.push(redaction); return redaction.after; }
        const result = resolveBinding(value, parts, parent, name);
        if (result) {
          bindings.push({pointer: pointer(parts), kind: "publication-file-sha256", targets: result.targets,
            before: result.before, after: result.after}); return result.after;
        }
        return value;
      }
      if (value && typeof value === "object") {
        const out = Array.isArray(value) ? [] : {};
        for (const [key, item] of Object.entries(value)) {
          if (unsafeText(key)) throw new Error(`Unexpected private key: ${name}${pointer([...parts, key])}`);
          out[key] = visit(item, [...parts, key], value);
        }
        // Only a file's own byte count may change. Topology and measured numbers never do.
        for (const sizeKey of ["bytes", "file_size_bytes"]) if (Number.isSafeInteger(value[sizeKey])) {
          for (const hashKey of ["sha256", "model_sha256", "glb_sha256"]) {
            const result = resolveBinding(value[hashKey], [...parts, hashKey], value, name);
            if (!result || !result.targets.every(t => /\.(?:glb|mp4)$/.test(t))) continue;
            const oldSizes = new Set(result.targets.map(t => originals.get(t).bytes));
            if (oldSizes.size !== 1 || !oldSizes.has(value[sizeKey])) throw new Error(`Stale file size binding: ${name}${pointer([...parts, sizeKey])}`);
            if (value[sizeKey] !== result.after_bytes) {
              out[sizeKey] = result.after_bytes;
              bindings.push({pointer: pointer([...parts, sizeKey]), kind: "publication-file-bytes", targets: result.targets,
                before: value[sizeKey], after: result.after_bytes});
            }
            break;
          }
        }
        return out;
      }
      return value;
    }
    const candidate = visit(doc.original, [], {});
    if (!bindings.length && !redactions.length) { doc.status = "done"; return; }
    const old = originals.get(name), archive = redactions.length ? null : `${PUBLICATION_ROOT}/authoring-records/${name}`;
    if (archive) { publicSafe(doc.original, name); artifacts.set(archive, read(name)); }
    const amendment = {id: ID, record: AMENDMENT_PATH, original_document_sha256: old.sha256,
      authoring_record: archive, authoring_record_status: archive ? "exact-public-safe-original" : "private-original-retained-not-published", notice: NOTICE};
    const metaPointers = [];
    if (Array.isArray(candidate)) {
      candidate.forEach((item, i) => {
        if (!item || typeof item !== "object" || Array.isArray(item)) throw new Error(`Unsupported array receipt: ${name}`);
        item.publication_amendment = amendment; metaPointers.push(`/${i}/publication_amendment`);
      });
    } else { candidate.publication_amendment = amendment; metaPointers.push("/publication_amendment"); }
    // Every semantic change is explicitly accounted for; metrics and hashes outside bindings are fixed.
    const restored = clone(candidate);
    const set = (p, v, remove = false) => {
      const keys = p.slice(1).split("/").map(k => k.replaceAll("~1", "/").replaceAll("~0", "~"));
      let o = restored; for (const k of keys.slice(0, -1)) o = o[k];
      if (remove) delete o[keys.at(-1)]; else o[keys.at(-1)] = v;
    };
    metaPointers.forEach(p => set(p, null, true));
    bindings.forEach(b => set(b.pointer, b.before));
    for (const r of redactions) {
      const keys = r.pointer.slice(1).split("/"); let o = doc.original; for (const k of keys) o = o[k]; set(r.pointer, o);
    }
    assert.deepEqual(restored, doc.original, `Unlogged evidence change: ${name}`);
    publicSafe(candidate, name);
    const bytes = amendedDocumentBytes(read(name), candidate, bindings, redactions, metaPointers);
    const current = {sha256: sha256(bytes), bytes: bytes.length};
    published.set(name, current); artifacts.set(name, bytes);
    documents.push({path: name, before_sha256: old.sha256, before_bytes: old.bytes,
      after_sha256: current.sha256, after_bytes: current.bytes, authoring_record: archive,
      archive_status: amendment.authoring_record_status, bindings, redactions, metadata_pointers: metaPointers,
      unchanged_evidence_sha256: conservedEvidence(read(name), bindings, redactions)});
    doc.status = "done";
  }
  [...docs.keys()].sort().forEach(resolveDocument);
  const counts = Object.fromEntries(["blend", "png", "glb"].map(ext => [ext, binaryRecords.filter(r => r.path.endsWith(`.${ext}`)).length]));
  const readmePath = `${PUBLICATION_ROOT}/README.md`;
  const readme = Buffer.from(`# Metadata-only publication amendment: 2026-09-07\n\n` +
    `This directory records publication copies, not a new sculpting, rendering or animation round. ` +
    `The change map binds ${binaryRecords.length} binary files (${counts.blend} Blender sources, ${counts.png} PNG images and ${counts.glb} historical GLBs), ` +
    `${documents.length} amended JSON documents and ${documents.filter(d => d.authoring_record).length} exact public-safe authoring archives.\n\n` +
    `## Authoring evidence and publication bindings\n\n` +
    `The original authoring documents describe the bytes actually used and measured during the historical builds. ` +
    `Their original file digests are preserved in byte-identical archives, including their original line endings. ` +
    `They must not be interpreted as manifests for the newly cleaned distribution files.\n\n` +
    `The canonical amended documents explicitly identify themselves as publication derivatives. File SHA-256 and file-size fields, including ` +
    `input_sha256 entries, now bind the publication copies; they do not claim that the old builder opened those cleaned bytes. ` +
    `Each document links its original authoring hash and archive status to [amendment.json](amendment.json). ` +
    `The amendment lists every changed JSON pointer with its original and current binding. Geometry, material, rig, action, motion, ` +
    `acceptance flags and measured counts are preserved. Original numeric tokens, including signed zero, exponent notation and ` +
    `large integers, are retained exactly. A separate conservation digest checks all remaining evidence.\n\n` +
    `## Omitted private originals\n\n` +
    `${documents.filter(d => !d.authoring_record).length} legacy canonical-highpoly authoring receipts contained workstation paths. Their exact originals remain privately retained ` +
    `and are authenticated by the original document digests; they are deliberately not included in the public authoring archive. ` +
    `The amendment records each path-redaction pointer and the original value digest without exposing the removed value. ` +
    `Existing repository files use relative paths; unpublished authoring outputs are explicitly null, not invented public artifacts.\n\n` +
    `## Verification and limits\n\n` +
    `The eight current runtime GLBs remain byte-identical. PNG proofs bind unchanged rendering chunks and independently decoded RGBA pixels. ` +
    `Legacy GLB proofs cover unchanged non-JSON chunks and unchanged semantic JSON outside the approved metadata fields. ` +
    `Blender proofs bind original, in-memory and reopened data equivalence. A separate byte-only step zeroes only unused bytes after ` +
    `the first NUL in the two exact SDNA metadata buffers, FileSelectParams.dir[1282] and RenderData.pic[1024]. Live strings and all ` +
    `other decompressed bytes remain identical. That byte-only step truthfully records no Blender reopen; a subsequent read-only ` +
    `Blender reopen, independent byte-delta check and full raw privacy scan each bind the final file hash. Raw RNA-only intermediate ` +
    `copies are not publication artifacts. Source sanitizer receipts and frozen verification tools are digest-bound separately.\n\n` +
    `The dependency order is binary copies, reports and validations, asset manifests, gallery manifests, then the amendment index. ` +
    `Documents refer to the stable amendment identifier/path rather than its final digest, avoiding a hash cycle. ` +
    `The clean-clone verifier checks published file bytes, exact original archives, allowed pointer changes, conserved evidence and runtime GLBs. ` +
    `No private files are required for that verifier.\n\n` +
    `This record does not assert a commit, push, deployment, fresh historical Blender test run, game-dev canonical package, ` +
    `mobile performance acceptance or 100-percent visual likeness. The current 2D fallback and existing acceptance limits remain unchanged.\n`);
  artifacts.set(readmePath, readme);
  const amendment = {schema: "asterion-metadata-publication-v1", id: ID, notice: NOTICE,
    source_head: snapshot.source_head, original_snapshot_sha256: sha256(snapshotBytes),
    rebinder_sha256: sha256(rebinderBytes), source_receipts: clone(sourceReceipts),
    files: binaryRecords.sort((a, b) => a.path.localeCompare(b.path)),
    documents: documents.sort((a, b) => a.path.localeCompare(b.path)), preserved_runtime_glbs: preserved,
    documentation: {path: readmePath, sha256: sha256(readme), bytes: readme.length},
    limits: ["No Blender authoring, render, motion or likeness test is claimed to have been rerun by this amendment.",
      "Original authoring receipts contain pre-publication file digests. They are historical records, not current distribution manifests.",
      "Omitted original receipts remain privately retained; their digests authenticate the baseline without publishing their workstation paths.",
      "This receipt does not constitute mobile, Linux deployment, game-dev canonical packaging or human likeness acceptance."]};
  publicSafe(amendment, AMENDMENT_PATH); artifacts.set(AMENDMENT_PATH, jsonBytes(amendment));
  for (const target of artifacts.keys()) if (!target.startsWith("assets/3d/")) throw new Error("Candidate outside asset publication scope");
  return {artifacts, amendment};
}

/** Clean-clone verification: no private authoring files or sanitizer executables are needed. */
export function verifyPublishedAmendment(repo) {
  const root = repo instanceof URL ? fileURLToPath(repo) : repo;
  const receipt = JSON.parse(safeRead(root, AMENDMENT_PATH));
  if (receipt.schema !== "asterion-metadata-publication-v1" || receipt.id !== ID || receipt.notice !== NOTICE) throw new Error("Invalid publication amendment");
  publicSafe(receipt, AMENDMENT_PATH);
  if (!Array.isArray(receipt.files) || !receipt.files.length || !Array.isArray(receipt.documents) || !receipt.documents.length) throw new Error("Missing publication bindings");
  const rows = new Map(), observed = new Map();
  const actual = name => {
    relativePath(name);
    if (!observed.has(name)) { const bytes = safeRead(root, name); observed.set(name, {sha256: sha256(bytes), bytes: bytes.length}); }
    return observed.get(name);
  };
  for (const r of [...receipt.files, ...receipt.documents]) {
    relativePath(r.path);
    if (!assetPath(r.path) || rows.has(r.path) || !DIGEST.test(r.before_sha256) || !DIGEST.test(r.after_sha256) ||
        r.before_sha256 === r.after_sha256 || !Number.isSafeInteger(r.before_bytes) || !Number.isSafeInteger(r.after_bytes)) throw new Error("Invalid or duplicate publication row");
    assert.deepEqual(actual(r.path), {sha256: r.after_sha256, bytes: r.after_bytes}, `Published binding mismatch: ${r.path}`);
    rows.set(r.path, r);
  }
  for (const r of receipt.files) {
    if (!/\.(blend|png|glb)$/.test(r.path) || RUNTIME_MODELS.includes(r.path)) throw new Error("Forbidden publication binary");
    validateProof(r);
  }
  assert.equal(receipt.documentation?.path, `${PUBLICATION_ROOT}/README.md`);
  assert.deepEqual(actual(receipt.documentation.path), {sha256: receipt.documentation.sha256, bytes: receipt.documentation.bytes}, "Publication explanation hash mismatch");
  assert.deepEqual(receipt.preserved_runtime_glbs.map(r => r.path), RUNTIME_MODELS);
  for (const r of receipt.preserved_runtime_glbs) assert.deepEqual(actual(r.path), {sha256: r.sha256, bytes: r.bytes}, "Runtime GLB changed");
  for (const r of receipt.documents) {
    if (!r.path.startsWith("assets/3d/") || !r.path.endsWith(".json")) throw new Error("Invalid receipt document path");
    const currentBytes = safeRead(root, r.path), current = JSON.parse(currentBytes); publicSafe(current, r.path);
    if (!Array.isArray(r.bindings) || !Array.isArray(r.redactions) || !Array.isArray(r.metadata_pointers)) throw new Error("Missing document delta log");
    const expectedMetadata = Array.isArray(current) ? current.map((_, i) => `/${i}/publication_amendment`) : ["/publication_amendment"];
    assert.deepEqual(r.metadata_pointers, expectedMetadata, "Incomplete amendment markers");
    const allPointers = [...r.bindings.map(b => b.pointer), ...r.redactions.map(b => b.pointer), ...r.metadata_pointers];
    if (new Set(allPointers).size !== allPointers.length) throw new Error("Duplicate document delta pointer");
    let original = null, originalBytes = null;
    if (r.authoring_record !== null) {
      if (r.redactions.length || r.archive_status !== "exact-public-safe-original" ||
          r.authoring_record !== `${PUBLICATION_ROOT}/authoring-records/${r.path}`) throw new Error("Invalid authoring archive claim");
      const bytes = safeRead(root, r.authoring_record);
      verifyBytes(bytes, {sha256: r.before_sha256, bytes: r.before_bytes}, r.authoring_record);
      originalBytes = bytes; original = JSON.parse(bytes); publicSafe(original, r.authoring_record);
    } else if (!r.redactions.length || !REDACTIONS.has(r.path) || r.archive_status !== "private-original-retained-not-published" ||
        fs.existsSync(path.join(root, `${PUBLICATION_ROOT}/authoring-records/${r.path}`))) throw new Error("Unexplained or falsely published omitted archive");
    for (const marker of r.metadata_pointers) {
      const {parent, key} = pointerSlot(current, marker), m = parent[key];
      assert.deepEqual(m, {id: ID, record: AMENDMENT_PATH, original_document_sha256: r.before_sha256,
        authoring_record: r.authoring_record, authoring_record_status: r.archive_status, notice: NOTICE});
    }
    for (const b of r.bindings) {
      const slot = pointerSlot(current, b.pointer);
      if (!Array.isArray(b.targets) || !b.targets.length || new Set(b.targets).size !== b.targets.length) throw new Error("Missing or duplicate binding targets");
      assert.deepEqual(slot.parent[slot.key], b.after, "Logged publication value differs from document");
      const isHash = b.kind === "publication-file-sha256";
      if (isHash ? !fileBinding(slot.parts, slot.parent) : b.kind !== "publication-file-bytes" || !["bytes", "file_size_bytes"].includes(slot.key)) throw new Error("Measurement or unknown pointer mutation");
      if (original) { const old = pointerSlot(original, b.pointer); assert.deepEqual(old.parent[old.key], b.before, "Original binding was fabricated"); }
      for (const target of b.targets) {
        relativePath(target);
        const row = rows.get(target); if (!row) throw new Error("Missing transitive publication target");
        assert.equal(b.before, isHash ? row.before_sha256 : row.before_bytes);
        assert.equal(b.after, isHash ? row.after_sha256 : row.after_bytes);
      }
      if (!isHash) {
        if (!b.targets.every(t => /\.(?:glb|mp4)$/.test(t))) throw new Error("Non-file measurement changed");
        const companion = r.bindings.find(h => h.kind === "publication-file-sha256" &&
          h.pointer.slice(0, h.pointer.lastIndexOf("/")) === b.pointer.slice(0, b.pointer.lastIndexOf("/")) &&
          JSON.stringify(h.targets) === JSON.stringify(b.targets));
        if (!companion) throw new Error("File size without its own hash binding");
      }
    }
    for (const redaction of r.redactions) {
      if (!REDACTIONS.get(r.path)?.has(redaction.pointer) || redaction.kind !== "redact-authoring-path" || !DIGEST.test(redaction.before_value_sha256)) throw new Error("Unapproved authoring path redaction");
      const slot = pointerSlot(current, redaction.pointer); assert.deepEqual(slot.parent[slot.key], redaction.after);
      if (redaction.after !== null) { relativePath(redaction.after); actual(redaction.after); }
    }
    const evidence = conservedEvidence(currentBytes, r.bindings, r.redactions, r.metadata_pointers);
    assert.equal(evidence, r.unchanged_evidence_sha256, "Unchanged authoring evidence was modified");
    if (original) assert.equal(conservedEvidence(originalBytes, r.bindings, r.redactions), evidence, "Original measured evidence differs");
  }
  return {files: receipt.files.length, documents: receipt.documents.length, unchanged_runtime_glbs: 8};
}

/** Keep immutable authoring literals as anchors, accepting only their exact documented publication copy. */
export function publishedHash(repo, name, originalHash) {
  relativePath(name);
  if (!DIGEST.test(originalHash)) throw new Error("Invalid original authoring hash");
  const root = repo instanceof URL ? fileURLToPath(repo) : repo;
  const receiptPath = path.join(root, AMENDMENT_PATH);
  if (!fs.existsSync(receiptPath)) return originalHash;
  const receipt = JSON.parse(fs.readFileSync(receiptPath, "utf8"));
  if (receipt.schema !== "asterion-metadata-publication-v1" || receipt.id !== ID) throw new Error("Invalid publication amendment");
  const rows = receipt.files.filter(r => r.path === name);
  if (!rows.length) return originalHash;
  if (rows.length !== 1 || rows[0].before_sha256 !== originalHash || !DIGEST.test(rows[0].after_sha256)) throw new Error("Original authoring anchor does not match publication amendment");
  verifyBytes(fs.readFileSync(path.join(root, name)), {sha256: rows[0].after_sha256, bytes: rows[0].after_bytes}, name);
  return rows[0].after_sha256;
}

function safeRead(root, name) {
  relativePath(name); const target = path.resolve(root, name), realRoot = fs.realpathSync(root);
  if (!fs.realpathSync(target).startsWith(realRoot + path.sep) || !fs.lstatSync(target).isFile()) throw new Error("Nonordinary or escaping input");
  return fs.readFileSync(target);
}

export function main(argv = process.argv.slice(2)) {
  const options = {maps: [], roots: []};
  for (let i = 0; i < argv.length; i += 2) {
    const value = argv[i + 1]; if (!value) throw new Error("Missing argument value");
    if (argv[i] === "--map") options.maps.push(value);
    else if (argv[i] === "--binary-root") options.roots.push(path.resolve(value));
    else if (argv[i] === "--originals") options.originals = path.resolve(value);
    else if (argv[i] === "--output") options.output = path.resolve(value);
    else throw new Error("Unknown argument");
  }
  const repo = fs.realpathSync(process.cwd()), privateRoot = path.join(repo, ".private") + path.sep;
  if (!options.originals || !options.output || !options.maps.length || !options.roots.length ||
      !options.output.startsWith(privateRoot) || fs.existsSync(options.output)) throw new Error("Use --originals, --map, --binary-root and a fresh private --output");
  const snapshotBytes = safeRead(options.originals, "snapshot.json"), snapshot = JSON.parse(snapshotBytes);
  const changes = [], sourceReceipts = [], observed = new Map();
  observed.set(path.join(options.originals, "snapshot.json"), sha256(snapshotBytes));
  observed.set(fileURLToPath(import.meta.url), sha256(fs.readFileSync(fileURLToPath(import.meta.url))));
  const observe = (root, name) => {
    const bytes = safeRead(root, name); observed.set(path.join(root, name), sha256(bytes)); return bytes;
  };
  for (const input of options.maps) {
    const bytes = fs.readFileSync(input), report = JSON.parse(bytes);
    observed.set(path.resolve(input), sha256(bytes));
    if (typeof report.schema !== "string" || !Array.isArray(report.files)) throw new Error("Sanitizer report requires schema and files[]");
    changes.push(...report.files); sourceReceipts.push({schema: report.schema, sha256: sha256(bytes), bytes: bytes.length, files: report.files.length});
  }
  const readCandidate = name => {
    const roots = options.roots.filter(root => fs.existsSync(path.join(root, name)));
    if (roots.length !== 1) throw new Error(`Missing or ambiguous candidate: ${name}`);
    return observe(roots[0], name);
  };
  const result = planRebindings({snapshot, snapshotBytes, changes, sourceReceipts,
    readOriginal: name => observe(options.originals, name), readCandidate});
  for (const entry of result.amendment.preserved_runtime_glbs) verifyBytes(safeRead(repo, entry.path), entry, entry.path);
  for (const [name, hash] of observed) if (sha256(fs.readFileSync(name)) !== hash) throw new Error("Input changed while preparing publication receipts");
  // Resolve an existing ancestor before mkdir, which could otherwise follow an escaping junction.
  const realPrivate = fs.realpathSync(path.join(repo, ".private"));
  if (realPrivate !== path.join(repo, ".private")) throw new Error("Unexpected private root link");
  let ancestor = path.dirname(options.output);
  while (!fs.existsSync(ancestor)) ancestor = path.dirname(ancestor);
  const realAncestor = fs.realpathSync(ancestor);
  if (realAncestor !== realPrivate && !realAncestor.startsWith(realPrivate + path.sep)) throw new Error("Escaping private destination ancestor");
  fs.mkdirSync(path.dirname(options.output), {recursive: true});
  if (!fs.realpathSync(path.dirname(options.output)).startsWith(privateRoot)) throw new Error("Unexpected private destination ancestor");
  fs.mkdirSync(options.output);
  for (const [name, bytes] of result.artifacts) {
    const target = path.join(options.output, name); fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.writeFileSync(target, bytes, {flag: "wx"});
    verifyBytes(fs.readFileSync(target), {sha256: sha256(bytes), bytes: bytes.length}, name);
  }
  console.log(JSON.stringify({binary_bindings: result.amendment.files.length, amended_documents: result.amendment.documents.length,
    candidate_files: result.artifacts.size, production_files_written: 0, latest_runtime_glbs_unchanged: 8}));
  return result;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
