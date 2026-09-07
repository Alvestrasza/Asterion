import test from "node:test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createReadStream } from "node:fs";
import { readFile } from "node:fs/promises";
import { AnimationMixer, Matrix4 } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { inspectCompanionArmor, setCompanionArmorVisible } from "../lib/companion-equipment.ts";

// Fixed delivery boundary from sculpt-v005/contract.py and deliver.py. Do not
// derive expected revisions, evidence sets, or acceptance from a candidate.
const kinds = ["asterion", "pony", "rabbit", "cat", "dog", "orc", "fairy", "elf"];
const names = ["Asterion", "Caelo", "Liora", "Nyra", "Fenn", "Brumo", "Selya", "Aelira"];
const clips = ["idle", "blink", "happy", "eat", "play", "pet_reaction", "sleep", "wake", "walk"];
const revision = kind => kind === "asterion" ? "sculpt-v006" : "sculpt-v005";
const baseline = kind => kind === "asterion" ? "sculpt-v005" : "sculpt-v004";
const boneCount = kind => kind === "asterion" ? 22 : ["orc", "elf"].includes(kind) ? 10 : kind === "fairy" ? 12 : 13;
const reference = kind => kind === "asterion"
  ? "assets/3d/reference/asterion/sculpt-v004/asterion-approved-turnaround.png"
  : `public/assets/companions/${kind}.png`;
const root = new URL("../", import.meta.url);
const file = path => readFile(new URL(path, root));
const json = async path => JSON.parse(await file(path));
const keysEqual = (actual, expected, label) => assert.deepEqual([...actual].sort(), [...expected].sort(), label);
const assertHash = value => assert.match(value, /^[A-F0-9]{64}$/);
const faceViews = ["face-hero", "face-front", "face-side", "blink-early", "blink-partial", "blink-closed"];
const viewSets = {
  source: [...faceViews, "hero", "rear", "body-hero"],
  import: [...faceViews, "hero", "body-hero"],
  baseline: ["face-hero", "face-front", "face-side"],
};
const scopeChecks = ["explicit_face_only_allowlist", "nonface_geometry_unchanged", "nonface_materials_unchanged",
  "all_unedited_source_objects_retained", "original_lid_pivots_unchanged", "meaningful_face_geometry_refinement"];
const checks = [...scopeChecks, "face_geometry_survives_source_reopen", "all_protected_geometry_survives_source_reopen",
  "all_protected_materials_survive_source_reopen", "six_facial_views_present", "finite_evaluated_partial_blinks",
  "original_rest_rig_unchanged", "original_constraints_drivers_unchanged", "all_original_action_data_unchanged",
  "original_frame_rate_unchanged", "two_character_meshes", "exact_distinct_components", "one_original_shared_skin",
  "nine_original_clips", "only_public_extras", "skinned_triangle_primitives", "under_40_primitives",
  "within_species_triangle_budget", "self_contained_no_projection", "no_editor_stage", "meshopt",
  "within_species_byte_budget", "finite_imported_geometry", "valid_normalized_known_weights",
  "bounded_importer_triangle_difference", "nine_clips_match_historical_import", "two_imported_components",
  "imported_equipment_metadata", "all_historical_and_builder_inputs_unchanged"];
const hairChecks = ["native_curves_present", "at_least_1000_native_strands", "native_points_radii_static_finite",
  "matching_native_export_groups", "all_native_points_match_export_tube_rings"];

