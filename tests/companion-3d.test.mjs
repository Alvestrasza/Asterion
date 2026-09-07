import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { publishedHash } from "../scripts/asset-publication/rebind.mjs";

import {
  ASTERION_MODEL_ASSET,
  ASTERION_REQUIRED_CLIPS,
  asterionClipForCareAction,
  asterionClipForPresentation,
  companion3DModelAsset
} from "../lib/companion-3d.ts";

const MODEL_PATH = new URL("../public/assets/3d/asterion/asterion-sculpt-v001.glb", import.meta.url);

function readGlbJson(buffer) {
  assert.equal(buffer.toString("ascii", 0, 4), "glTF");
  assert.equal(buffer.readUInt32LE(4), 2);
  assert.equal(buffer.readUInt32LE(8), buffer.length);
  const jsonLength = buffer.readUInt32LE(12);
  assert.equal(buffer.toString("ascii", 16, 20), "JSON");
  return JSON.parse(buffer.toString("utf8", 20, 20 + jsonLength).trim());
}

test("every companion resolves its own current versioned 3D figure", () => {
  assert.equal(ASTERION_MODEL_ASSET, "/assets/3d/asterion/asterion-sculpt-v006.glb");
  assert.equal(companion3DModelAsset("asterion"), ASTERION_MODEL_ASSET);
  for (const kind of ["rabbit", "cat", "orc", "pony", "fairy", "dog", "elf"]) {
    const version = "sculpt-v005";
    assert.equal(companion3DModelAsset(kind), `/assets/3d/${kind}/${kind}-${version}.glb`);
  }
});

test("care actions and mood presentations select stable Asterion clips", () => {
  assert.equal(asterionClipForCareAction("feed"), "eat");
  assert.equal(asterionClipForCareAction("play"), "play");
  assert.equal(asterionClipForCareAction("pet"), "pet_reaction");
  assert.equal(asterionClipForCareAction("sleep"), "sleep");
  assert.equal(asterionClipForCareAction("wake"), "wake");
  assert.equal(asterionClipForPresentation("idle", true), "sleep");
  assert.equal(asterionClipForPresentation("idle", false), "idle");
  assert.equal(asterionClipForPresentation("waiting", false), "walk");
  assert.equal(asterionClipForPresentation("failed", false), "sleep");
  assert.equal(asterionClipForPresentation("waving", false), "happy");
  assert.equal(asterionClipForPresentation("review", false), "idle");
});

test("historical Asterion v001 GLB remains self-contained with its original production contract", async () => {
  const buffer = await readFile(MODEL_PATH);
  const gltf = readGlbJson(buffer);
  const animationNames = gltf.animations.map((animation) => animation.name).sort();
  const triangleCount = gltf.meshes.reduce(
    (meshTotal, mesh) =>
      meshTotal +
      mesh.primitives.reduce((primitiveTotal, primitive) => {
        assert.equal(primitive.mode ?? 4, 4);
        return primitiveTotal + gltf.accessors[primitive.indices].count / 3;
      }, 0),
    0
  );

  assert.ok(buffer.length > 10_000_000 && buffer.length < 30_000_000);
  assert.deepEqual(animationNames, [...ASTERION_REQUIRED_CLIPS].sort());
  assert.ok(triangleCount > 1_000_000 && triangleCount < 2_000_000);
  assert.equal(gltf.meshes.length, 1);
  assert.ok(gltf.materials.length <= 24);
  const eyeMaterial = gltf.materials.find((material) => material.name === "AST_Eye_living_azure");
  assert.ok(eyeMaterial, "The authored vertex-colored eye material must survive export");
  assert.ok(
    eyeMaterial.emissiveFactor === undefined || eyeMaterial.emissiveFactor.every((channel) => channel === 0),
    "Eye emission must not export as a constant gray wash over its vertex colors"
  );
  assert.equal(gltf.skins.length, 1);
  assert.equal(gltf.skins[0].joints.length, 22);
  assert.equal(gltf.cameras, undefined);
  assert.equal(gltf.extensions?.KHR_lights_punctual, undefined);
  assert.ok(gltf.extensionsUsed.includes("EXT_meshopt_compression"));
  assert.deepEqual(gltf.extensionsRequired, ["EXT_meshopt_compression"]);
  assert.equal(gltf.images?.length ?? 0, 0);
  assert.ok(gltf.buffers.every((buffer) => buffer.uri === undefined));
  assert.ok(gltf.meshes[0].primitives.some((primitive) => primitive.attributes.COLOR_0 !== undefined));
  const primitives = gltf.meshes[0].primitives;
  assert.ok(primitives.length <= 24);
  for (const primitive of primitives) {
    assert.notEqual(primitive.attributes.JOINTS_0, undefined);
    assert.notEqual(primitive.attributes.WEIGHTS_0, undefined);
  }
  const positions = primitives.map((primitive) => gltf.accessors[primitive.attributes.POSITION]);
  const spans = [0, 1, 2].map((axis) =>
    Math.max(...positions.map((accessor) => accessor.max[axis])) -
    Math.min(...positions.map((accessor) => accessor.min[axis]))
  );
  // glTF is Y-up: a full quadruped must have genuine width, height, and depth.
  assert.ok(spans[0] > 2 && spans[1] > 5 && spans[2] > 4);
});

