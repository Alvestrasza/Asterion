import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { deflateSync, inflateSync } from "node:zlib";
import { sanitizePng, sanitizeGlb, writeMediaCandidates } from "../scripts/asset-publication/sanitize_media.mjs";

// All path-like fixture strings are synthetic, not workstation identifiers.
const syntheticPath = "Z:/__synthetic__/source.blend";
const legacyPath = "public/assets/3d/asterion/asterion.glb";
const signature = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
const rgba = Buffer.from([255, 80, 20, 255, 5, 100, 220, 0]);

// Independent bitwise CRC oracle, deliberately separate from Node's native CRC.
function crc32(data) {
  let crc = 0xffffffff;
  for (const byte of data) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(type, data = Buffer.alloc(0)) {
  const result = Buffer.alloc(data.length + 12);
  result.writeUInt32BE(data.length); result.write(type, 4, "ascii"); data.copy(result, 8);
  result.writeUInt32BE(crc32(result.subarray(4, -4)), result.length - 4);
  return result;
}
function png(metadata = [chunk("tEXt", Buffer.from(`File\0${syntheticPath}`))]) {
  const header = Buffer.from("00000002000000010806000000", "hex");
  return Buffer.concat([signature, chunk("IHDR", header), chunk("gAMA", Buffer.from("0000b18f", "hex")),
    ...metadata, chunk("IDAT", deflateSync(Buffer.concat([Buffer.from([0]), rgba]))), chunk("IEND")]);
}
function pngChunks(input) {
  const result = [];
  for (let offset = 8; offset < input.length;) {
    const length = input.readUInt32BE(offset), end = offset + length + 12;
    result.push({ type: input.toString("ascii", offset + 4, offset + 8), raw: input.subarray(offset, end),
      data: input.subarray(offset + 8, end - 4) });
    offset = end;
  }
  return result;
}
function pixels(input) {
  const raw = inflateSync(Buffer.concat(pngChunks(input).filter(item => item.type === "IDAT").map(item => item.data)));
  assert.equal(raw[0], 0); // This independent fixture uses one unfiltered RGBA row.
  return raw.subarray(1);
}
function glb(document = {}, binary = Buffer.from([1, 2, 3, 4, 5, 6, 7, 8])) {
  const raw = Buffer.from(typeof document === "string" ? document : JSON.stringify({ asset: { version: "2.0" }, ...document }));
  const json = Buffer.concat([raw, Buffer.alloc((4 - raw.length % 4) % 4, 32)]);
  const header = Buffer.alloc(20); header.write("glTF"); header.writeUInt32LE(2, 4);
  header.writeUInt32LE(28 + json.length + binary.length, 8); header.writeUInt32LE(json.length, 12); header.write("JSON", 16);
  const binHeader = Buffer.alloc(8); binHeader.writeUInt32LE(binary.length); binHeader.write("BIN\0", 4);
  return Buffer.concat([header, json, binHeader, binary]);
}
function glbParts(buffer) {
  const size = buffer.readUInt32LE(12);
  return { json: JSON.parse(buffer.toString("utf8", 20, 20 + size)), binary: buffer.subarray(20 + size) };
}
const fixtureDocument = () => ({ scenes: [{ extras: { exploratory_turnaround: ".private/synthetic/turnaround.png",
  optimization_source: ".private/synthetic/source.blend", note: "Public synthetic fixture" } }],
  buffers: [{ byteLength: 8 }], nodes: [{ name: "Body", mesh: 0, skin: 0 }],
  meshes: [{ primitives: [{ attributes: { POSITION: 0 } }] }],
  skins: [{ joints: [1] }], animations: [{ name: "idle", samplers: [], channels: [] }] });

test("PNG removes only path-bearing File text and preserves decoded RGBA, alpha and every retained chunk", () => {
  const original = png([chunk("tEXt", Buffer.from(`File\0${syntheticPath}`)),
    chunk("tEXt", Buffer.from("Comment\0Public fixture")), chunk("tEXt", Buffer.from("File\0unsaved"))]);
  const before = Buffer.from(original), result = sanitizePng(original);
  assert.equal(result.changed, true);
  assert.deepEqual(original, before);
  assert.deepEqual(pixels(result.buffer), rgba);
  assert.deepEqual(pngChunks(result.buffer).map(item => item.raw),
    pngChunks(original).filter(item => !item.data.equals(Buffer.from(`File\0${syntheticPath}`))).map(item => item.raw));
  assert.equal(result.proof.rendering_chunks_unchanged, true);
  assert.equal(result.proof.only_path_bearing_file_text_removed, true);
  assert.equal(sanitizePng(result.buffer).changed, false);
});

test("PNG rejects malformed framing, CRC, chunk bounds, terminal data and duplicate headers", () => {
  const valid = png();
  const corruptCrc = Buffer.from(valid); corruptCrc[29] ^= 1;
  const corruptLength = Buffer.from(valid); corruptLength.writeUInt32BE(0xffffffff, 8);
  const badOrder = Buffer.concat([signature, ...pngChunks(valid).reverse().map(item => item.raw)]);
  for (const invalid of [Buffer.alloc(0), valid.subarray(0, -1), corruptCrc, corruptLength,
    Buffer.concat([valid, Buffer.from([0])]), badOrder,
    Buffer.concat([signature, pngChunks(valid)[0].raw, ...pngChunks(valid).map(item => item.raw)])]) {
    assert.throws(() => sanitizePng(invalid), /PNG_/);
  }
});

test("PNG rejects dangerous metadata in unapproved, compressed and international text fields", () => {
  const dangerous = [
    chunk("tEXt", Buffer.from(`Comment\0${syntheticPath}`)),
    chunk("zTXt", Buffer.concat([Buffer.from("Comment\0\0"), deflateSync(Buffer.from(".private/synthetic/source"))])),
    chunk("iTXt", Buffer.from("Comment\0\0\0\0\0javascript:synthetic")),
    chunk("tEXt", Buffer.from("Author\0Synthetic Person")),
    chunk("tEXt", Buffer.from("File\0Z:/__synthetic__/github_pat_" + "X".repeat(40))),
    chunk("vpAg", Buffer.from(".private/synthetic/unknown")),
  ];
  for (const item of dangerous) assert.throws(() => sanitizePng(png([item])), /UNAPPROVED_METADATA/);
  assert.throws(() => sanitizePng(png([chunk("zTXt", Buffer.from("Broken\0\0bad"))])), /PNG_/);
});

test("PNG preserves ordinary EXIF orientation data and rejects identity/GPS tags", () => {
  const exif = Buffer.from("49492a0008000000010012010300010000000100000000000000", "hex");
  assert.deepEqual(sanitizePng(png([chunk("eXIf", exif)])).buffer, png([chunk("eXIf", exif)]));
  for (const tag of [0x8825, 0x013b]) {
    const forbidden = Buffer.from(exif); forbidden.writeUInt16LE(tag, 10);
    assert.throws(() => sanitizePng(png([chunk("eXIf", forbidden)])), /UNAPPROVED_METADATA/);
  }
});

test("ordinary HTTPS metadata is not misclassified as a drive-letter path", () => {
  const original = png([chunk("tEXt", Buffer.from("Comment\0https://example.invalid/reference"))]);
  assert.equal(sanitizePng(original).changed, false);
  assert.equal(sanitizeGlb(glb({ extras: { reference: "https://example.invalid/reference" } }), legacyPath).changed, false);
});

test("GLB replaces only the two approved values and preserves binary chunks, images, rig and actions", () => {
  const original = glb(fixtureDocument()), snapshot = Buffer.from(original);
  const result = sanitizeGlb(original, legacyPath), before = glbParts(original), after = glbParts(result.buffer);
  assert.equal(result.changed, true);
  assert.deepEqual(original, snapshot);
  assert.deepEqual(after.binary, before.binary);
  for (const key of ["exploratory_turnaround", "optimization_source"]) {
    assert.equal(after.json.scenes[0].extras[key], "[private path removed for publication]");
    delete before.json.scenes[0].extras[key]; delete after.json.scenes[0].extras[key];
  }
  assert.deepEqual(after.json, before.json);
  assert.equal(result.proof.all_non_json_chunks_byte_identical, true);
  assert.equal(result.proof.semantic_json_unchanged_except_allowed_values, true);
  assert.equal(sanitizeGlb(result.buffer, legacyPath).changed, false);
});

test("GLB rejects unknown private fields, wrong file/scene scopes and private data outside scene extras", () => {
  const fixtures = [fixtureDocument(), fixtureDocument(), fixtureDocument(), fixtureDocument()];
  fixtures[0].scenes[0].extras.unknown_private_source = ".private/synthetic/unknown";
  fixtures[1].nodes[0].extras = { note: syntheticPath };
  fixtures[2].scenes.push({ extras: { exploratory_turnaround: ".private/synthetic/unknown" } });
  fixtures[3].asset = { version: "2.0", generator: "javascript:synthetic" };
  for (const document of fixtures) assert.throws(() => sanitizeGlb(glb(document), legacyPath), /UNAPPROVED_METADATA/);
  assert.throws(() => sanitizeGlb(glb(fixtureDocument()), "public/assets/3d/dog/dog.glb"), /UNAPPROVED_METADATA/);
});

test("GLB validates length/alignment, mandatory JSON, chunk bounds and duplicate JSON keys", () => {
  const original = glb(fixtureDocument());
  const badTotal = Buffer.from(original); badTotal.writeUInt32LE(original.length + 4, 8);
  const badChunk = Buffer.from(original); badChunk.writeUInt32LE(original.length + 4, 12);
  const badAlignment = Buffer.from(original); badAlignment.writeUInt32LE(1, 12);
  const wrongType = Buffer.from(original); wrongType.write("BIN\0", 16);
  for (const invalid of [Buffer.alloc(0), original.subarray(0, -1), badTotal, badChunk, badAlignment, wrongType,
    glb('{"asset":{"version":"2.0"},"scenes":[],"scenes":[]}')]) {
    assert.throws(() => sanitizeGlb(invalid, legacyPath), /GLB_/);
  }
});

test("GLB retains unmodified JSON lexemes including high-precision numbers", () => {
  const lexical = '{"asset":{"version":"2.0"}, "scenes":[{"extras":{"exploratory_turnaround":".private/synthetic/a"}}], "extras":{"value":1.2345678901234567890}}';
  const result = sanitizeGlb(glb(lexical), legacyPath);
  const jsonText = result.buffer.toString("utf8", 20, 20 + result.buffer.readUInt32LE(12));
  assert.ok(jsonText.includes('"value":1.2345678901234567890'));
});

test("GLB decodes escaped absolute paths and only canonical pointers get a hash-verified public reference", () => {
  const canonicalReferenceSha256 = "A".repeat(64), document = fixtureDocument();
  for (const key of ["canonical_reference", "reference_path"]) document.scenes[0].extras[key] = "Z:\\__synthetic__\\public\\assets\\companions\\asterion.png";
  document.scenes[0].extras.canonical_reference_sha256 = canonicalReferenceSha256;
  document.scenes[0].extras.reference_sha256 = canonicalReferenceSha256;
  const input = glb(document);
  assert.throws(() => sanitizeGlb(input, legacyPath), /GLB_CANONICAL_REFERENCE_HASH/);
  assert.throws(() => sanitizeGlb(input, legacyPath, { canonicalReferenceSha256: "B".repeat(64) }), /GLB_CANONICAL_REFERENCE_HASH/);
  const result = sanitizeGlb(input, legacyPath, { canonicalReferenceSha256 }), after = glbParts(result.buffer);
  for (const key of ["canonical_reference", "reference_path"]) assert.equal(after.json.scenes[0].extras[key], "public/assets/companions/asterion.png");
  assert.equal(result.proof.canonical_reference_bindings.length, 2);
  assert.equal(result.proof.interpreted_json_privacy_scan.verified, true);
  assert.equal(result.proof.interpreted_json_privacy_scan.findings, 0);
  assert.deepEqual(after.binary, glbParts(input).binary);
  const unexpected = structuredClone(document);
  unexpected.scenes[0].extras.other_reference = unexpected.scenes[0].extras.reference_path;
  assert.throws(() => sanitizeGlb(glb(unexpected), legacyPath, { canonicalReferenceSha256 }), /UNAPPROVED_METADATA/);
});

test("GLB embedded images remain exact, and metadata removal inside an image is never silently allowed", () => {
  const image = png([]), binary = Buffer.concat([image, Buffer.alloc((4 - image.length % 4) % 4)]);
  const document = fixtureDocument(); document.buffers[0].byteLength = binary.length;
  document.images = [{ mimeType: "image/png", bufferView: 0 }];
  document.bufferViews = [{ buffer: 0, byteOffset: 0, byteLength: image.length }];
  const input = glb(document, binary), result = sanitizeGlb(input, legacyPath);
  assert.deepEqual(glbParts(result.buffer).binary, glbParts(input).binary);
  assert.equal(result.proof.embedded_image_count, 1);
  const unsafeImage = png(), unsafeBinary = Buffer.concat([unsafeImage, Buffer.alloc((4 - unsafeImage.length % 4) % 4)]);
  document.bufferViews[0].byteLength = unsafeImage.length;
  assert.throws(() => sanitizeGlb(glb(document, unsafeBinary), legacyPath), /UNAPPROVED_METADATA_EMBEDDED_PNG/);
});

const workRoot = fileURLToPath(new URL("../.private/publication-2026-09-07/media-candidates/", import.meta.url));
function withWorkspace(run) {
  fs.mkdirSync(workRoot, { recursive: true });
  const root = fs.mkdtempSync(path.join(workRoot, ".tests-"));
  const source = path.join(root, "assets", "fixture.png"); fs.mkdirSync(path.dirname(source), { recursive: true });
  fs.writeFileSync(source, png());
  const options = { repoRoot: root, candidateRoot: ".private/candidates", reportPath: ".private/report.json", files: ["assets/fixture.png"] };
  try { return run({ root, source, options }); }
  finally { assert.ok(path.dirname(root) === path.resolve(workRoot)); fs.rmSync(root, { recursive: true }); }
}

test("copy operation is non-overwriting, reports hashes and bytes, and never mutates its sources", () => withWorkspace(({ root, source, options }) => {
  const before = fs.readFileSync(source), report = writeMediaCandidates(options);
  assert.deepEqual(fs.readFileSync(source), before);
  assert.equal(report.files.length, 1);
  assert.equal(report.files[0].path, "assets/fixture.png");
  assert.match(report.files[0].before_sha256, /^[A-F0-9]{64}$/);
  assert.notEqual(report.files[0].before_sha256, report.files[0].after_sha256);
  assert.ok(report.files[0].before_bytes > report.files[0].after_bytes);
  const destination = path.join(root, ".private/candidates/assets/fixture.png"), candidate = fs.readFileSync(destination);
  assert.deepEqual(pixels(candidate), rgba);
  assert.throws(() => writeMediaCandidates(options), /DESTINATION_EXISTS/);
  assert.deepEqual(fs.readFileSync(destination), candidate);
  fs.unlinkSync(path.join(root, ".private/report.json"));
  assert.throws(() => writeMediaCandidates(options), /DESTINATION_EXISTS/);
  assert.deepEqual(fs.readFileSync(destination), candidate);
}));

test("copy operation rejects source/output escapes, unapproved input roots, symlinks and report collisions", () => withWorkspace(({ root, options }) => {
  for (const file of ["../outside.png", "/absolute.png", "Z:/absolute.png", "assets/../fixture.png", "assets\\fixture.png", ".private/secret.png",
    "assets/.. /fixture.png", "assets/con.png", "assets/fixture.png:stream"]) {
    assert.throws(() => writeMediaCandidates({ ...options, files: [file] }), /PATH_/);
  }
  for (const candidateRoot of ["../escape", "assets", ".private/../assets", ".private"]) {
    assert.throws(() => writeMediaCandidates({ ...options, candidateRoot }), /PATH_/);
  }
  fs.mkdirSync(path.join(root, ".private"), { recursive: true });
  fs.writeFileSync(path.join(root, ".private/report.json"), "original report");
  assert.throws(() => writeMediaCandidates(options), /DESTINATION_EXISTS/);
  assert.equal(fs.existsSync(path.join(root, ".private/candidates/assets/fixture.png")), false);
  fs.unlinkSync(path.join(root, ".private/report.json"));
  // Directory junctions are available on Windows without symlink privilege.
  fs.symlinkSync(path.join(root, "assets"), path.join(root, ".private/link"), "junction");
  assert.throws(() => writeMediaCandidates({ ...options, candidateRoot: ".private/link" }), /PATH_SYMLINK/);
  fs.symlinkSync(path.join(root, "assets"), path.join(root, "assets", "link"), "junction");
  assert.throws(() => writeMediaCandidates({ ...options, files: ["assets/link/fixture.png"] }), /PATH_SYMLINK/);
}));

test("batch preflight rejects unknown private metadata before writing any candidate", () => withWorkspace(({ root, options }) => {
  fs.writeFileSync(path.join(root, "assets", "unsafe.png"), png([chunk("tEXt", Buffer.from(`Comment\0${syntheticPath}`))]));
  assert.throws(() => writeMediaCandidates({ ...options, files: [...options.files, "assets/unsafe.png"] }), /UNAPPROVED_METADATA/);
  assert.equal(fs.existsSync(path.join(root, ".private/candidates/assets/fixture.png")), false);
  assert.equal(fs.existsSync(path.join(root, ".private/report.json")), false);
}));

test("copy operation rejects an unreviewed legacy GLB byte hash before creating publication files", () => withWorkspace(({ root, options }) => {
  const source = path.join(root, legacyPath), reference = path.join(root, "public/assets/companions/asterion.png");
  fs.mkdirSync(path.dirname(source), { recursive: true }); fs.mkdirSync(path.dirname(reference), { recursive: true });
  fs.writeFileSync(source, glb(fixtureDocument())); fs.writeFileSync(reference, png([]));
  assert.throws(() => writeMediaCandidates({ ...options, files: [legacyPath] }), /GLB_UNREVIEWED_INPUT_HASH/);
  assert.equal(fs.existsSync(path.join(root, ".private/candidates", legacyPath)), false);
  assert.equal(fs.existsSync(path.join(root, ".private/report.json")), false);
}));
