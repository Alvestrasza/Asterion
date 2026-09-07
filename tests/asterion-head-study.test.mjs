import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { publishedHash } from "../scripts/asset-publication/rebind.mjs";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { ASTERION_REQUIRED_CLIPS } from "../lib/companion-3d.ts";

const root = new URL("../", import.meta.url);
const sha = (b) => createHash("sha256").update(b).digest("hex").toUpperCase();
const json = async (p) => JSON.parse(await readFile(new URL(p, root), "utf8"));

test("Asterion head study removes head hair from the actual portable geometry", async () => {
  const buffer = await readFile(new URL("public/assets/3d/asterion/asterion-sculpt-v003.glb", root));
  const doc = JSON.parse(buffer.toString("utf8", 20, 20 + buffer.readUInt32LE(12)).trim());
  const triangles = doc.meshes.flatMap(m => m.primitives).reduce((n,p) => n + doc.accessors[p.indices].count / 3, 0);
  assert.equal(triangles, 3_051_226); // v002 minus its four measured head-hair groups.
  assert.equal(doc.meshes.length, 1);
  assert.equal(doc.skins.length, 1);
  assert.equal(doc.skins[0].joints.length, 22);
  assert.deepEqual(doc.animations.map(a => a.name).sort(), [...ASTERION_REQUIRED_CLIPS].sort());
  const tailJoint = doc.skins[0].joints.findIndex(i => doc.nodes[i].name === "tail.01");
  assert.ok(tailJoint >= 0);
  const loader = new GLTFLoader().setMeshoptDecoder(MeshoptDecoder);
  const loaded = await loader.parseAsync(buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength), "");
  let hairVertices = 0;
  loaded.scene.traverse(o => {
    if (!o.isMesh || !/groom/.test(o.material.name)) return;
    const indices = o.geometry.getAttribute("skinIndex"), weights = o.geometry.getAttribute("skinWeight");
    hairVertices += indices.count;
    for (let i=0; i<indices.count; i++) {
      for (let k=0; k<4; k++) {
        if (weights.getComponent(i,k) > 0) assert.equal(indices.getComponent(i,k), tailJoint, "No head-bound hair may remain");
      }
    }
  });
  assert.ok(hairVertices > 1000, "Tail hair must remain");
});

test("Asterion head study binds preserved solid geometry, tail hair and animation evidence", async () => {
  const m = await json("assets/3d/source/asterion/sculpt-v003/manifest.json");
  assert.equal(m.head_hair_removed, true);
  assert.deepEqual(m.hair_groups, ["tail"]);
  assert.equal(m.hair_strands, 3582);
  assert.equal(m.animations_unchanged, true);
  assert.equal(m.retained_geometry_unchanged, true);
  assert.equal(m.source_sha256, sha(await readFile(new URL(m.source, root))));
  assert.equal(m.model_sha256, sha(await readFile(new URL(m.model, root))));
  const v = await json(m.validation);
  assert.equal(v.passed, true);
  assert.equal(v.source_sha256, m.source_sha256);
  assert.equal(v.model_sha256, m.model_sha256);
  assert.equal(v.removed_objects.length, 8);
  assert.ok(Object.values(v.checks).every(x => x === true));
  for (const [path,digest] of Object.entries(m.builder_sha256)) {
    assert.equal(sha(await readFile(new URL(path, root))), digest, path);
  }
});

test("Asterion's complete v002 hair retains its authoring anchor and documented publication copy", async () => {
  const source = "assets/3d/source/asterion/sculpt-v002/asterion-sculpt-v002.blend";
  assert.equal(sha(await readFile(new URL(source, root))), publishedHash(root, source, "7984098FE471690C511F253B3BC584D2F7E7F473087B72E1EBE00C38663FF10E"));
  assert.equal(sha(await readFile(new URL("public/assets/3d/asterion/asterion-sculpt-v002.glb", root))), "5DDC901135C30D85B82760AA026B8146ED1E90ABBA15E600F2FB69DF6DB08838");
});