for (const kind of ["rabbit", "cat", "orc", "pony", "fairy", "dog", "elf"]) {
  test(`${kind} historical v002 delivery remains a distinct volumetric skinned model with nine clips`, async () => {
    const version = "sculpt-v002";
    const path = new URL(`../public/assets/3d/${kind}/${kind}-${version}.glb`, import.meta.url);
    const buffer = await readFile(path);
    const gltf = readGlbJson(buffer);
    const manifest = JSON.parse(await readFile(new URL(`../assets/3d/source/${kind}/${version}/manifest.json`, import.meta.url), "utf8"));
    assert.equal(manifest.kind, kind);
    assert.equal(manifest.model_sha256, createHash("sha256").update(buffer).digest("hex").toUpperCase());
    const source = await readFile(new URL(`../${manifest.source}`, import.meta.url));
    assert.equal(createHash("sha256").update(source).digest("hex").toUpperCase(), manifest.source_sha256);
    const reference = await readFile(new URL(`../public/assets/companions/${kind}.png`, import.meta.url));
    assert.equal(createHash("sha256").update(reference).digest("hex").toUpperCase(), manifest.reference_sha256);
    for (const [path, digest] of Object.entries(manifest.builder_sha256)) {
      const builder = await readFile(new URL(`../${path}`, import.meta.url));
      assert.equal(createHash("sha256").update(builder).digest("hex").toUpperCase(), digest, `${kind}: builder ${path}`);
    }
    assert.equal(manifest.fresh_import_passed, true);
    assert.equal(manifest.mobile_performance_accepted, false);
    assert.ok(buffer.length > 1_000_000 && buffer.length < 20_000_000);
    assert.equal(gltf.meshes.length, 1);
    assert.equal(gltf.skins.length, 1);
    assert.ok(gltf.skins[0].joints.length >= 10);
    assert.deepEqual(gltf.animations.map(({ name }) => name).sort(), [...ASTERION_REQUIRED_CLIPS].sort());
    assert.equal(gltf.images?.length ?? 0, 0, "Source artwork must not become a projected image plane");
    assert.equal(gltf.cameras, undefined);
    assert.equal(gltf.extensions?.KHR_lights_punctual, undefined);
    assert.ok(gltf.buffers.every(({ uri }) => uri === undefined));
    assert.deepEqual(gltf.extensionsRequired, ["EXT_meshopt_compression"]);
    const primitives = gltf.meshes[0].primitives;
    assert.ok(primitives.length < 40, "Preserve a bounded material draw-call count");
    let triangles = 0;
    for (const primitive of primitives) {
      assert.equal(primitive.mode ?? 4, 4);
      assert.notEqual(primitive.attributes.JOINTS_0, undefined);
      assert.notEqual(primitive.attributes.WEIGHTS_0, undefined);
      triangles += gltf.accessors[primitive.indices].count / 3;
    }
    // Aelira's folded mantle and modeled leaf embroidery justify a bounded
    // 1.6M authoring allowance; this is not a mobile-performance acceptance.
    const triangleBudget = kind === "elf" ? 1_600_000 : 1_500_000;
    assert.ok(triangles > 100_000 && triangles < triangleBudget);
    const positions = primitives.map(({ attributes }) => gltf.accessors[attributes.POSITION]);
    const spans = [0, 1, 2].map((axis) => Math.max(...positions.map(({ max }) => max[axis])) -
      Math.min(...positions.map(({ min }) => min[axis])));
    assert.ok(spans[0] > .7 && spans[1] > 2 && spans[2] > .5, "Full width, height and depth in Y-up glTF");
    const eyes = gltf.materials.flatMap((material, index) => material.name.endsWith("_living_iris") ? [index] : []);
    assert.equal(eyes.length, 2);
    for (const index of eyes) {
      assert.ok(primitives.some(({ material, attributes }) => material === index && attributes.COLOR_0 !== undefined));
      assert.ok((gltf.materials[index].emissiveFactor ?? [0, 0, 0]).every((value) => value === 0));
    }
  });
}

