import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { publishedHash } from "../scripts/asset-publication/rebind.mjs";
import { AnimationMixer } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { companion3DModelAsset, ASTERION_REQUIRED_CLIPS } from "../lib/companion-3d.ts";
import { inspectCompanionArmor, setCompanionArmorVisible } from "../lib/companion-equipment.ts";

const kinds = ["pony", "rabbit", "cat", "dog", "orc", "fairy", "elf"];
const root = new URL("../", import.meta.url);
const file = path => readFile(new URL(path, root));
const json = async path => JSON.parse(await file(path));
const sha = value => createHash("sha256").update(value).digest("hex").toUpperCase();

test("all seven companion routes select the latest modular face revision", () => {
  for (const kind of kinds) assert.equal(companion3DModelAsset(kind), `/assets/3d/${kind}/${kind}-sculpt-v005.glb`);
});

test("Selya's gemstone roots belong to the same detachable outfit as their bezels", async () => {
  const v = await json("assets/3d/reference/fairy/sculpt-v003/validation.json");
  for (const rootName of ["AST_Selya_throat_emerald", "AST_Selya_heart_waist_emerald"]) {
    assert.ok(v.changes.equipment_source_objects.includes(rootName), `${rootName} must be detachable`);
    assert.ok(v.changes.equipment_source_objects.includes(`${rootName}_gold_bezel`));
    assert.ok(!v.changes.body_source_objects.includes(rootName));
  }
});

