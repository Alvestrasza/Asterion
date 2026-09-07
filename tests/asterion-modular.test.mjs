import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { publishedHash } from "../scripts/asset-publication/rebind.mjs";
import { AnimationMixer } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { ASTERION_REQUIRED_CLIPS } from "../lib/companion-3d.ts";
import { inspectCompanionArmor, setCompanionArmorVisible } from "../lib/companion-equipment.ts";

const root = new URL("../", import.meta.url);
const sha = bytes => createHash("sha256").update(bytes).digest("hex").toUpperCase();
const file = path => readFile(new URL(path, root));
const json = async path => JSON.parse(await file(path));

test("preserved Asterion v004 exports body and complete outfit as two independent shared-skin components", async () => {
  const buffer = await file("public/assets/3d/asterion/asterion-sculpt-v004.glb");
  assert.equal(buffer.toString("ascii",0,4),"glTF");
  assert.equal(buffer.readUInt32LE(8),buffer.length);
  const doc = JSON.parse(buffer.toString("utf8",20,20+buffer.readUInt32LE(12)).trim());
  const nodes=doc.nodes.filter(n => n.mesh !== undefined);
  assert.equal(doc.meshes.length,2);
  assert.equal(nodes.length,2);
  assert.deepEqual(nodes.map(n=>n.extras.asterion_component).sort(),["armor","body"]);
  assert.equal(doc.skins.length,1);
  assert.equal(doc.skins[0].joints.length,22);
  assert.ok(nodes.every(n=>n.skin===0));
  const armor=nodes.find(n=>n.extras.asterion_component==="armor");
  assert.equal(armor.extras.asterion_equipment_slot,"outfit");
  assert.equal(armor.extras.asterion_equipment_id,"ceremonial-gold-v1");
  assert.ok(nodes.every(n=>n.extras.asterion_rig==="asterion-rig-v1"));
  assert.deepEqual(doc.animations.map(a=>a.name).sort(),[...ASTERION_REQUIRED_CLIPS].sort());
  assert.equal(doc.images?.length??0,0);
  assert.ok(doc.buffers.every(b=>!b.uri));
});

test("actual decoded Asterion outfit toggles without touching body geometry, skeleton or running clip", async () => {
  const buffer = await file("public/assets/3d/asterion/asterion-sculpt-v004.glb");
  const gltf = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).parseAsync(
    buffer.buffer.slice(buffer.byteOffset,buffer.byteOffset+buffer.byteLength),"");
  let body,armor;
  gltf.scene.traverse(o=>{
    if(o.userData.asterion_component==="body" && !body)body=o;
    if(o.userData.asterion_component==="armor" && !armor)armor=o;
  });
  assert.ok(body && armor && body!==armor);
  const meshes=[];gltf.scene.traverse(o=>{if(o.isSkinnedMesh)meshes.push(o);});
  assert.ok(meshes.length>2,"Actual material primitives decoded");
  const bones=meshes[0].skeleton.bones;
  assert.ok(meshes.every(m=>m.skeleton.bones.every((b,i)=>b===bones[i])));
  const positions=meshes.map(m=>m.geometry.getAttribute("position"));
  const mixer=new AnimationMixer(gltf.scene);
  const clip=gltf.animations.find(c=>c.name==="walk");
  const action=mixer.clipAction(clip).play();mixer.update(.37);
  const time=action.time;
  const on=inspectCompanionArmor(gltf.scene);
  assert.equal(on.outfits,1);assert.ok(on.visibleMeshes>0);
  for(let i=0;i<3;i++) {
    const off=setCompanionArmorVisible(gltf.scene,false);
    assert.equal(off.visibleMeshes,0);assert.equal(body.visible,true);
    assert.equal(action.time,time);
    assert.deepEqual(setCompanionArmorVisible(gltf.scene,true),on);
  }
  assert.ok(meshes.every((m,i)=>m.geometry.getAttribute("position")===positions[i]));
  mixer.update(.1);assert.ok(action.time>time);
  assert.equal(mixer.existingAction(clip),action);
  mixer.stopAllAction();
});

test("modular Asterion binds measured face/contact improvements and independent export evidence", async () => {
  const m=await json("assets/3d/source/asterion/sculpt-v004/manifest.json");
  const build=await json(m.build_report), validation=await json(m.validation);
  assert.equal(m.source_sha256,sha(await file(m.source)));
  assert.equal(m.model_sha256,sha(await file(m.model)));
  assert.equal(build.source_sha256,m.source_sha256);
  assert.equal(validation.source_sha256,m.source_sha256);
  assert.equal(validation.model_sha256,m.model_sha256);
  assert.equal(build.passed,true);assert.equal(validation.passed,true);
  assert.ok(Object.values(build.checks).every(Boolean));
  assert.ok(Object.values(validation.checks).every(Boolean));
  assert.ok(build.face.head_front_retraction>.1);
  assert.ok(build.face.mouth_half_width<.40);
  assert.equal(build.dorsal.plates.length,21);
  assert.ok(build.dorsal.plates.every(p=>p.max_rim_distance<.007));
  assert.ok(build.dorsal.baseline_max_nearest_plate_gap>.10);
  assert.equal(validation.native_groom.native_strands,3582);
  assert.equal(m.head_hair_removed,true);
  assert.equal(m.animations_unchanged,true);
  assert.deepEqual(Object.keys(validation.components).sort(),["armor","body"]);
  for(const [path,digest] of Object.entries(m.builder_sha256))assert.equal(sha(await file(path)),digest,path);
});

test("the previous head-hair-free authoring anchor remains recoverable through documented publication copies", async () => {
  const source = "assets/3d/source/asterion/sculpt-v003/asterion-sculpt-v003.blend";
  assert.equal(sha(await file(source)), publishedHash(root, source, "044E0C219693A8D9BB9004F26CD50F5082A3E02D6CD59C8D48D7EC2813013228"));
  assert.equal(sha(await file("public/assets/3d/asterion/asterion-sculpt-v003.glb")),"A2923D851CA53F8983EA5BCCD71C160D6381244C058B0429ACF797FD524A3DE1");
});
