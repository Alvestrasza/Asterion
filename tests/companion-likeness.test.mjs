import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { AnimationMixer } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { companion3DModelAsset, ASTERION_REQUIRED_CLIPS } from "../lib/companion-3d.ts";
import { inspectCompanionArmor, setCompanionArmorVisible } from "../lib/companion-equipment.ts";

const kinds = ["asterion", "pony", "rabbit", "cat", "dog", "orc", "fairy", "elf"];
const revision = kind => kind === "asterion" ? "sculpt-v005" : "sculpt-v004";
const root = new URL("../", import.meta.url);
const file = path => readFile(new URL(path, root));
const json = async path => JSON.parse(await file(path));
const sha = value => createHash("sha256").update(value).digest("hex").toUpperCase();

test("all eight routes select the current facial revision while likeness history remains preserved", () => {
  for (const kind of kinds) assert.equal(companion3DModelAsset(kind), `/assets/3d/${kind}/${kind}-${kind === "asterion" ? "sculpt-v006" : "sculpt-v005"}.glb`);
});

test("comparison layouts bind the actual final manifests, approved art and old/new GLB renders", async () => {
  const gallery = await json("assets/3d/reference/companions/sculpt-v004/gallery-manifest.json");
  assert.equal(gallery.likeness_accepted, false);
  assert.equal(gallery.source_files_modified, false);
  assert.deepEqual(gallery.figures.map(figure => figure.kind), kinds);
  assert.equal(sha(await file(gallery.gallery)), gallery.sha256);
  assert.equal(sha(await file("assets/3d/source/companions/sculpt-v004/gallery.py")), gallery.assembly_script_sha256);
  for (const figure of gallery.figures) {
    assert.equal(figure.manifest, `assets/3d/source/${figure.kind}/${revision(figure.kind)}/manifest.json`);
    for (const field of ["manifest", "reference", "previous", "current", "comparison"]) {
      assert.equal(sha(await file(figure[field])), figure[`${field}_sha256`]);
    }
    const manifest = await json(figure.manifest);
    assert.equal(figure.reference_sha256, manifest.reference_sha256);
    assert.equal(figure.current_sha256, manifest.import_renders.hero.sha256);
  }
});

test("Selya's gemstone roots belong to the same detachable outfit as their bezels", async () => {
  const v = await json("assets/3d/reference/fairy/sculpt-v004/validation.json");
  for (const rootName of ["AST_Selya_throat_emerald", "AST_Selya_heart_waist_emerald"]) {
    assert.ok(v.changes.equipment_source_objects.includes(rootName), `${rootName} must be detachable`);
    assert.ok(v.changes.equipment_source_objects.includes(`${rootName}_gold_bezel`));
    assert.ok(!v.changes.body_source_objects.includes(rootName));
  }
});

for (const kind of kinds) {
  test(`${kind} likeness delivery binds source, original reference, builders and fresh import evidence`, async () => {
    const m = await json(`assets/3d/source/${kind}/${revision(kind)}/manifest.json`);
    assert.equal(sha(await file(m.source)), m.source_sha256);
    const buffer = await file(m.model);
    assert.equal(sha(buffer), m.model_sha256);
    assert.equal(sha(await file(m.reference)), m.reference_sha256);
    assert.equal(sha(await file(m.validation)), m.validation_sha256);
    for (const [path, hash] of Object.entries(m.input_sha256)) assert.equal(sha(await file(path)), hash, path);
    const v = await json(m.validation);
    assert.equal(v.passed, true);
    assert.equal(v.checks.authored_eyes_survive_source_reopen, true);
    assert.equal(v.checks.meaningful_geometry_refinement, true);
    assert.notEqual(m.model_sha256, v.input_sha256[`public/assets/3d/${kind}/${kind}-${kind === "asterion" ? "sculpt-v004" : "sculpt-v003"}.glb`]);
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
    assert.ok(m.triangles < (kind === "asterion" ? 8_000_000 : 2_000_000) && buffer.length < (kind === "asterion" ? 80_000_000 : 25_000_000) && m.draw_calls < 40);
    assert.equal(doc.images?.length ?? 0, 0);
    assert.ok(doc.buffers.every(b => b.uri === undefined));
    const bodyNames = new Set(v.changes.body_source_objects);
    if (kind === "dog") {
      assert.ok([...bodyNames].some(n => n.includes("haunch_cream_crescent")));
      const clearance = v.changes.pendant_clearance;
      assert.ok(clearance.measured_clearance >= .024);
      assert.ok(clearance.footprint_fur_vertices > 20_000);
      assert.equal(clearance.family.length, 7);
      assert.equal(clearance.bib_deleted_or_hidden, false);
      assert.equal(clearance.original_tab_collar_ring_unchanged, true);
    }
    if (kind === "asterion") {
      assert.equal(v.changes.head_mane_omitted, true);
      const hair = v.hair_evidence;
      assert.deepEqual(Object.keys(hair.correspondence), ["tail"]);
      assert.ok(hair.native_objects.every(obj => obj.group === "tail" && obj.physics.length === 0));
      assert.equal(hair.native_strands, 3582);
      assert.equal(hair.native_points, 50148);
      assert.ok(hair.correspondence.tail.passed);
      assert.ok(hair.correspondence.tail.max_center_error_world < 1e-5);
      assert.ok(hair.correspondence.tail.max_radius_error_world_bound < 1e-5);
    }
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
      for (const name of ["AST_Brumo_v3_base_under_tunic", "AST_Brumo_v3_base_shorts"]) assert.ok(bodyNames.has(name));
    }
    if (kind === "orc" || kind === "elf") {
      const joints = v.changes.body_joint_completion.connectors;
      assert.ok(joints.length >= (kind === "orc" ? 6 : 5));
      for (const joint of joints) {
        assert.equal(joint.component, "body");
        assert.ok(bodyNames.has(joint.name));
        assert.ok(!v.changes.equipment_source_objects.includes(joint.name));
        assert.equal(joint.closed_manifold, true);
        assert.equal(joint.non_two_face_edges, 0);
        assert.equal(joint.finite_geometry, true);
        assert.equal(joint.finite_normalized_known_rig_weights, true);
        assert.ok(joint.triangles > 0);
      }
    }
  });

  test(`${kind} likeness decoded outfit toggles while body, original bones and animation continue`, async () => {
    const buffer = await file(`public/assets/3d/${kind}/${kind}-${revision(kind)}.glb`);
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
