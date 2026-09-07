/** Metadata-only publication copies. Never overwrite an input or destination.
 * PNG framing: https://www.w3.org/TR/png-3/#5DataRep
 * GLB framing: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#glb-file-format-specification
 * This is an explicitly authorized publication transformation, not a re-export.
 * node scripts/asset-publication/sanitize_media.mjs --output .private/REVIEW/media-candidates --report .private/REVIEW/media-report.json
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import { crc32, inflateSync } from "node:zlib";
import { isDeepStrictEqual } from "node:util";

const PNG = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);
const REDACTED = "[private path removed for publication]";
const CANONICAL_REFERENCE = "public/assets/companions/asterion.png";
const LIMIT = 4 * 1024 * 1024;
const utf8 = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true });
const legacyRules = {
  "public/assets/3d/asterion/asterion-highpoly-v001.glb": {
    before_sha256: "3146D3C9FED5AC833F2C0AC26C510275786FA70378756153CDFF592011EC65CE",
    pointers: ["/scenes/0/extras/turnaround_guidance", "/scenes/0/extras/highpoly_source"],
    canonical_fields: ["canonical_reference"],
  },
  "public/assets/3d/asterion/asterion.glb": {
    before_sha256: "E6029162AA07C6A64A6F1E28D0A218D04688F362AD1D6E0A9F385D14DC653BEB",
    pointers: ["/scenes/0/extras/exploratory_turnaround", "/scenes/0/extras/optimization_source"],
    canonical_fields: ["reference_path", "canonical_reference"],
  },
};
const fail = code => { throw new Error(code); };
const requireThat = (condition, code) => { if (!condition) fail(code); };
const digest = value => createHash("sha256").update(value).digest("hex").toUpperCase();
const pointerPart = value => String(value).replaceAll("~", "~0").replaceAll("/", "~1");
const pathRisk = /(?:^|[^a-z0-9])[a-z]:[\\/]|\\\\[^\\]|file:\/\/|\/(?:home|Users|tmp|var|srv|opt|mnt|media|run)\/|(?:^|[^a-z0-9_.-])\.(?:private|codex)(?:[\\/]|$)|AppData[\\/]|codex-clipboard/i;
const unsafeRisk = /gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-[A-Za-z0-9_-]{24,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|javascript:|data:text\/html|\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b|[a-z]+:\/\/[^\s/@:]+:[^\s/@]+@/i;
const identityKey = /^(?:Author|Artist|Creator|GPS|GPSInfo|Username|Hostname|Password|Secret|Token|API[-_]?Key)$/i;
const identityText = /dc:creator|photoshop:AuthorsPosition|exif:GPS|tiff:Artist/i;
const dangerous = value => pathRisk.test(value) || unsafeRisk.test(value) || identityText.test(value);

function inspectRawMetadata(data) {
  // Scan byte-oriented strings and UTF-16 fields without emitting their values.
  for (const text of [data.toString("latin1"), data.toString("utf16le"),
    Buffer.from(data.subarray(0, data.length - data.length % 2)).swap16().toString("utf16le")]) {
    requireThat(!dangerous(text), "UNAPPROVED_METADATA");
  }
}

function inspectExif(data) {
  requireThat(data.length >= 8, "PNG_EXIF_BOUNDS");
  const order = data.toString("ascii", 0, 2);
  requireThat(order === "II" || order === "MM", "PNG_EXIF_ORDER");
  const u16 = offset => order === "II" ? data.readUInt16LE(offset) : data.readUInt16BE(offset);
  const u32 = offset => order === "II" ? data.readUInt32LE(offset) : data.readUInt32BE(offset);
  requireThat(u16(2) === 42, "PNG_EXIF_MAGIC");
  const pending = [u32(4)], seen = new Set(), widths = [0, 1, 1, 2, 4, 8, 1, 1, 2, 4, 8, 4, 8];
  while (pending.length) {
    const offset = pending.pop(); if (!offset) continue;
    requireThat(!seen.has(offset) && seen.size < 128 && offset + 2 <= data.length, "PNG_EXIF_BOUNDS");
    seen.add(offset); const count = u16(offset);
    requireThat(count <= 4096 && offset + 2 + count * 12 + 4 <= data.length, "PNG_EXIF_BOUNDS");
    for (let i = 0; i < count; i++) {
      const field = offset + 2 + i * 12, tag = u16(field), type = u16(field + 2), amount = u32(field + 4);
      requireThat(![0x8825, 0x013b, 0x8298, 0x9c9d, 0xa430, 0xa431, 0xa435].includes(tag), "UNAPPROVED_METADATA_EXIF_IDENTITY");
      requireThat(widths[type] > 0, "PNG_EXIF_TYPE");
      const bytes = amount * widths[type], location = bytes > 4 ? u32(field + 8) : field + 8;
      requireThat(location + bytes <= data.length, "PNG_EXIF_BOUNDS");
      if (tag === 0x8769 || tag === 0xa005) pending.push(u32(field + 8));
    }
    pending.push(u32(offset + 2 + count * 12));
  }
  inspectRawMetadata(data);
}

function textChunk(type, data) {
  requireThat(data.length <= LIMIT, "PNG_METADATA_SIZE");
  const zero = data.indexOf(0);
  requireThat(zero >= 1 && zero <= 79, "PNG_TEXT_KEYWORD");
  const keyword = data.toString("latin1", 0, zero);
  requireThat(/^[\x20-\x7e\xa1-\xff]+$/.test(keyword) && !/^ | $| {2}/.test(keyword), "PNG_TEXT_KEYWORD");
  let text;
  try {
    if (type === "tEXt") {
      requireThat(data.indexOf(0, zero + 1) < 0, "PNG_TEXT_NULL");
      text = data.toString("latin1", zero + 1);
    } else if (type === "zTXt") {
      requireThat(data[zero + 1] === 0, "PNG_TEXT_COMPRESSION");
      text = inflateSync(data.subarray(zero + 2), { maxOutputLength: LIMIT }).toString("latin1");
    } else {
      const flag = data[zero + 1], method = data[zero + 2], language = data.indexOf(0, zero + 3);
      const translated = language < 0 ? -1 : data.indexOf(0, language + 1);
      requireThat([0, 1].includes(flag) && method === 0 && language >= 0 && translated >= 0, "PNG_TEXT_COMPRESSION");
      const descriptor = data.subarray(zero + 3, translated);
      inspectRawMetadata(descriptor);
      const payload = data.subarray(translated + 1);
      text = utf8.decode(flag ? inflateSync(payload, { maxOutputLength: LIMIT }) : payload);
    }
  } catch (error) {
    if (/^(PNG_|UNAPPROVED_METADATA)/.test(error.message)) throw error;
    fail("PNG_TEXT_DECODE");
  }
  requireThat(!identityKey.test(keyword) && !dangerous(keyword), "UNAPPROVED_METADATA_KEY");
  // Only this audited PNG field may be removed. Other hazards fail closed.
  if (type === "tEXt" && keyword === "File" && pathRisk.test(text)) {
    requireThat(!unsafeRisk.test(text) && !identityText.test(text), "UNAPPROVED_METADATA_FILE");
    return true;
  }
  requireThat(!dangerous(text), "UNAPPROVED_METADATA_TEXT");
  return false;
}

function parsePng(input) {
  requireThat(Buffer.isBuffer(input) && input.length >= 20 && input.subarray(0, 8).equals(PNG), "PNG_SIGNATURE");
  const chunks = []; let offset = 8, idat = false, endedIdat = false, ended = false;
  while (offset < input.length) {
    requireThat(!ended && offset + 12 <= input.length, "PNG_CHUNK_BOUNDS");
    const length = input.readUInt32BE(offset), end = offset + length + 12;
    requireThat(length <= 0x7fffffff && end <= input.length, "PNG_CHUNK_BOUNDS");
    const type = input.toString("ascii", offset + 4, offset + 8), data = input.subarray(offset + 8, end - 4);
    requireThat(/^[A-Za-z]{2}[A-Z][A-Za-z]$/.test(type), "PNG_CHUNK_TYPE");
    requireThat(crc32(input.subarray(offset + 4, end - 4)) === input.readUInt32BE(end - 4), "PNG_CRC");
    requireThat(chunks.length > 0 ? type !== "IHDR" : type === "IHDR", "PNG_HEADER_ORDER");
    if (type === "IHDR") {
      requireThat(length === 13 && data.readUInt32BE(0) > 0 && data.readUInt32BE(4) > 0, "PNG_HEADER");
      const depths = { 0: [1, 2, 4, 8, 16], 2: [8, 16], 3: [1, 2, 4, 8], 4: [8, 16], 6: [8, 16] };
      requireThat(depths[data[9]]?.includes(data[8]) && data[10] === 0 && data[11] === 0 && [0, 1].includes(data[12]), "PNG_HEADER");
    } else if (type === "IDAT") {
      requireThat(!endedIdat, "PNG_IDAT_ORDER"); idat = true;
    } else if (idat) endedIdat = true;
    if (type === "IEND") { requireThat(length === 0 && idat && end === input.length, "PNG_END"); ended = true; }
    requireThat(!/^[A-Z]/.test(type) || ["IHDR", "PLTE", "IDAT", "IEND"].includes(type), "PNG_UNKNOWN_CRITICAL_CHUNK");
    chunks.push({ type, data, raw: input.subarray(offset, end), offset }); offset = end;
  }
  requireThat(ended, "PNG_MISSING_IEND");
  return chunks;
}

export function sanitizePng(input) {
  const chunks = parsePng(input), kept = [], removed = [];
  for (const chunk of chunks) {
    let remove = false;
    if (["tEXt", "zTXt", "iTXt"].includes(chunk.type)) remove = textChunk(chunk.type, chunk.data);
    else if (chunk.type === "eXIf") inspectExif(chunk.data);
    else if (chunk.type === "iCCP") {
      const zero = chunk.data.indexOf(0);
      requireThat(zero > 0 && chunk.data[zero + 1] === 0, "PNG_ICC_FORMAT");
      inspectRawMetadata(chunk.data.subarray(0, zero));
      try { inspectRawMetadata(inflateSync(chunk.data.subarray(zero + 2), { maxOutputLength: LIMIT })); }
      catch (error) { if (/^UNAPPROVED_METADATA/.test(error.message)) throw error; fail("PNG_ICC_DECODE"); }
    } else if (!["IHDR", "PLTE", "IDAT", "IEND", "tRNS", "gAMA", "cHRM", "sRGB", "sBIT", "bKGD", "hIST", "pHYs", "oFFs", "tIME"].includes(chunk.type)) {
      // Unfamiliar ancillary chunks are never deleted. Visible path/identity
      // content blocks the entire copy; otherwise their bytes remain exact.
      inspectRawMetadata(chunk.data);
    }
    if (remove) removed.push({ type: "tEXt", keyword: "File", offset: chunk.offset, bytes: chunk.raw.length });
    else kept.push(chunk.raw);
  }
  const buffer = removed.length ? Buffer.concat([PNG, ...kept]) : input;
  const after = parsePng(buffer);
  requireThat(after.length === kept.length && after.every((item, i) => item.raw.equals(kept[i])), "PNG_PRESERVATION_FAILURE");
  return { buffer, changed: removed.length > 0, proof: {
    type: "png", removed_metadata: removed, only_path_bearing_file_text_removed: true,
    rendering_chunks_unchanged: true, retained_chunk_count: kept.length,
    retained_chunk_sha256: digest(Buffer.concat(kept)),
    idat_sha256: digest(Buffer.concat(chunks.filter(item => item.type === "IDAT").map(item => item.raw))),
    decoded_rgba_independently_verified: false,
  } };
}

// Locate string values without reserializing unrelated JSON. Reject duplicate
// keys and malformed input; preserve numerical lexemes beyond JS precision.
function jsonStrings(text) {
  let offset = 0; const strings = new Map();
  const space = () => { while (/[ \t\r\n]/.test(text[offset] ?? "!") && offset < text.length) offset++; };
  function string() {
    requireThat(text[offset] === '"', "GLB_JSON_STRING");
    const start = offset++;
    while (offset < text.length) {
      if (text[offset] === "\\") { offset += 2; continue; }
      if (text[offset++] === '"') {
        try { return { value: JSON.parse(text.slice(start, offset)), start, end: offset }; }
        catch { fail("GLB_JSON_STRING"); }
      }
    }
    fail("GLB_JSON_STRING");
  }
  function value(pointer, depth) {
    requireThat(depth <= 128, "GLB_JSON_DEPTH"); space();
    if (text[offset] === '"') { const item = string(); strings.set(pointer, item); return; }
    if (text[offset] === "{" || text[offset] === "[") {
      const object = text[offset++] === "{", end = object ? "}" : "]", keys = new Set(); let index = 0;
      space(); if (text[offset] === end) { offset++; return; }
      while (offset < text.length) {
        let key = index++;
        if (object) {
          space(); key = string().value;
          requireThat(!keys.has(key), "GLB_JSON_DUPLICATE_KEY"); keys.add(key); space();
          requireThat(text[offset++] === ":", "GLB_JSON_COLON");
        }
        value(`${pointer}/${pointerPart(key)}`, depth + 1); space();
        if (text[offset] === end) { offset++; return; }
        requireThat(text[offset++] === ",", "GLB_JSON_SEPARATOR");
      }
      fail("GLB_JSON_BOUNDS");
    }
    const scalar = /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(text.slice(offset));
    requireThat(scalar, "GLB_JSON_VALUE"); offset += scalar[0].length;
  }
  value("", 0); space(); requireThat(offset === text.length, "GLB_JSON_TRAILING_DATA");
  return strings;
}

function inspectJpeg(input) {
  requireThat(input.length >= 4 && input.readUInt16BE(0) === 0xffd8, "GLB_JPEG_HEADER");
  let offset = 2;
  while (offset + 2 <= input.length) {
    requireThat(input[offset++] === 0xff, "GLB_JPEG_MARKER");
    while (input[offset] === 0xff) offset++;
    const marker = input[offset++]; if (marker === 0xda || marker === 0xd9) return;
    if (marker === 0x01 || (marker >= 0xd0 && marker <= 0xd7)) continue;
    requireThat(offset + 2 <= input.length, "GLB_JPEG_BOUNDS"); const length = input.readUInt16BE(offset);
    requireThat(length >= 2 && offset + length <= input.length, "GLB_JPEG_BOUNDS");
    if ((marker >= 0xe0 && marker <= 0xef) || marker === 0xfe) {
      const data = input.subarray(offset + 2, offset + length); inspectRawMetadata(data);
      if (data.toString("ascii", 0, 6) === "Exif\0\0") inspectExif(data.subarray(6));
    }
    offset += length;
  }
  fail("GLB_JPEG_BOUNDS");
}

export function sanitizeGlb(input, relativePath, { canonicalReferenceSha256 } = {}) {
  requireThat(Buffer.isBuffer(input) && input.length >= 20 && input.toString("ascii", 0, 4) === "glTF", "GLB_HEADER");
  requireThat(input.readUInt32LE(4) === 2 && input.readUInt32LE(8) === input.length, "GLB_LENGTH_VERSION");
  const chunks = []; let offset = 12;
  while (offset < input.length) {
    requireThat(offset + 8 <= input.length, "GLB_CHUNK_BOUNDS");
    const length = input.readUInt32LE(offset), type = input.toString("ascii", offset + 4, offset + 8), end = offset + 8 + length;
    requireThat(length % 4 === 0 && end <= input.length, "GLB_CHUNK_BOUNDS_ALIGNMENT");
    requireThat(chunks.length === 0 ? type === "JSON" : chunks.length === 1 && type === "BIN\0", "GLB_CHUNK_TYPE_ORDER");
    chunks.push({ type, start: offset, data: input.subarray(offset + 8, end), raw: input.subarray(offset, end) }); offset = end;
  }
  requireThat(chunks.length > 0, "GLB_JSON_MISSING");
  let text, document;
  try { text = utf8.decode(chunks[0].data); } catch { fail("GLB_JSON_UTF8"); }
  const spans = jsonStrings(text);
  try { document = JSON.parse(text); } catch { fail("GLB_JSON_SYNTAX"); }
  requireThat(document && !Array.isArray(document) && document.asset?.version === "2.0", "GLB_ASSET_VERSION");
  const rule = legacyRules[relativePath], allowed = new Map((rule?.pointers ?? []).map(pointer => [pointer, REDACTED])), changed = [];
  const canonicalProof = [];
  for (const key of rule?.canonical_fields ?? []) {
    const extras = document.scenes?.[0]?.extras, value = extras?.[key];
    if (value === undefined) continue;
    const hashKey = key === "reference_path" ? "reference_sha256" : "canonical_reference_sha256";
    requireThat(typeof value === "string" && value.replaceAll("\\", "/").endsWith(CANONICAL_REFERENCE), "GLB_CANONICAL_REFERENCE_PATH");
    requireThat(typeof canonicalReferenceSha256 === "string" && /^[A-F0-9]{64}$/.test(canonicalReferenceSha256)
      && typeof extras[hashKey] === "string" && extras[hashKey].toUpperCase() === canonicalReferenceSha256, "GLB_CANONICAL_REFERENCE_HASH");
    const pointer = `/scenes/0/extras/${key}`; allowed.set(pointer, CANONICAL_REFERENCE);
    canonicalProof.push({ pointer, path: CANONICAL_REFERENCE, sha256: canonicalReferenceSha256, associated_hash_verified: true });
  }
  let scannedStrings = 0, scannedKeys = 0;
  function inspect(value, pointer = "", allowEdits = true) {
    if (typeof value === "string") {
      scannedStrings++;
      if (allowEdits && allowed.has(pointer) && pathRisk.test(value)) {
        requireThat(!unsafeRisk.test(value) && !identityText.test(value), "UNAPPROVED_METADATA_GLB_VALUE");
        changed.push(pointer);
      } else requireThat(!dangerous(value), "UNAPPROVED_METADATA_GLB_VALUE");
    } else if (Array.isArray(value)) value.forEach((item, i) => inspect(item, `${pointer}/${i}`, allowEdits));
    else if (value && typeof value === "object") for (const [key, item] of Object.entries(value)) {
      scannedKeys++;
      requireThat(!dangerous(key) && !identityKey.test(key), "UNAPPROVED_METADATA_GLB_KEY");
      inspect(item, `${pointer}/${pointerPart(key)}`, allowEdits);
    }
  }
  inspect(document);
  for (const item of document.images ?? []) {
    requireThat(item.uri === undefined, "UNAPPROVED_METADATA_EXTERNAL_IMAGE");
    const view = document.bufferViews?.[item.bufferView], bin = chunks[1]?.data, start = view?.byteOffset ?? 0;
    requireThat(view?.buffer === 0 && bin && Number.isInteger(start) && start >= 0 && Number.isInteger(view.byteLength)
      && view.byteLength > 0 && start + view.byteLength <= bin.length, "GLB_EMBEDDED_IMAGE_BOUNDS");
    const image = bin.subarray(start, start + view.byteLength);
    if (item.mimeType === "image/png") requireThat(!sanitizePng(image).changed, "UNAPPROVED_METADATA_EMBEDDED_PNG");
    else if (item.mimeType === "image/jpeg") inspectJpeg(image);
    else fail("UNAPPROVED_METADATA_EMBEDDED_FORMAT");
  }
  let replaced = text;
  for (const pointer of [...changed].sort((a, b) => spans.get(b).start - spans.get(a).start)) {
    const span = spans.get(pointer); replaced = replaced.slice(0, span.start) + JSON.stringify(allowed.get(pointer)) + replaced.slice(span.end);
  }
  const afterDocument = JSON.parse(replaced), expected = structuredClone(document);
  for (const pointer of changed) expected.scenes[0].extras[pointer.split("/").at(-1)] = allowed.get(pointer);
  requireThat(isDeepStrictEqual(expected, afterDocument), "GLB_SEMANTIC_PRESERVATION_FAILURE");
  scannedStrings = 0; scannedKeys = 0; inspect(afterDocument, "", false);
  const binary = input.subarray(chunks[0].start + chunks[0].raw.length);
  let buffer = input;
  if (changed.length) {
    const json = Buffer.from(replaced.replace(/[ \t\r\n]+$/, "")), pad = Buffer.alloc((4 - json.length % 4) % 4, 32);
    const header = Buffer.from(input.subarray(0, 20));
    header.writeUInt32LE(20 + json.length + pad.length + binary.length, 8); header.writeUInt32LE(json.length + pad.length, 12);
    buffer = Buffer.concat([header, json, pad, binary]);
  }
  requireThat(buffer.subarray(20 + buffer.readUInt32LE(12)).equals(binary), "GLB_BINARY_PRESERVATION_FAILURE");
  return { buffer, changed: changed.length > 0, proof: {
    type: "glb", changed_scene_extra_values: changed, replacement: REDACTED,
    canonical_reference_bindings: canonicalProof,
    interpreted_json_privacy_scan: { verified: true, string_values_scanned: scannedStrings, keys_scanned: scannedKeys, findings: 0 },
    semantic_json_unchanged_except_allowed_values: true, unmodified_json_lexemes_unchanged: true,
    all_non_json_chunks_byte_identical: true, binary_chunks_sha256: digest(binary),
    binary_chunks_bytes: binary.length, embedded_image_count: (document.images ?? []).length,
    geometry_materials_images_rig_actions_unchanged: true,
  } };
}

function relative(value) {
  requireThat(typeof value === "string" && value.length > 0 && !/[\\:\x00-\x1f]/.test(value)
    && !value.split("/").some(part => ["", ".", ".."].includes(part) || /[. ]$/.test(part)
      || /^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)/i.test(part)), "PATH_INVALID_RELATIVE");
  return value;
}
function privatePath(value) {
  relative(value); requireThat(value.startsWith(".private/") && value.split("/").length >= 2, "PATH_PRIVATE_DESTINATION_REQUIRED");
  return value;
}
function safePath(root, value, directory = false) {
  relative(value); let current = root;
  for (const part of value.split("/")) {
    current = path.join(current, part);
    let stat; try { stat = fs.lstatSync(current); } catch (error) { if (error.code !== "ENOENT") fail("PATH_INSPECTION_FAILED"); }
    if (stat) {
      requireThat(!stat.isSymbolicLink(), "PATH_SYMLINK");
      if (current !== path.join(root, value) || directory) requireThat(stat.isDirectory(), "PATH_NOT_DIRECTORY");
    }
  }
  return current;
}
function absent(location) {
  try { fs.lstatSync(location); fail("DESTINATION_EXISTS"); }
  catch (error) { if (error.code !== "ENOENT") throw error; }
}
function exclusiveWrite(root, value, data) {
  safePath(root, value); let parent = root;
  for (const part of value.split("/").slice(0, -1)) {
    parent = path.join(parent, part);
    try { fs.mkdirSync(parent); } catch (error) { if (error.code !== "EEXIST") fail("PATH_CREATE_FAILED"); }
    requireThat(!fs.lstatSync(parent).isSymbolicLink() && fs.statSync(parent).isDirectory(), "PATH_SYMLINK");
  }
  const destination = safePath(root, value); let fd;
  try { fd = fs.openSync(destination, "wx"); }
  catch (error) { if (error.code === "EEXIST") fail("DESTINATION_EXISTS"); fail("DESTINATION_CREATE_FAILED"); }
  try { fs.writeFileSync(fd, data); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
}

export function writeMediaCandidates({ repoRoot = process.cwd(), candidateRoot, reportPath, files }) {
  const root = fs.realpathSync(repoRoot); privatePath(candidateRoot); privatePath(reportPath);
  requireThat(reportPath !== candidateRoot && !reportPath.startsWith(candidateRoot + "/"), "PATH_REPORT_OUTSIDE_MIRROR_REQUIRED");
  safePath(root, candidateRoot, true); absent(safePath(root, reportPath));
  requireThat(Array.isArray(files) && files.length > 0 && new Set(files).size === files.length, "PATH_INPUT_LIST");
  const canonicalReferenceSha256 = files.some(file => legacyRules[file])
    ? digest(fs.readFileSync(safePath(root, CANONICAL_REFERENCE))) : undefined;
  const plan = [];
  // Complete read-only preflight before creating any output file.
  for (const file of [...files].sort()) {
    relative(file); requireThat(/^(?:assets\/|public\/assets\/)/.test(file) && /\.(?:png|glb)$/.test(file), "PATH_INPUT_SCOPE");
    const source = safePath(root, file); requireThat(fs.lstatSync(source).isFile(), "PATH_SOURCE_NOT_FILE");
    const input = fs.readFileSync(source), transform = file.endsWith(".png") ? sanitizePng(input) : sanitizeGlb(input, file, { canonicalReferenceSha256 });
    if (!transform.changed) continue;
    const before = digest(input);
    if (file.endsWith(".glb")) requireThat(before === legacyRules[file]?.before_sha256, "GLB_UNREVIEWED_INPUT_HASH");
    absent(safePath(root, `${candidateRoot}/${file}`));
    plan.push({ path: file, before_sha256: before, after_sha256: digest(transform.buffer), before_bytes: input.length,
      after_bytes: transform.buffer.length, proof: transform.proof });
  }
  for (const entry of plan) {
    const source = safePath(root, entry.path), input = fs.readFileSync(source);
    requireThat(digest(input) === entry.before_sha256, "SOURCE_CHANGED_AFTER_PREFLIGHT");
    const result = entry.path.endsWith(".png") ? sanitizePng(input) : sanitizeGlb(input, entry.path, { canonicalReferenceSha256 });
    requireThat(digest(result.buffer) === entry.after_sha256, "CANDIDATE_CHANGED_AFTER_PREFLIGHT");
    exclusiveWrite(root, `${candidateRoot}/${entry.path}`, result.buffer);
    requireThat(digest(fs.readFileSync(source)) === entry.before_sha256, "SOURCE_CHANGED_AFTER_COPY");
    requireThat(digest(fs.readFileSync(safePath(root, `${candidateRoot}/${entry.path}`))) === entry.after_sha256, "CANDIDATE_READBACK_MISMATCH");
    entry.proof.original_source_unchanged_after_copy = true;
    entry.proof.candidate_readback_hash_verified = true;
  }
  const report = { schema: "asterion.media-publication.v1", operation: "metadata-only-new-copies",
    source_media_written: false, scanned_files: files.length, changed_files: plan.length,
    unchanged_files_not_copied: files.length - plan.length,
    counts: { png: plan.filter(item => item.path.endsWith(".png")).length, glb: plan.filter(item => item.path.endsWith(".glb")).length },
    independent_privacy_scan: { verified: false }, independent_decoded_rgba_check: { verified: false }, files: plan };
  exclusiveWrite(root, reportPath, Buffer.from(JSON.stringify(report, null, 2) + "\n"));
  return report;
}

function main() {
  const options = { repo: process.cwd(), baseline: "d18917c" };
  for (let i = 2; i < process.argv.length; i += 2) {
    const key = process.argv[i].replace(/^--/, ""), value = process.argv[i + 1];
    requireThat(["repo", "baseline", "output", "report"].includes(key) && value, "ARGUMENTS_INVALID"); options[key] = value;
  }
  requireThat(options.output && options.report, "ARGUMENTS_OUTPUT_REPORT_REQUIRED");
  const git = args => execFileSync("git", args, { cwd: options.repo, encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).split(/\r?\n/).filter(Boolean);
  const files = [...new Set([...git(["diff", "--name-only", "--diff-filter=ACMR", options.baseline]),
    ...git(["ls-files", "--others", "--exclude-standard"])])].filter(file => /^(?:assets\/|public\/assets\/)/.test(file) && /\.(png|glb)$/.test(file));
  const report = writeMediaCandidates({ repoRoot: options.repo, candidateRoot: options.output, reportPath: options.report, files });
  console.log(JSON.stringify({ scanned_files: report.scanned_files, changed_files: report.changed_files, counts: report.counts }));
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(); } catch (error) {
    // Never print native errors or matched metadata; these may expose paths.
    console.error(JSON.stringify({ error: /^[A-Z][A-Z_]+$/.test(error.message) ? error.message : "MEDIA_COPY_FAILED" }));
    process.exitCode = 1;
  }
}
