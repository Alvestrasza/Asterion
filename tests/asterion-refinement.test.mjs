import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { publishedHash } from "../scripts/asset-publication/rebind.mjs";
import { ASTERION_REQUIRED_CLIPS } from "../lib/companion-3d.ts";

const root = new URL("../", import.meta.url);
const sha = (bytes) => createHash("sha256").update(bytes).digest("hex").toUpperCase();
const json = async (path) => JSON.parse(await readFile(new URL(path, root), "utf8"));

test("Asterion v002 is the requested approximately five-million-triangle delivery", async () => {
  const buffer = await readFile(new URL("public/assets/3d/asterion/asterion-sculpt-v002.glb", root));
  assert.equal(buffer.toString("ascii", 0, 4), "glTF");
  assert.equal(buffer.readUInt32LE(4), 2);
  assert.equal(buffer.readUInt32LE(8), buffer.length);
  const gltf = JSON.parse(buffer.toString("utf8", 20, 20 + buffer.readUInt32LE(12)).trim());
  const triangles = gltf.meshes.flatMap(({ primitives }) => primitives)
    .reduce((sum, primitive) => sum + gltf.accessors[primitive.indices].count / 3, 0);
  assert.ok(triangles >= 4_500_000 && triangles <= 5_500_000);
  assert.ok(buffer.length > 20_000_000 && buffer.length < 100_000_000);
  assert.equal(gltf.meshes.length, 1);
  assert.equal(gltf.skins.length, 1);
  assert.equal(gltf.skins[0].joints.length, 22);
  assert.deepEqual(gltf.animations.map(({ name }) => name).sort(), [...ASTERION_REQUIRED_CLIPS].sort());
  assert.ok(gltf.meshes[0].primitives.length < 40);
  assert.ok(gltf.materials.some(({ name }) => /hair|groom/i.test(name)));
  const navy = gltf.materials.find(({ name }) => name === "AST_navy");
  const gold = gltf.materials.find(({ name }) => name === "AST_gold");
  assert.ok(navy.pbrMetallicRoughness.baseColorFactor[2] < 0.1, "navy must not export white");
  assert.ok(gold.pbrMetallicRoughness.baseColorFactor[0] > gold.pbrMetallicRoughness.baseColorFactor[2] * 3);
  assert.equal(gltf.images?.length ?? 0, 0);
  assert.equal(gltf.cameras, undefined);
  assert.equal(gltf.extensions?.KHR_lights_punctual, undefined);
  assert.ok(gltf.buffers.every(({ uri }) => uri === undefined));
  assert.deepEqual(gltf.extensionsRequired, ["EXT_meshopt_compression"]);
  for (const primitive of gltf.meshes[0].primitives) {
    assert.equal(primitive.mode ?? 4, 4);
    assert.notEqual(primitive.attributes.JOINTS_0, undefined);
    assert.notEqual(primitive.attributes.WEIGHTS_0, undefined);
  }
});

test("Asterion v002 binds the editable native-hair source and independent validation", async () => {
  const manifest = await json("assets/3d/source/asterion/sculpt-v002/manifest.json");
  assert.equal(manifest.version, "sculpt-v002");
  assert.equal(manifest.source_sha256, sha(await readFile(new URL(manifest.source, root))));
  assert.equal(manifest.model_sha256, sha(await readFile(new URL(manifest.model, root))));
  assert.equal(manifest.reference_sha256, sha(await readFile(new URL(manifest.reference, root))));
  for (const [path, digest] of Object.entries(manifest.builder_sha256)) {
    assert.equal(sha(await readFile(new URL(path, root))), digest, path);
  }
  assert.equal(manifest.native_hair, true);
  assert.ok(manifest.hair_strands > 1000);
  assert.equal(manifest.hair_physics, false);
  assert.equal(manifest.animations_unchanged, true);
  assert.equal(manifest.human_likeness_accepted, false);
  assert.equal(manifest.mobile_performance_accepted, false);
  const validation = await json(manifest.validation);
  assert.equal(validation.passed, true);
  assert.equal(validation.master_sha256, manifest.source_sha256);
  assert.equal(validation.glb_sha256, manifest.model_sha256);
  assert.ok(Object.values(validation.checks).every((value) => value === true));
});

test("Asterion refinement preserves original authoring anchors through explicit metadata publication bindings", async () => {
  const preserved = {
    "assets/3d/source/asterion/sculpt-v001/asterion-sculpt-v001.blend": "AD7976E6715D5528E67959E6B8C29B6B42D9C3C699CCBAB085AC3A47593D42E0",
    "public/assets/3d/asterion/asterion-sculpt-v001.glb": "EE133C744A11C37FDC447963094E2C4F7614441FC6CDC5127960FFD7135FD165",
    "assets/3d/reference/asterion/sculpt-v001/asterion-approved-turnaround.png": "FE91A72F21A139CB4443E7BDE99498FC7AF7D07B8784A5F4A0B48CC37A141AEC"
  };
  for (const [path, digest] of Object.entries(preserved)) {
    assert.equal(sha(await readFile(new URL(path, root))), publishedHash(root, path, digest), path);
  }
});