function inputPaths(kind) {
  const previous = baseline(kind);
  const module = kind === "asterion" ? "asterion/sculpt-v006/face.py" : `companions/sculpt-v005/${
    ["pony", "rabbit"].includes(kind) ? "equine_lapine" : ["cat", "dog"].includes(kind) ? "feline_canine" : "folk"}_faces.py`;
  return [
    `assets/3d/source/${kind}/${previous}/${kind}-${previous}.blend`,
    `public/assets/3d/${kind}/${kind}-${previous}.glb`, reference(kind),
    "assets/3d/source/companions/sculpt-v001/common.py",
    "assets/3d/source/asterion/sculpt-v001/build_sculpt.py", "assets/3d/source/asterion/sculpt-v001/rig_delivery.py",
    "assets/3d/source/asterion/sculpt-v002/validate_refinement.py", "assets/3d/source/asterion/sculpt-v003/build_head_study.py",
    "assets/3d/source/asterion/sculpt-v004/export_equipment.py",
    ...["build.py", "refinements.py", "export_equipment.py"].map(name => `assets/3d/source/companions/sculpt-v004/${name}`),
    ...["build.py", "contract.py", "guards.py"].map(name => `assets/3d/source/companions/sculpt-v005/${name}`),
    `assets/3d/source/${module}`,
    ...(["cat", "dog"].includes(kind) ? ["assets/3d/source/cat/sculpt-v002/nyra_detail.py"] : []),
  ];
}

async function boundHash(path, expected) {
  assertHash(expected);
  assert.ok(typeof path === "string" && !path.includes("\\") && !path.split("/").includes(".."));
  const url = new URL(path, root);
  assert.ok(url.href.startsWith(root.href), `Repository-local evidence: ${path}`);
  const hash = createHash("sha256");
  // Stream large Blender masters instead of retaining every input in RAM.
  for await (const chunk of createReadStream(url)) hash.update(chunk);
  assert.equal(hash.digest("hex").toUpperCase(), expected, path);
}

function hashMap(values, label) {
  assert.ok(values && Object.keys(values).length > 0, label);
  for (const [name, value] of Object.entries(values)) {
    assert.ok(name.length > 0, label);
    assertHash(value);
  }
}

function sourceNames(report) {
  return [...report.changes.body_source_objects, ...report.changes.equipment_source_objects,
    ...(report.hair_evidence?.native_objects ?? []).map(object => object.name)];
}

function validateScope(report, previous) {
  const scope = report.face_scope, changes = report.changes;
  keysEqual(Object.keys(scope.checks), scopeChecks, "Exact source-scope checks");
  assert.ok(Object.values(scope.checks).every(value => value === true));
  assert.deepEqual(scope.invalid_face_objects, []);
  assert.ok(scope.protected_object_count >= 20 && scope.protected_material_count >= 1);
  for (const key of ["protected_geometry_sha256", "protected_material_sha256",
    "original_face_geometry_sha256", "candidate_face_geometry_sha256"]) hashMap(scope[key], key);
  assert.equal(Object.keys(scope.protected_geometry_sha256).length, scope.protected_object_count);
  assert.equal(Object.keys(scope.protected_material_sha256).length, scope.protected_material_count);
  const allowed = new Set(changes.face_objects), removed = new Set(changes.removed_face_objects);
  assert.equal(allowed.size, changes.face_objects.length, "Unique explicit face allowlist");
  assert.equal(removed.size, changes.removed_face_objects.length, "Unique removed-face records");
  assert.ok(allowed.size >= 3);
  const oldNames = sourceNames(previous), newNames = sourceNames(report);
  assert.equal(new Set(oldNames).size, oldNames.length);
  assert.equal(new Set(newNames).size, newNames.length);
  keysEqual(Object.keys(scope.original_face_geometry_sha256), oldNames.filter(name => allowed.has(name)));
  keysEqual(Object.keys(scope.candidate_face_geometry_sha256), newNames.filter(name => allowed.has(name)));
  keysEqual(Object.keys(scope.protected_geometry_sha256), oldNames.filter(name => !allowed.has(name)));
  keysEqual(newNames.filter(name => !allowed.has(name)), Object.keys(scope.protected_geometry_sha256));
  keysEqual(oldNames.filter(name => !newNames.includes(name)), removed);
  for (const name of allowed) {
    assert.ok(removed.has(name) || changes.body_source_objects.includes(name), `${name} must be a facial body part`);
    assert.ok(!changes.equipment_source_objects.includes(name), `${name} cannot alter equipment`);
    assert.doesNotMatch(name.toLowerCase(), /horn|diadem|forehead_lance|hair|crown|mane|(^|_)ear[_.]|leaf_ear|ear_swept/);
  }
  assert.ok([...removed].every(name => allowed.has(name)));
  assert.deepEqual(changes.added_base_clothing, []);
  assert.ok(changes.edited_objects.every(edit => allowed.has(edit.name) && typeof edit.operation === "string"));
  const meaningful = changes.edited_objects.filter(edit =>
    (Number.isFinite(edit.max_displacement) && edit.max_displacement > 1e-4) ||
    (Number.isInteger(edit.new_vertices) && edit.new_vertices > 0));
  assert.ok(meaningful.length >= 3, "At least three measured geometry edits");
  assert.ok([...allowed].filter(name => scope.original_face_geometry_sha256[name] !== scope.candidate_face_geometry_sha256[name]).length >= 3);
  assert.deepEqual(scope.original_lid_pivots, scope.candidate_lid_pivots);
  assert.ok(Object.keys(scope.original_lid_pivots).length >= 2);
  for (const [name, pivot] of Object.entries(scope.original_lid_pivots)) {
    assert.ok(allowed.has(name), `${name} is an explicitly protected facial pivot`);
    assert.equal(pivot.length, 3);
    assert.ok(pivot.every(Number.isFinite));
  }
  assert.deepEqual(report.source_blink_samples.map(sample => sample.frame), [1, 5, 7, 8, 9, 10, 12, 16, 24]);
  for (const sample of report.source_blink_samples) {
    assert.equal(sample.nonfinite_coordinates, 0);
    assert.ok(Number.isInteger(sample.evaluated_vertices) && sample.evaluated_vertices > 0);
  }
}

