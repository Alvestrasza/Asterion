import test from "node:test";
import assert from "node:assert/strict";
import { AnimationClip, AnimationMixer, Bone, Group, Mesh, MeshBasicMaterial, NumberKeyframeTrack, Skeleton, SkinnedMesh } from "three";
import { inspectCompanionArmor, setCompanionArmorVisible } from "../lib/companion-equipment.ts";

function makeOutfit(id = "ceremonial-gold-v1") {
  const outfit = new Group();
  outfit.userData = {
    asterion_component: "armor",
    asterion_equipment_slot: "outfit",
    asterion_equipment_id: id
  };
  return outfit;
}

test("metadata toggles the whole outfit, including nested material primitives, without hiding the body", () => {
  const root = new Group();
  const body = new SkinnedMesh();
  body.userData.asterion_component = "body";
  const outfit = makeOutfit();
  const nested = new Group();
  const gold = new SkinnedMesh();
  const blue = new SkinnedMesh();
  nested.add(blue);
  outfit.add(gold, nested);
  root.add(body, outfit);
  const hierarchy = [body.parent, outfit.parent, gold.parent, blue.parent];

  assert.deepEqual(inspectCompanionArmor(root), { outfits: 1, visibleOutfits: 1, meshes: 2, visibleMeshes: 2 });
  for (let repeat = 0; repeat < 3; repeat++) {
    assert.deepEqual(setCompanionArmorVisible(root, false), { outfits: 1, visibleOutfits: 0, meshes: 2, visibleMeshes: 0 });
    assert.equal(body.visible, true);
    assert.equal(gold.visible, true, "Hide the outfit root, not its individual primitives");
    assert.equal(blue.visible, true);
    assert.deepEqual(setCompanionArmorVisible(root, true), { outfits: 1, visibleOutfits: 1, meshes: 2, visibleMeshes: 2 });
  }
  assert.deepEqual([body.parent, outfit.parent, gold.parent, blue.parent], hierarchy);
});

test("missing or incomplete extras and suggestive names or colors never identify equipment", () => {
  const root = new Group();
  for (const metadata of [
    {}, { asterion_component: "armor" },
    { asterion_component: "armor", asterion_equipment_slot: "outfit" },
    { asterion_component: "body", asterion_equipment_slot: "outfit", asterion_equipment_id: "ceremonial-gold-v1" },
    { asterion_component: "armor", asterion_equipment_slot: "head", asterion_equipment_id: "ceremonial-gold-v1" },
    { asterion_component: "armor", asterion_equipment_slot: "outfit", asterion_equipment_id: "" }
  ]) {
    const mesh = new Mesh(undefined, new MeshBasicMaterial({ color: 0xffcc44 }));
    mesh.name = "AST_Armor_Gold";
    mesh.userData = metadata;
    root.add(mesh);
  }
  assert.deepEqual(setCompanionArmorVisible(root, false), { outfits: 0, visibleOutfits: 0, meshes: 0, visibleMeshes: 0 });
  assert.ok(root.children.every(child => child.visible));
});

test("inspection reports effective visibility and preserves authored hidden primitives", () => {
  const root = new Group();
  const parent = new Group();
  const outfit = makeOutfit();
  const shown = new Mesh();
  const hidden = new Mesh();
  hidden.visible = false;
  const invisibleMaterial = new Mesh(undefined, new MeshBasicMaterial({ visible: false }));
  outfit.add(shown, hidden, invisibleMaterial);
  parent.add(outfit);
  root.add(parent);
  assert.deepEqual(setCompanionArmorVisible(root, true), { outfits: 1, visibleOutfits: 1, meshes: 3, visibleMeshes: 1 });
  parent.visible = false;
  assert.deepEqual(setCompanionArmorVisible(root, true), { outfits: 1, visibleOutfits: 0, meshes: 3, visibleMeshes: 0 });
  parent.visible = true;
  setCompanionArmorVisible(root, false);
  setCompanionArmorVisible(root, true);
  assert.equal(hidden.visible, false);
  assert.equal(invisibleMaterial.material.visible, false);
});

test("duplicate descendant extras are treated as one outfit and future outfit IDs use the same slot", () => {
  const root = new Group();
  const outfit = makeOutfit("future-reward-outfit");
  const primitive = new SkinnedMesh();
  primitive.userData = { ...outfit.userData };
  outfit.add(primitive);
  root.add(outfit);
  assert.deepEqual(setCompanionArmorVisible(root, false), { outfits: 1, visibleOutfits: 0, meshes: 1, visibleMeshes: 0 });
  assert.equal(primitive.visible, true);
});

test("equipment toggling does not replace the shared skeleton or restart a real running animation", () => {
  const root = new Group();
  const bone = new Bone();
  bone.name = "head";
  const skeleton = new Skeleton([bone]);
  const body = new SkinnedMesh();
  const armor = new SkinnedMesh();
  body.bind(skeleton);
  armor.bind(skeleton);
  armor.userData = makeOutfit().userData;
  root.add(bone, body, armor);
  const clip = new AnimationClip("idle", 2, [new NumberKeyframeTrack("head.position[x]", [0, 2], [0, 2])]);
  const mixer = new AnimationMixer(root);
  const action = mixer.clipAction(clip).play();
  mixer.update(0.5);
  assert.equal(action.time, 0.5);
  setCompanionArmorVisible(root, false);
  assert.equal(action.time, 0.5);
  mixer.update(0.25);
  assert.equal(action.time, 0.75);
  assert.equal(bone.position.x, 0.75);
  setCompanionArmorVisible(root, true);
  assert.equal(action.time, 0.75);
  assert.equal(body.skeleton, skeleton);
  assert.equal(armor.skeleton, skeleton);
  assert.equal(mixer.existingAction(clip), action);
  assert.equal(body.visible, true);
  mixer.stopAllAction();
});