test("Reference refinements preserve all original v001 masters, exports and artwork", async () => {
  for (const kind of ["rabbit", "cat", "orc", "pony", "fairy", "dog", "elf"]) {
    const manifest = JSON.parse(await readFile(new URL(`../assets/3d/source/${kind}/sculpt-v001/manifest.json`, import.meta.url), "utf8"));
    for (const [path, hash] of [[manifest.model, manifest.model_sha256], [manifest.source, manifest.source_sha256],
      [`public/assets/companions/${kind}.png`, manifest.reference_sha256]]) {
      const content = await readFile(new URL(`../${path}`, import.meta.url));
      assert.equal(createHash("sha256").update(content).digest("hex").toUpperCase(), hash, `${kind}: historical ${path}`);
    }
  }
});

test("Remaining refinements preserve Caelo and Liora authoring anchors through documented publication copies", async () => {
  const checkpoints = {
    pony: ["EEA0A5E90849567838D69E906EEBA45F175B48132C28D5E589CA4A7EE86D0847", "8ACBEFF75EE53A76D1FEC1798A61232957A142A1E4B7E68BCE5B277786B61153"],
    rabbit: ["D6ED849A0528157E60D98D15E349D4630D5344C777B51BCFAE36F7D0508085C1", "2C0F4479A9FAF1004812BFF5AF878A975A08C108D4CA0F034942AA87FAAFFB25"]
  };
  for (const [kind, [sourceHash, modelHash]] of Object.entries(checkpoints)) {
    for (const [path, hash] of [
      [`assets/3d/source/${kind}/sculpt-v002/${kind}-sculpt-v002.blend`, sourceHash],
      [`public/assets/3d/${kind}/${kind}-sculpt-v002.glb`, modelHash]
    ]) {
      const content = await readFile(new URL(`../${path}`, import.meta.url));
      assert.equal(createHash("sha256").update(content).digest("hex").toUpperCase(), publishedHash(new URL("../", import.meta.url), path, hash));
    }
  }
});

for (const kind of ["rabbit", "cat", "orc", "pony", "fairy", "dog", "elf"]) {
  test(`${kind} v002 binds independent import and full-mesh motion evidence to its actual delivery`, async () => {
    const buffer = await readFile(new URL(`../public/assets/3d/${kind}/${kind}-sculpt-v002.glb`, import.meta.url));
    const digest = createHash("sha256").update(buffer).digest("hex").toUpperCase();
    const motion = JSON.parse(await readFile(new URL(`../assets/3d/reference/${kind}/sculpt-v002/motion-validation.json`, import.meta.url), "utf8"));
    const validation = JSON.parse(await readFile(new URL(`../assets/3d/reference/${kind}/sculpt-v002/import-validation.json`, import.meta.url), "utf8"));
    assert.equal(validation.sha256, digest);
    assert.equal(validation.passed, true);
    assert.equal(Object.keys(validation.checks).length, 19);
    assert.ok(Object.values(validation.checks).every(value => value === true));
    if (["cat", "orc", "fairy", "dog", "elf"].includes(kind)) {
      const master = await readFile(new URL(`../assets/3d/source/${kind}/sculpt-v002/${kind}-sculpt-v002.blend`, import.meta.url));
      assert.equal(validation.master_sha256, createHash("sha256").update(master).digest("hex").toUpperCase());
    }
    assert.equal(motion.source_sha256, digest);
    assert.equal(motion.passed, true);
    assert.equal(motion.samples.length, 6);
    assert.ok(motion.samples.every(({ finite, evaluated_vertices }) => finite && evaluated_vertices > 100_000));
    for (const clip of ["idle", "sleep", "walk"]) {
      const comparison = motion.loop_comparisons[clip];
      assert.equal(typeof comparison.max_vertex_distance, "number");
      assert.equal(comparison.within_tolerance, true);
      assert.ok(comparison.max_vertex_distance <= 1e-4);
    }
    assert.equal(motion.collision_free_verified, false);
  });
}