function validateRig(report, previous, kind) {
  assert.deepEqual(report.original_rig, previous.candidate_rig, "Bound historical rig, not two unanchored matching claims");
  assert.deepEqual(report.original_rig, report.candidate_rig, "Full published rest/behavior/action records unchanged");
  const rig = report.candidate_rig;
  assertHash(rig.rest_sha256); assertHash(rig.behavior_sha256);
  assert.equal(rig.bones, boneCount(kind)); assert.equal(rig.fps, 30); assert.equal(rig.fps_base, 1);
  keysEqual(Object.keys(rig.actions), clips);
  keysEqual(Object.keys(report.motion_comparison), clips);
  for (const clip of clips) {
    const action = rig.actions[clip], motion = report.motion_comparison[clip];
    assertHash(action.sha256);
    assert.equal(action.finite_keys, true);
    assert.ok(Number.isInteger(action.key_count) && action.key_count > 0);
    assert.ok(Number.isInteger(action.curve_count) && action.curve_count > 0);
    assert.equal(action.frame_range.length, 2);
    assert.ok(action.frame_range.every(Number.isFinite) && action.frame_range[1] > action.frame_range[0]);
    assert.equal(motion.passed, true); assert.equal(motion.finite, true); assert.equal(motion.same_bone_names, true);
    assert.equal(motion.sample_count, 9); assert.equal(motion.tolerance, 2e-4);
    assert.ok(Number.isFinite(motion.max_world_skin_matrix_component_error) && motion.max_world_skin_matrix_component_error >= 0 && motion.max_world_skin_matrix_component_error <= 2e-4);
    assert.ok(Number.isFinite(motion.duration_error_seconds) && motion.duration_error_seconds >= 0 && motion.duration_error_seconds <= 1e-5);
  }
}

function componentExtras(kind, component) {
  const data = { asterion_component: component, asterion_rig: `${kind}-rig-v1` };
  if (component === "armor") Object.assign(data, { asterion_equipment_slot: "outfit",
    asterion_equipment_id: kind === "asterion" ? "ceremonial-gold-v1" : `${kind}-outfit-v1` });
  return data;
}

