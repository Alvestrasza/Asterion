import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import zlib from "node:zlib";
import { cleanBlendTails, decodeSeekable, writeTailCopies, sha256 } from "../scripts/asset-publication/clean_blend_tails.mjs";

const u16 = n => { const b = Buffer.alloc(2); b.writeUInt16LE(n); return b; };
const u32 = n => { const b = Buffer.alloc(4); b.writeUInt32LE(n); return b; };
const align4 = b => Buffer.concat([b, Buffer.alloc((4 - b.length % 4) % 4)]);
function strings(tag, values) { return align4(Buffer.concat([Buffer.from(tag), u32(values.length), Buffer.from(values.join("\0") + "\0")])); }
function block(code, sdna, data, count = 1) {
  const b = Buffer.alloc(32); b.write(code, 0, "ascii"); b.writeUInt32LE(sdna, 4);
  b.writeBigUInt64LE(16n, 8); b.writeBigUInt64LE(BigInt(data.length), 16); b.writeBigUInt64LE(BigInt(count), 24);
  return Buffer.concat([b, data]);
}
function fixture({ terminated = true, wrongTargetType = false, badTlen = false } = {}) {
  const names = ["marker", "dir[1282]", "extra[14]", "flag", "pic[1024]", "other[8]", "sentinel", "r"];
  const types = ["char", "int", "FileSelectParams", "RenderData", "Scene", "Unrelated"];
  const lengths = [1, 4, 1300, 1036, 1040, 1282]; if (badTlen) lengths[2]++;
  const definitions = [[2, [[1, 0], [wrongTargetType ? 1 : 0, 1], [0, 2]]],
    [3, [[1, 3], [0, 4], [0, 5]]], [4, [[1, 6], [3, 7]]], [5, [[0, 1]]]];
  const dna = Buffer.concat([Buffer.from("SDNA"), strings("NAME", names), strings("TYPE", types),
    align4(Buffer.concat([Buffer.from("TLEN"), ...lengths.map(u16)])), Buffer.from("STRC"), u32(definitions.length),
    ...definitions.flatMap(([type, fields]) => [u16(type), u16(fields.length), ...fields.flatMap(([t, n]) => [u16(t), u16(n)])])]);
  const selection = Buffer.alloc(1300, 0x51); selection.fill(0, 4, 1286); Buffer.from("//\0old synthetic tail").copy(selection, 4);
  if (!terminated) selection.fill(0x41, 4, 1286);
  const scene = Buffer.alloc(1040, 0x52); scene.fill(0, 8, 1032); Buffer.from("//renders/\0old synthetic render tail").copy(scene, 8);
  const unrelated = Buffer.alloc(1282, 0x53); Buffer.from("//\0UNRELATED MUST SURVIVE").copy(unrelated);
  const head = Buffer.from("BLENDER17-01v0502"), a = block("DATA", 0, selection), b = block("SC\0\0", 2, scene);
  const raw = Buffer.concat([head, a, b, block("DATA", 3, unrelated), block("DNA1", 0, dna), block("ENDB", 0, Buffer.alloc(0), 0)]);
  return { raw, selectionStart: 17 + 32 + 4, renderStart: 17 + a.length + 32 + 8 };
}
function encode(raw, boundaries = [128, 1024]) {
  const ends = [...boundaries.filter(n => n < raw.length), raw.length], frames = [];
  let start = 0;
  for (const end of ends) { const part = raw.subarray(start, end); frames.push({ data: zlib.zstdCompressSync(part), size: part.length }); start = end; }
  const table = Buffer.concat([u32(0x184d2a5e), u32(frames.length * 8 + 9),
    ...frames.flatMap(f => [u32(f.data.length), u32(f.size)]), u32(frames.length), Buffer.from([0]), u32(0x8f92eab1)]);
  return Buffer.concat([...frames.map(f => f.data), table]);
}

test("SDNA cleanup zeros only post-NUL nonzero bytes in the two exact fields, across compressed frames", () => {
  const f = fixture(), input = encode(f.raw, [128, 1024, 4096]), original = Buffer.from(input), result = cleanBlendTails(input);
  const after = decodeSeekable(result.buffer).raw, expected = Buffer.from(f.raw);
  for (const [start, length] of [[f.selectionStart, 1282], [f.renderStart, 1024]]) {
    expected.fill(0, expected.indexOf(0, start) + 1, start + length);
  }
  assert.deepEqual(input, original); assert.deepEqual(after, expected);
  assert.equal(after.length, f.raw.length);
  assert.equal(result.proof.only_allowlisted_post_nul_bytes_zeroed, true);
  assert.equal(result.proof.all_other_decompressed_bytes_identical, true);
  assert.equal(result.proof.fields.length, 2);
  assert.ok(result.proof.changed_ranges.every(r => r.end > r.start && r.end - r.start === r.bytes));
  assert.equal(result.proof.zeroed_bytes, result.proof.changed_ranges.reduce((n, r) => n + r.bytes, 0));
  assert.ok(result.proof.unchanged_compressed_frames > 0);
  assert.equal(cleanBlendTails(result.buffer).changed, false);
});