for (const kind of kinds) {
  test(`${kind} modular delivery binds source, original reference, builders and fresh import evidence`, async () => {
    const m = await json(`assets/3d/source/${kind}/sculpt-v003/manifest.json`);
    assert.equal(sha(await file(m.source)), m.source_sha256);
    const buffer = await file(m.model);
    assert.equal(sha(buffer), m.model_sha256);
    assert.equal(sha(await file(m.reference)), m.reference_sha256);
    assert.equal(sha(await file(m.validation)), m.validation_sha256);
    for (const [path, hash] of Object.entries(m.input_sha256)) assert.equal(sha(await file(path)), hash, path);
    const v = await json(m.validation);
    assert.equal(v.passed, true);
    assert.ok(Object.values(v.checks).every(value => value === true));
    assert.ok(m.edited_objects >= 8);
    assert.equal(m.animations_unchanged, true);
    assert.equal(m.mobile_performance_accepted, false);
    assert.equal(m.human_likeness_accepted, false);
    assert.equal(v.original_rig.rest_sha256, v.candidate_rig.rest_sha256);
    for (const clip of ASTERION_REQUIRED_CLIPS) {
      assert.equal(v.original_rig.actions[clip].sha256, v.candidate_rig.actions[clip].sha256);
      assert.equal(v.motion_comparison[clip].passed, true);
      assert.equal(v.motion_comparison[clip].sample_count, 9);
      assert.ok(v.motion_comparison[clip].max_world_skin_matrix_component_error <= 2e-4);
    }
    for (const render of Object.values({ ...m.renders, ...Object.fromEntries(Object.entries(m.import_renders).map(([k, value]) => [`import-${k}`, value])) })) {
      assert.equal(sha(await file(render.file)), render.sha256);
    }
    const doc = JSON.parse(buffer.toString("utf8", 20, 20 + buffer.readUInt32LE(12)).trim());
    assert.equal(doc.meshes.length, 2);
    assert.equal(doc.skins.length, 1);
    const nodes = doc.nodes.filter(n => n.mesh !== undefined);
    assert.deepEqual(nodes.map(n => n.extras.asterion_component).sort(), ["armor", "body"]);
    assert.ok(nodes.every(n => n.skin === 0 && n.extras.asterion_rig === `${kind}-rig-v1`));
    assert.deepEqual(doc.animations.map(a => a.name).sort(), [...ASTERION_REQUIRED_CLIPS].sort());
    assert.ok(m.triangles < 2_000_000 && buffer.length < 25_000_000 && m.draw_calls < 40);
    assert.equal(doc.images?.length ?? 0, 0);
    assert.ok(doc.buffers.every(b => b.uri === undefined));
    const bodyNames = new Set(v.changes.body_source_objects);
    if (kind === "dog") assert.ok([...bodyNames].some(n => n.includes("haunch_cream_crescent")));
    if (kind === "fairy") {
      for (const name of ["AST_Selya_throat_emerald", "AST_Selya_heart_waist_emerald"]) {
        assert.ok(v.changes.equipment_source_objects.includes(name), `${name} must hide together with its bezel`);
        assert.ok(!bodyNames.has(name));
      }
      assert.ok([...bodyNames].some(n => n.includes("fitted_mint_bodice")));
      assert.ok([...bodyNames].some(n => n.includes("dress_tier_0_petal")));
      assert.ok([...bodyNames].some(n => n.includes("dress_tier_1_petal")));
      assert.ok([...bodyNames].some(n => n.includes("upper_wing")));
      assert.ok(!v.changes.equipment_source_objects.some(n => n.includes("wing")));
    }
    if (kind === "elf") for (const part of ["cream_tunic", "forest_trouser", "shaped_boot"])
      assert.ok([...bodyNames].some(n => n.includes(part)));
    if (kind === "orc") {
      assert.equal(v.changes.added_base_clothing.length, 2);
      assert.ok(v.changes.added_base_clothing.every(n => bodyNames.has(n)));
    }
  });

  test(`${kind} actual decoded outfit toggles while body, original bones and animation continue`, async () => {
    const buffer = await file(`public/assets/3d/${kind}/${kind}-sculpt-v003.glb`);
    const gltf = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(
      buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength), "");
    const meshes = []; let body;
    gltf.scene.traverse(obj => {
      if (obj.isSkinnedMesh) meshes.push(obj);
      if (obj.userData.asterion_component === "body" && !body) body = obj;
    });
    assert.ok(body && meshes.length > 2);
    const bones = meshes[0].skeleton.bones;
    assert.ok(meshes.every(m => m.skeleton.bones.every((bone, i) => bone === bones[i])));
    const positions = meshes.map(m => m.geometry.getAttribute("position"));
    const mixer = new AnimationMixer(gltf.scene);
    const clip = gltf.animations.find(c => c.name === "walk");
    const action = mixer.clipAction(clip).play(); mixer.update(.31);
    const on = inspectCompanionArmor(gltf.scene);
    assert.equal(on.outfits, 1); assert.ok(on.visibleMeshes > 0);
    for (let i = 0; i < 3; i++) {
      const time = action.time;
      assert.equal(setCompanionArmorVisible(gltf.scene, false).visibleMeshes, 0);
      assert.equal(body.visible, true); assert.equal(action.time, time);
      assert.deepEqual(setCompanionArmorVisible(gltf.scene, true), on);
      mixer.update(.05); assert.ok(action.time > time);
    }
    assert.ok(meshes.every((m, i) => m.geometry.getAttribute("position") === positions[i]));
    mixer.stopAllAction();
    for (const mesh of meshes) {
      mesh.geometry.dispose();
      for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) material.dispose();
    }
  });
}

test("Asterion v004 retains its original authoring anchor and documented metadata publication copy", async () => {
  const source = "assets/3d/source/asterion/sculpt-v004/asterion-sculpt-v004.blend";
  assert.equal(sha(await file(source)), publishedHash(root, source, "07F6ECF1594F5D41BFE262367CA2188E48B942BCFF9F0A6C493EF18B04693822"));
  assert.equal(sha(await file("public/assets/3d/asterion/asterion-sculpt-v004.glb")), "CF14A6363C19B8C1B599C5C89181A63B31296CC97B72A0299C0230D9C81DF6CF");
});