function glbDocument(buffer, manifest) {
  assert.equal(buffer.toString("ascii", 0, 4), "glTF");
  assert.equal(buffer.readUInt32LE(4), 2); assert.equal(buffer.readUInt32LE(8), buffer.length);
  assert.equal(buffer.toString("ascii", 16, 20), "JSON");
  const doc = JSON.parse(buffer.toString("utf8", 20, 20 + buffer.readUInt32LE(12)).trim());
  assert.equal(doc.meshes.length, 2); assert.equal(doc.skins.length, 1);
  const nodes = doc.nodes.filter(node => node.mesh !== undefined);
  assert.equal(nodes.length, 2); assert.equal(new Set(nodes.map(node => node.mesh)).size, 2);
  keysEqual(nodes.map(node => node.extras.asterion_component), ["armor", "body"]);
  assert.equal(doc.skins[0].joints.length, boneCount(manifest.kind));
  assert.equal(new Set(doc.skins[0].joints).size, boneCount(manifest.kind));
  let triangles = 0, primitives = 0;
  for (const node of nodes) {
    assert.equal(node.skin, 0);
    assert.deepEqual(node.extras, componentExtras(manifest.kind, node.extras.asterion_component));
    const parts = doc.meshes[node.mesh].primitives;
    const count = parts.reduce((sum, part) => sum + doc.accessors[part.indices].count / 3, 0);
    assert.deepEqual(manifest.components[node.extras.asterion_component], { mesh: node.mesh, skin: 0, triangles: count, primitives: parts.length });
    for (const part of parts) {
      assert.equal(part.mode ?? 4, 4);
      for (const name of ["POSITION", "JOINTS_0", "WEIGHTS_0"]) assert.ok(Number.isInteger(part.attributes[name]));
    }
    assert.ok(Number.isInteger(count) && count > 0);
    triangles += count; primitives += parts.length;
  }
  assert.equal(triangles, manifest.triangles); assert.equal(primitives, manifest.draw_calls);
  assert.equal(doc.materials.length, manifest.materials); assert.equal(buffer.length, manifest.bytes);
  assert.ok(primitives > 0 && primitives < 40);
  assert.ok(triangles < (manifest.kind === "asterion" ? 8_000_000 : 2_000_000));
  assert.ok(buffer.length < (manifest.kind === "asterion" ? 80_000_000 : 25_000_000));
  assert.equal(doc.images?.length ?? 0, 0); assert.equal(doc.cameras?.length ?? 0, 0);
  assert.ok(doc.buffers.length > 0 && doc.buffers.every(item => item.uri === undefined));
  assert.ok(doc.extensionsUsed.includes("EXT_meshopt_compression"));
  assert.equal(doc.extensions?.KHR_lights_punctual, undefined);
  keysEqual(doc.animations.map(action => action.name), clips);
  return doc;
}

async function decode(path) {
  const buffer = await file(path);
  const gltf = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(
    buffer.buffer.slice(buffer.byteOffset, buffer.byteOffset + buffer.byteLength), "");
  const meshes = [], components = [];
  gltf.scene.traverse(object => {
    if (object.isSkinnedMesh) meshes.push(object);
    if (object.userData.asterion_component && !object.parent?.userData.asterion_component) components.push(object);
  });
  assert.ok(meshes.length >= 2);
  const skeleton = meshes[0].skeleton;
  assert.ok(meshes.every(mesh => mesh.skeleton.bones.length === skeleton.bones.length &&
    mesh.skeleton.bones.every((bone, index) => bone === skeleton.bones[index])));
  const mixer = new AnimationMixer(gltf.scene);
  return { gltf, buffer, meshes, components, skeleton, mixer };
}

function skinSample(asset, clip, fraction) {
  asset.mixer.stopAllAction();
  const action = asset.mixer.clipAction(clip).reset().play();
  action.time = clip.duration * fraction;
  asset.mixer.update(0); asset.gltf.scene.updateMatrixWorld(true);
  return asset.skeleton.bones.map((bone, index) =>
    new Matrix4().multiplyMatrices(bone.matrixWorld, asset.skeleton.boneInverses[index]).elements);
}