test("unsupported Blender headers, truncated blocks, malformed SDNA and missing NUL fail closed", () => {
  const f = fixture(), badHeader = Buffer.from(f.raw); badHeader[16] = 0x33;
  const badLength = Buffer.from(f.raw); badLength.writeBigUInt64LE(999999n, 17 + 16);
  const badDna = Buffer.from(f.raw); badDna[badDna.lastIndexOf(Buffer.from("SDNA"))] = 0;
  for (const [index, raw] of [Buffer.alloc(0), f.raw.subarray(0, -1), badHeader, badLength, badDna,
    fixture({ badTlen: true }).raw, fixture({ wrongTargetType: true }).raw, fixture({ terminated: false }).raw].entries()) {
    assert.throws(() => cleanBlendTails(encode(raw)), /BLEND_|SDNA_|ZSTD_/, `Malformed fixture ${index}`);
  }
});

test("seek-table framing, consumed frame lengths, descriptors and decompressed sizes are strict", () => {
  const source = encode(fixture().raw), wrongMagic = Buffer.from(source), badSize = Buffer.from(source), checksum = Buffer.from(source);
  wrongMagic[wrongMagic.length - 1] ^= 1;
  const count = source.readUInt32LE(source.length - 9), start = source.length - count * 8 - 17;
  badSize.writeUInt32LE(0xffffffff, start + 12); checksum[checksum.length - 5] = 0x80;
  const corrupt = Buffer.from(source); corrupt[0] ^= 1;
  for (const input of [source.subarray(0, -1), wrongMagic, badSize, checksum, corrupt, Buffer.concat([source, Buffer.from([0])])]) {
    assert.throws(() => cleanBlendTails(input), /ZSTD_/);
  }
});

test("all cleaned live C-string prefixes, unrelated path-looking data and SDNA remain byte-identical", () => {
  const f = fixture(), result = cleanBlendTails(encode(f.raw)), after = decodeSeekable(result.buffer).raw;
  assert.ok(after.includes(Buffer.from("UNRELATED MUST SURVIVE")));
  for (const field of result.proof.fields) {
    assert.deepEqual(after.subarray(field.start, field.first_nul_offset + 1), f.raw.subarray(field.start, field.first_nul_offset + 1));
  }
  const dna = f.raw.indexOf(Buffer.from("SDNA")); assert.deepEqual(after.subarray(dna), f.raw.subarray(dna));
});

function workspace(t) {
  const repo = fs.mkdtempSync(path.join(os.tmpdir(), "asterion-blend-tail-test-"));
  t.after(() => { assert.ok(fs.realpathSync(repo).startsWith(fs.realpathSync(os.tmpdir()) + path.sep)); fs.rmSync(repo, { recursive: true }); });
  const relative = "assets/3d/source/synthetic/source.blend", input = encode(fixture().raw);
  const inputRoot = ".private/raw", outputRoot = ".private/final", reportPath = ".private/proof.json";
  const target = path.join(repo, inputRoot, relative); fs.mkdirSync(path.dirname(target), { recursive: true }); fs.writeFileSync(target, input);
  const summary = { files: [{ path: relative, before_sha256: "A".repeat(64), before_bytes: 100,
    after_sha256: sha256(input), after_bytes: input.length }] };
  return { repo, relative, input, options: { repoRoot: repo, inputRoot, outputRoot, reportPath, summary } };
}

test("copy is exclusive, source-bound, private and repeat verification never overwrites", t => {
  const f = workspace(t), report = writeTailCopies(f.options), entry = report.files[0];
  assert.equal(entry.before_sha256, sha256(f.input)); assert.notEqual(entry.before_sha256, entry.after_sha256);
  assert.deepEqual(fs.readFileSync(path.join(f.repo, f.options.inputRoot, f.relative)), f.input);
  assert.throws(() => writeTailCopies(f.options), /DESTINATION_EXISTS/);
  const candidate = fs.readFileSync(path.join(f.repo, f.options.outputRoot, f.relative));
  assert.throws(() => writeTailCopies({ ...f.options, reportPath: ".private/second.json" }), /DESTINATION_EXISTS/);
  const verified = writeTailCopies({ ...f.options, reportPath: ".private/verified.json", verifyExisting: true });
  assert.equal(verified.files[0].proof.reused_existing_read_only, true);
  assert.deepEqual(fs.readFileSync(path.join(f.repo, f.options.outputRoot, f.relative)), candidate);
});

test("stale hashes, escaping paths and linked destinations fail before output", t => {
  const f = workspace(t);
  const stale = structuredClone(f.options.summary); stale.files[0].after_sha256 = "B".repeat(64);
  assert.throws(() => writeTailCopies({ ...f.options, summary: stale }), /SOURCE_HASH/);
  for (const outputRoot of ["assets", "../escape", ".private/../assets", ".private", ".private/raw"]) {
    assert.throws(() => writeTailCopies({ ...f.options, outputRoot }), /PATH_/);
  }
  const escaping = structuredClone(f.options.summary); escaping.files[0].path = "assets/3d/../outside.blend";
  assert.throws(() => writeTailCopies({ ...f.options, summary: escaping }), /PATH_/);
  fs.symlinkSync(path.join(f.repo, f.options.inputRoot), path.join(f.repo, ".private/link"), process.platform === "win32" ? "junction" : "dir");
  assert.throws(() => writeTailCopies({ ...f.options, outputRoot: ".private/link" }), /PATH_SYMLINK/);
  assert.equal(fs.existsSync(path.join(f.repo, ".private/final")), false);
});
