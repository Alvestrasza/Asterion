/** Zero unreachable C-string tails in two reviewed Blender 5.2 metadata fields.
 * Never edits an input, live C string, other decompressed byte, or SDNA definition.
 * Layout authority: Blender source/blender/blenloader_core/BLO_core_bhead.hh.
 * Container authority: facebook/zstd contrib/seekable_format specification.
 * Both are checked structurally; unknown formats fail rather than being guessed.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import zlib from "node:zlib";

export const sha256 = bytes => createHash("sha256").update(bytes).digest("hex").toUpperCase();
const check = (condition, code) => { if (!condition) throw new Error(code); };
const HEADER = Buffer.from("BLENDER17-01v0502");
const MAX_RAW = 2 ** 31 - 1, MAX_FRAME = 64 * 1024 * 1024;
const targetFields = new Map([["FileSelectParams.dir", 1282], ["RenderData.pic", 1024]]);

export function decodeSeekable(input) {
  check(Buffer.isBuffer(input) && input.length >= 25, "ZSTD_CONTAINER_BOUNDS");
  check(input.readUInt32LE(input.length - 4) === 0x8f92eab1, "ZSTD_SEEK_MAGIC");
  const count = input.readUInt32LE(input.length - 9), descriptor = input[input.length - 5];
  // This explicitly audited Blender writer uses no per-entry XXH64 checksum.
  check(count > 0 && count < 100000 && descriptor === 0, "ZSTD_UNSUPPORTED_SEEK_DESCRIPTOR");
  const tableBytes = count * 8 + 9, tableStart = input.length - tableBytes - 8;
  check(tableStart >= 0 && input.readUInt32LE(tableStart) === 0x184d2a5e
    && input.readUInt32LE(tableStart + 4) === tableBytes, "ZSTD_SEEK_TABLE_BOUNDS");
  let position = 0, rawPosition = 0; const frames = [];
  for (let i = 0; i < count; i++) {
    const size = input.readUInt32LE(tableStart + 8 + i * 8), rawSize = input.readUInt32LE(tableStart + 12 + i * 8);
    check(size >= 4 && rawSize > 0 && rawSize <= MAX_FRAME && position + size <= tableStart
      && rawPosition + rawSize <= MAX_RAW, "ZSTD_FRAME_BOUNDS");
    const encoded = input.subarray(position, position + size);
    check(encoded.readUInt32LE(0) === 0xfd2fb528, "ZSTD_FRAME_MAGIC");
    let decoded;
    try { decoded = zlib.zstdDecompressSync(encoded, { info: true, maxOutputLength: MAX_FRAME }); }
    catch { throw new Error("ZSTD_FRAME_DECODE"); }
    check(decoded.engine.bytesWritten === size && decoded.buffer.length === rawSize, "ZSTD_FRAME_SIZE_MISMATCH");
    frames.push({ encoded, raw: decoded.buffer, start: rawPosition, end: rawPosition + rawSize, index: i });
    position += size; rawPosition += rawSize;
  }
  check(position === tableStart, "ZSTD_UNINDEXED_DATA");
  return { raw: Buffer.concat(frames.map(frame => frame.raw), rawPosition), frames,
    table: input.subarray(tableStart), descriptor };
}

function parseBlocks(raw) {
  check(raw.length >= HEADER.length + 32 && raw.subarray(0, HEADER.length).equals(HEADER), "BLEND_HEADER_UNSUPPORTED");
  const blocks = []; let offset = HEADER.length, ended = false;
  while (offset < raw.length) {
    check(!ended && offset + 32 <= raw.length, "BLEND_BLOCK_HEADER_BOUNDS");
    const length = Number(raw.readBigUInt64LE(offset + 16)), count = Number(raw.readBigUInt64LE(offset + 24));
    check(Number.isSafeInteger(length) && Number.isSafeInteger(count) && count >= 0
      && length >= 0 && offset + 32 + length <= raw.length, "BLEND_BLOCK_BOUNDS");
    const code = raw.toString("latin1", offset, offset + 4), sdna = raw.readUInt32LE(offset + 4);
    blocks.push({ code, sdna, count, length, start: offset + 32, header: offset });
    offset += 32 + length;
    if (code === "ENDB") { check(length === 0 && count === 0 && offset === raw.length, "BLEND_END_BLOCK"); ended = true; }
  }
  check(ended && blocks.filter(block => block.code === "DNA1").length === 1, "BLEND_DNA_OR_END_MISSING");
  return blocks;
}

function parseDna(data) {
  let offset = 0;
  const bounds = size => check(offset + size <= data.length, "SDNA_BOUNDS");
  const tag = expected => { bounds(4); check(data.toString("ascii", offset, offset + 4) === expected, "SDNA_TAG"); offset += 4; };
  const u16 = () => { bounds(2); const result = data.readUInt16LE(offset); offset += 2; return result; };
  const u32 = () => { bounds(4); const result = data.readUInt32LE(offset); offset += 4; return result; };
  const align = () => { const next = Math.ceil(offset / 4) * 4; bounds(next - offset); offset = next; };
  function strings() {
    const count = u32(); check(count > 0 && count <= 100000, "SDNA_STRING_COUNT"); const result = [];
    for (let i = 0; i < count; i++) {
      const end = data.indexOf(0, offset); check(end > offset && end - offset <= 1024, "SDNA_UNTERMINATED_STRING");
      const value = data.toString("latin1", offset, end); check(/^[\x20-\x7e]+$/.test(value), "SDNA_STRING_ENCODING");
      result.push(value); offset = end + 1;
    }
    align(); return result;
  }
  tag("SDNA"); tag("NAME"); const names = strings(); tag("TYPE"); const types = strings();
  check(new Set(types).size === types.length, "SDNA_DUPLICATE_TYPE");
  tag("TLEN"); const lengths = types.map(() => u16()); align(); tag("STRC"); const count = u32();
  check(count > 0 && count <= types.length, "SDNA_STRUCT_COUNT");
  const structs = [], byType = new Map();
  for (let i = 0; i < count; i++) {
    const type = u16(), size = u16();
    check(type < types.length && !byType.has(type)
      && (size > 0 || (types[type] === "raw_data" && lengths[type] === 0)), "SDNA_STRUCT_DEFINITION");
    const fields = [];
    for (let j = 0; j < size; j++) {
      const fieldType = u16(), nameIndex = u16(); check(fieldType < types.length && nameIndex < names.length, "SDNA_FIELD_INDEX");
      fields.push({ type: fieldType, name: names[nameIndex] });
    }
    const definition = { type, fields, index: i }; structs.push(definition); byType.set(type, definition);
  }
  // Only alignment padding, never a hidden second SDNA document, may remain.
  check(data.length - offset <= 3 && data.subarray(offset).every(byte => byte === 0), "SDNA_TRAILING_DATA");
  const layouts = new Map(), active = new Set();
  function layout(type) {
    if (layouts.has(type)) return layouts.get(type);
    const definition = byType.get(type);
    if (!definition) {
      check([1, 2, 4, 8].includes(lengths[type]), "SDNA_UNKNOWN_PRIMITIVE_LAYOUT");
      return { size: lengths[type], alignment: lengths[type], fields: [] };
    }
    check(!active.has(type), "SDNA_RECURSIVE_EMBEDDED_STRUCT"); active.add(type);
    let position = 0, alignment = 1; const fields = [];
    for (const field of definition.fields) {
      const pointer = field.name.includes("*");
      // Pointers to functions/arrays are not used in the approved ancestry;
      // refusing them avoids mistaking pointed-to dimensions for field size.
      check(!/[()]/.test(field.name), "SDNA_COMPLEX_DECLARATOR");
      const dimensions = [...field.name.matchAll(/\[(\d+)\]/g)], name = field.name.replaceAll(/\[\d+\]/g, "");
      check(/^\**[A-Za-z_]\w*$/.test(name), "SDNA_FIELD_DECLARATOR");
      const units = dimensions.reduce((product, match) => product * Number(match[1]), 1);
      check(Number.isSafeInteger(units) && units > 0 && units <= 1e7, "SDNA_ARRAY_BOUNDS");
      const element = pointer ? { size: 8, alignment: 8 } : layout(field.type);
      position = Math.ceil(position / element.alignment) * element.alignment;
      const size = element.size * units;
      check(position + size <= lengths[type], "SDNA_TLEN_MISMATCH");
      fields.push({ ...field, baseName: name.replace(/^\*+/, ""), offset: position, size, units, pointer });
      position += size; alignment = Math.max(alignment, element.alignment);
    }
    position = Math.ceil(position / alignment) * alignment;
    check(position === lengths[type], "SDNA_TLEN_MISMATCH");
    const result = { size: position, alignment, fields }; layouts.set(type, result); active.delete(type); return result;
  }
  const typeOf = name => { const result = types.indexOf(name); check(result >= 0 && byType.has(result), "SDNA_REQUIRED_TYPE"); return result; };
  const selectType = typeOf("FileSelectParams"), renderType = typeOf("RenderData"), sceneType = typeOf("Scene");
  const fieldOf = (type, name) => {
    const fields = layout(type).fields.filter(field => field.baseName === name); check(fields.length === 1, "SDNA_REQUIRED_FIELD"); return fields[0];
  };
  const dir = fieldOf(selectType, "dir"), pic = fieldOf(renderType, "pic"), sceneRender = fieldOf(sceneType, "r");
  for (const [typeName, field] of [["FileSelectParams", dir], ["RenderData", pic]]) {
    const size = targetFields.get(`${typeName}.${field.baseName}`);
    check(types[field.type] === "char" && !field.pointer && field.name === `${field.baseName}[${size}]`
      && field.size === size, "SDNA_TARGET_FIELD_MISMATCH");
  }
  check(sceneRender.type === renderType && !sceneRender.pointer && sceneRender.units === 1, "SDNA_SCENE_RENDER_ANCESTRY");
  return { structs, types, lengths, selectType, sceneType, dir, pic, sceneRender, layout,
    sdna_sha256: sha256(data), struct_count: count };
}

function locateFields(raw, blocks) {
  const block = blocks.find(item => item.code === "DNA1"), dna = parseDna(raw.subarray(block.start, block.start + block.length));
  const fields = [];
  for (const owner of blocks) {
    if (["DNA1", "ENDB", "REND", "TEST"].includes(owner.code)) continue;
    check(owner.sdna < dna.structs.length, "SDNA_BLOCK_INDEX");
    const type = dna.structs[owner.sdna].type;
    if (![dna.selectType, dna.sceneType].includes(type)) continue;
    check(owner.count > 0 && owner.length === dna.lengths[type] * owner.count, "SDNA_ROOT_BLOCK_BOUNDS");
    if (type === dna.selectType) check(owner.code === "DATA", "SDNA_SELECTOR_BLOCK_TYPE");
    else check(owner.code === "SC\0\0", "SDNA_SCENE_BLOCK_TYPE");
    for (let i = 0; i < owner.count; i++) {
      const base = owner.start + i * dna.lengths[type];
      const isSelect = type === dna.selectType, metadata = isSelect ? dna.dir : dna.pic;
      const start = base + metadata.offset + (isSelect ? 0 : dna.sceneRender.offset), end = start + metadata.size;
      check(start >= owner.start && end <= owner.start + owner.length, "SDNA_TARGET_BLOCK_BOUNDS");
      const firstNul = raw.indexOf(0, start); check(firstNul >= start && firstNul < end, "SDNA_UNTERMINATED_TARGET_CSTRING");
      fields.push({ field: isSelect ? "FileSelectParams.dir[1282]" : "RenderData.pic[1024]",
        owner_path: isSelect ? "FileSelectParams.dir" : "Scene.r.pic", root_block_offset: owner.header,
        element_index: i, start, end, bytes: metadata.size, first_nul_offset: firstNul,
        live_cstring_sha256: sha256(raw.subarray(start, firstNul + 1)) });
    }
  }
  check(fields.some(field => field.owner_path === "FileSelectParams.dir") && fields.some(field => field.owner_path === "Scene.r.pic"), "SDNA_REQUIRED_INSTANCES");
  fields.sort((a, b) => a.start - b.start);
  check(fields.every((field, i) => i === 0 || field.start >= fields[i - 1].end), "SDNA_OVERLAPPING_FIELDS");
  return { fields, sdna_sha256: dna.sdna_sha256, struct_count: dna.struct_count };
}

export function cleanBlendTails(input) {
  const decoded = decodeSeekable(input), { raw } = decoded, blocks = parseBlocks(raw);
  const located = locateFields(raw, blocks), after = Buffer.from(raw), ranges = [];
  for (const field of located.fields) {
    let start = field.first_nul_offset + 1, changed = 0;
    while (start < field.end) {
      if (raw[start] === 0) { start++; continue; }
      let end = start + 1; while (end < field.end && raw[end] !== 0) end++;
      after.fill(0, start, end); ranges.push({ start, end, bytes: end - start, field: field.field }); changed += end - start; start = end;
    }
    field.nonzero_tail_bytes = changed;
    check(after.subarray(field.start, field.first_nul_offset + 1).equals(raw.subarray(field.start, field.first_nul_offset + 1)), "BLEND_LIVE_STRING_CHANGED");
  }
  let position = 0; const untouched = createHash("sha256");
  for (const range of ranges) {
    check(raw.subarray(position, range.start).equals(after.subarray(position, range.start)), "BLEND_UNAPPROVED_BYTE_CHANGE");
    untouched.update(raw.subarray(position, range.start)); position = range.end;
  }
  check(raw.subarray(position).equals(after.subarray(position)), "BLEND_UNAPPROVED_BYTE_CHANGE"); untouched.update(raw.subarray(position));
  const table = Buffer.from(decoded.table), encoded = [], changedFrames = [];
  for (const frame of decoded.frames) {
    let data = frame.encoded;
    if (ranges.some(range => range.start < frame.end && range.end > frame.start)) {
      data = zlib.zstdCompressSync(after.subarray(frame.start, frame.end), { params: {
        [zlib.constants.ZSTD_c_compressionLevel]: 3, [zlib.constants.ZSTD_c_checksumFlag]: 1,
      } });
      check(data.length <= 0xffffffff, "ZSTD_REENCODED_FRAME_SIZE");
      table.writeUInt32LE(data.length, 8 + frame.index * 8); changedFrames.push(frame.index);
    }
    encoded.push(data);
  }
  const buffer = ranges.length ? Buffer.concat([...encoded, table]) : input;
  // Re-decode the actual output container, including the rebuilt seek table.
  const output = decodeSeekable(buffer); check(output.raw.equals(after), "ZSTD_OUTPUT_READBACK_MISMATCH");
  const finalFields = locateFields(output.raw, parseBlocks(output.raw));
  check(JSON.stringify(finalFields.fields) === JSON.stringify(located.fields.map(({ nonzero_tail_bytes, ...field }) => field)), "SDNA_OUTPUT_LAYOUT_CHANGED");
  return { buffer, changed: ranges.length > 0, proof: {
    schema: "asterion.blender-cstring-tail-proof.v1", blender_header: HEADER.toString(), pointer_bytes: 8, bhead_bytes: 32,
    sdna_sha256: located.sdna_sha256, sdna_structures: located.struct_count,
    decompressed_bytes: raw.length, before_decompressed_sha256: sha256(raw), after_decompressed_sha256: sha256(after),
    all_other_decompressed_bytes_identical: true, unchanged_decompressed_segments_sha256: untouched.digest("hex").toUpperCase(),
    only_allowlisted_post_nul_bytes_zeroed: true, live_cstrings_unchanged: true, fields: located.fields,
    changed_ranges: ranges, zeroed_bytes: ranges.reduce((n, range) => n + range.bytes, 0),
    changed_compressed_frame_indices: changedFrames, unchanged_compressed_frames: decoded.frames.length - changedFrames.length,
    seek_table_frame_count: decoded.frames.length, seek_table_descriptor: decoded.descriptor,
    independently_reopened_in_blender: false,
  } };
}

function relative(value) {
  check(typeof value === "string" && value && !/[\\:\x00-\x1f]/.test(value)
    && !value.split("/").some(part => !part || part === "." || part === ".." || /[. ]$/.test(part)
      || /^(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)/i.test(part)), "PATH_INVALID"); return value;
}
function ordinary(root, value) {
  relative(value); let target = root;
  for (const part of value.split("/")) {
    target = path.join(target, part); const info = fs.lstatSync(target, { throwIfNoEntry: false });
    check(!info?.isSymbolicLink(), "PATH_SYMLINK");
    if (info && target !== path.join(root, value)) check(info.isDirectory(), "PATH_NOT_DIRECTORY");
  }
  return target;
}
function put(root, value, bytes) {
  const target = ordinary(root, value); check(!fs.existsSync(target), "DESTINATION_EXISTS");
  fs.mkdirSync(path.dirname(target), { recursive: true }); ordinary(root, value);
  fs.writeFileSync(target, bytes, { flag: "wx" });
  check(fs.readFileSync(target).equals(bytes), "OUTPUT_READBACK_MISMATCH");
}

export function writeTailCopies({ repoRoot = process.cwd(), inputRoot, outputRoot, reportPath, summary,
  paths = null, verifyExisting = false }) {
  const repo = fs.realpathSync(repoRoot);
  for (const value of [inputRoot, outputRoot, reportPath]) { relative(value); check(value.startsWith(".private/"), "PATH_PRIVATE_REQUIRED"); ordinary(repo, value); }
  check(inputRoot !== outputRoot && !inputRoot.startsWith(outputRoot + "/") && !outputRoot.startsWith(inputRoot + "/"), "PATH_SEPARATE_MIRRORS_REQUIRED");
  check(!reportPath.startsWith(outputRoot + "/") && !reportPath.startsWith(inputRoot + "/"), "PATH_REPORT_OUTSIDE_MIRRORS_REQUIRED");
  check(!fs.existsSync(ordinary(repo, reportPath)), "DESTINATION_EXISTS");
  check(Array.isArray(summary?.files) && summary.files.length > 0, "SOURCE_SUMMARY_REQUIRED");
  const selected = paths === null ? summary.files : summary.files.filter(row => paths.includes(row.path));
  check(selected.length > 0 && (paths === null || selected.length === new Set(paths).size), "PATH_SELECTION_MISMATCH");
  check(new Set(selected.map(row => row.path)).size === selected.length, "PATH_DUPLICATE_SOURCE");
  const read = row => {
    relative(row.path); check(/^assets\/3d\/source\/.+\.blend$/.test(row.path), "PATH_SOURCE_SCOPE");
    const bytes = fs.readFileSync(ordinary(repo, `${inputRoot}/${row.path}`));
    check(sha256(bytes) === row.after_sha256 && bytes.length === row.after_bytes, "SOURCE_HASH_MISMATCH"); return bytes;
  };
  const records = [];
  // Validate all paths, hashes and output collisions before the first write.
  for (const row of selected) {
    read(row); const target = ordinary(repo, `${outputRoot}/${row.path}`);
    check(verifyExisting || !fs.existsSync(target), "DESTINATION_EXISTS");
  }
  const dependencies = summary.auxiliary_byte_identical_dependencies ?? [];
  for (const row of dependencies) {
    relative(row.path); check(/^(?:public\/assets\/|assets\/3d\/).+\.png$/.test(row.path), "PATH_DEPENDENCY_SCOPE");
    const bytes = fs.readFileSync(ordinary(repo, row.path)); check(sha256(bytes) === row.sha256 && bytes.length === row.bytes, "SOURCE_DEPENDENCY_HASH");
    const target = ordinary(repo, `${outputRoot}/${row.path}`);
    if (fs.existsSync(target)) check(sha256(fs.readFileSync(target)) === row.sha256, "SOURCE_DEPENDENCY_COLLISION");
  }
  const scriptSha = sha256(fs.readFileSync(fileURLToPath(import.meta.url)));
  for (const row of selected) {
    const input = read(row), result = cleanBlendTails(input), outputPath = `${outputRoot}/${row.path}`;
    const target = ordinary(repo, outputPath), reused = fs.existsSync(target);
    if (reused) check(verifyExisting && fs.readFileSync(target).equals(result.buffer), "DESTINATION_EXISTING_MISMATCH");
    else put(repo, outputPath, result.buffer);
    check(sha256(read(row)) === row.after_sha256, "SOURCE_CHANGED_DURING_COPY");
    records.push({ path: row.path, before_sha256: row.after_sha256, before_bytes: row.after_bytes,
      after_sha256: sha256(result.buffer), after_bytes: result.buffer.length,
      original_source_binding: { sha256: row.before_sha256, bytes: row.before_bytes },
      proof: { ...result.proof, code_sha256: scriptSha, source_bytes_unchanged: true,
        candidate_readback_verified: true, reused_existing_read_only: reused } });
  }
  for (const row of dependencies) {
    const value = `${outputRoot}/${row.path}`;
    if (!fs.existsSync(ordinary(repo, value))) put(repo, value, fs.readFileSync(ordinary(repo, row.path)));
    check(sha256(fs.readFileSync(ordinary(repo, value))) === row.sha256, "SOURCE_DEPENDENCY_READBACK");
  }
  const report = { schema: "asterion.blender-cstring-tail-copy.v1", code_sha256: scriptSha,
    source_media_written: false, input_stage: "RNA-sanitized intermediate candidate",
    notice: "The before binding refers to the intermediate RNA copy. Final publication must retain the original source binding and independent Blender semantic reopen proof.",
    files: records, auxiliary_byte_identical_dependencies: dependencies };
  put(repo, reportPath, Buffer.from(JSON.stringify(report, null, 2) + "\n")); return report;
}

function main() {
  const options = { paths: [] }; let verifyExisting = false;
  for (let i = 2; i < process.argv.length; i++) {
    const name = process.argv[i]; if (name === "--verify-existing") { verifyExisting = true; continue; }
    const value = process.argv[++i]; check(value && ["--summary", "--report", "--path"].includes(name), "ARGUMENTS_INVALID");
    if (name === "--path") options.paths.push(value); else options[name.slice(2)] = value;
  }
  check(options.summary && options.report, "ARGUMENTS_REQUIRED");
  const repo = fs.realpathSync(process.cwd()); relative(options.summary); check(options.summary.startsWith(".private/"), "PATH_PRIVATE_REQUIRED");
  const summary = JSON.parse(fs.readFileSync(ordinary(repo, options.summary)));
  const result = writeTailCopies({ repoRoot: repo, inputRoot: ".private/publication-2026-09-07/blender-candidates",
    outputRoot: ".private/publication-2026-09-07/blender-final-candidates", reportPath: options.report,
    summary, paths: options.paths.length ? options.paths : null, verifyExisting });
  console.log(JSON.stringify({ files: result.files.length, zeroed_bytes: result.files.reduce((n, row) => n + row.proof.zeroed_bytes, 0), source_media_written: false }));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(); } catch (error) { console.error(JSON.stringify({ error: /^[A-Z][A-Z_]+$/.test(error.message) ? error.message : "TAIL_COPY_FAILED" })); process.exitCode = 1; }
}