function dispose(asset) {
  if (!asset) return;
  asset.mixer.stopAllAction(); asset.mixer.uncacheRoot(asset.gltf.scene);
  const materials = new Set();
  for (const mesh of asset.meshes) {
    mesh.geometry.dispose();
    for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) materials.add(material);
  }
  materials.forEach(material => material.dispose());
}

for (const kind of kinds) {
  test(`${kind} face-only delivery binds fixed inputs, source scope, original actions and all review views`, async () => {
    const version = revision(kind), review = `assets/3d/reference/${kind}/${version}`;
    const m = await json(`assets/3d/source/${kind}/${version}/manifest.json`);
    const paths = { source: `assets/3d/source/${kind}/${version}/${kind}-${version}.blend`,
      model: `public/assets/3d/${kind}/${kind}-${version}.glb`, reference: `${review}/original.png`, validation: `${review}/validation.json` };
    for (const [field, path] of Object.entries(paths)) {
      assert.equal(m[field], path); await boundHash(path, m[`${field}_sha256`]);
    }
    const v = await json(paths.validation);
    for (const document of [m, v]) {
      assert.equal(document.schema, "asterion-face-only-v1"); assert.equal(document.kind, kind);
      assert.equal(document.name, names[kinds.indexOf(kind)]); assert.equal(document.version, version);
      for (const claim of ["human_likeness_accepted", "mobile_performance_accepted", "projection_used", "paid_provider_used", "compression_lossless"]) assert.equal(document[claim], false, claim);
      assert.match(document.animation_limit, /no anatomical closure/i);
      assert.match(document.likeness_limit, /not a 100-percent likeness/i);
      assert.equal(document.package_status, "Local hash-checked Blender delivery; no game-dev canonical receipt.");
      keysEqual(document.clips, clips); assert.equal(document.bones, boneCount(kind));
    }
    for (const field of ["face_scope_only", "nonface_unchanged", "animations_unchanged", "equipment_separate", "fresh_import_passed"]) assert.equal(m[field], true, field);
    assert.equal(v.passed, true); assert.equal(v.nonface_unchanged, true);
    for (const field of ["source_sha256", "model_sha256", "reference_sha256", "triangles", "bytes", "bones", "draw_calls", "materials", "components"]) assert.deepEqual(m[field], v[field], field);
    assert.equal(v.reference_input, reference(kind)); await boundHash(reference(kind), m.reference_sha256);
    keysEqual(Object.keys(v.checks), [...checks, ...(kind === "asterion" ? hairChecks : [])]);
    assert.ok(Object.values(v.checks).every(value => value === true));
    assert.deepEqual(m.input_sha256, v.input_sha256);
    keysEqual(Object.keys(m.input_sha256), inputPaths(kind), "No missing or substituted builder inputs");
    for (const [path, hash] of Object.entries(m.input_sha256)) await boundHash(path, hash);
    assert.notEqual(m.model_sha256, m.input_sha256[`public/assets/3d/${kind}/${kind}-${baseline(kind)}.glb`]);
    const oldManifest = await json(`assets/3d/source/${kind}/${baseline(kind)}/manifest.json`);
    await boundHash(oldManifest.validation, oldManifest.validation_sha256);
    assert.equal(oldManifest.source_sha256, m.input_sha256[oldManifest.source]);
    assert.equal(oldManifest.model_sha256, m.input_sha256[oldManifest.model]);
    const old = await json(oldManifest.validation);
    validateRig(v, old, kind); validateScope(v, old);
    assert.equal(m.edited_objects, v.changes.edited_objects.length);
    assert.equal(m.protected_object_count, v.face_scope.protected_object_count);
    assert.equal(m.protected_material_count, v.face_scope.protected_material_count);
    for (const [category, expected] of Object.entries(viewSets)) {
      const renders = m[{ source: "renders", import: "import_renders", baseline: "baseline_renders" }[category]];
      assert.deepEqual(renders, v[`${category}_views`]); keysEqual(Object.keys(renders), expected);
      for (const [view, render] of Object.entries(renders)) {
        assert.equal(render.file, `${review}/${category}/${kind}-${view}.png`);
        assert.equal(render.clip, view.startsWith("blink-") ? "blink" : "idle");
        assert.equal(render.frame, ({ "blink-early": 5, "blink-partial": 7, "blink-closed": 10 })[view] ?? 1);
        await boundHash(render.file, render.sha256);
      }
    }
  });

  test(`${kind} decoded face GLB retains two components, the shared rig, nine clips and live outfit toggling`, async () => {
    const m = await json(`assets/3d/source/${kind}/${revision(kind)}/manifest.json`);
    let candidate, previous;
    try {
      candidate = await decode(m.model);
      glbDocument(candidate.buffer, m);
      previous = await decode(`public/assets/3d/${kind}/${kind}-${baseline(kind)}.glb`);
      keysEqual(candidate.components.map(object => object.userData.asterion_component), ["armor", "body"]);
      for (const component of candidate.components) {
        // GLTFLoader preserves the authored node name alongside public extras.
        const { name, ...extras } = component.userData;
        assert.equal(name, `${kind}_${extras.asterion_component}`);
        assert.deepEqual(extras, componentExtras(kind, extras.asterion_component));
      }
      assert.equal(candidate.skeleton.bones.length, boneCount(kind));
      assert.deepEqual(candidate.skeleton.bones.map(bone => bone.name), previous.skeleton.bones.map(bone => bone.name));
      keysEqual(candidate.gltf.animations.map(clip => clip.name), clips);
      keysEqual(previous.gltf.animations.map(clip => clip.name), clips);
      const positions = candidate.meshes.map(mesh => mesh.geometry.getAttribute("position"));
      const body = candidate.components.find(object => object.userData.asterion_component === "body");
      const outfit = inspectCompanionArmor(candidate.gltf.scene);
      assert.equal(outfit.outfits, 1); assert.equal(outfit.visibleOutfits, 1); assert.ok(outfit.visibleMeshes > 0);
      for (const name of clips) {
        const clip = candidate.gltf.animations.find(action => action.name === name);
        const oldClip = previous.gltf.animations.find(action => action.name === name);
        assert.ok(clip.duration > 0 && Math.abs(clip.duration - oldClip.duration) <= 1e-5, name);
        assert.ok(clip.tracks.length > 0 && clip.tracks.every(track => track.times.length > 0 && track.values.every(Number.isFinite)));
        for (let sample = 0; sample < 9; sample++) {
          const current = skinSample(candidate, clip, sample / 8), old = skinSample(previous, oldClip, sample / 8);
          for (let bone = 0; bone < current.length; bone++) for (let element = 0; element < 16; element++) {
            assert.ok(Number.isFinite(current[bone][element]) && Number.isFinite(old[bone][element]));
            assert.ok(Math.abs(current[bone][element] - old[bone][element]) <= 2e-4, `${name}: sample ${sample}, bone ${bone}, matrix ${element}`);
          }
        }
        const action = candidate.mixer.clipAction(clip).reset().play(); candidate.mixer.update(.03);
        const time = action.time;
        assert.equal(setCompanionArmorVisible(candidate.gltf.scene, false).visibleMeshes, 0);
        assert.equal(body.visible, true); assert.equal(action.time, time);
        candidate.mixer.update(.03); assert.ok(action.time > time);
        assert.deepEqual(setCompanionArmorVisible(candidate.gltf.scene, true), outfit);
        assert.ok(candidate.meshes.every((mesh, index) => mesh.geometry.getAttribute("position") === positions[index]));
      }
    } finally { dispose(candidate); dispose(previous); }
  });
}
