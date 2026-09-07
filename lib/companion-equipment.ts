import type { Material, Object3D } from "three";

export type CompanionArmorState = {
  outfits: number;
  visibleOutfits: number;
  meshes: number;
  visibleMeshes: number;
};

function armorRoots(root: Object3D): Object3D[] {
  const outfits: Object3D[] = [];
  const visit = (node: Object3D) => {
    const data = node.userData;
    if (data.asterion_component === "armor" && data.asterion_equipment_slot === "outfit" &&
      typeof data.asterion_equipment_id === "string" && data.asterion_equipment_id.trim().length > 0) {
      outfits.push(node);
      // A glTF node may contain several material primitives. It is one outfit,
      // even if the loader also copies its extras onto a primitive descendant.
      return;
    }
    node.children.forEach(visit);
  };
  visit(root);
  return outfits;
}

function isEffectivelyVisible(node: Object3D): boolean {
  for (let ancestor: Object3D | null = node; ancestor; ancestor = ancestor.parent) {
    if (!ancestor.visible) return false;
  }
  return true;
}

/** Report loaded scene-graph visibility, never the requested React prop. */
export function inspectCompanionArmor(root: Object3D): CompanionArmorState {
  const outfits = armorRoots(root);
  const state = { outfits: outfits.length, visibleOutfits: 0, meshes: 0, visibleMeshes: 0 };
  for (const outfit of outfits) {
    if (isEffectivelyVisible(outfit)) state.visibleOutfits++;
    outfit.traverse((node) => {
      const mesh = node as Object3D & { isMesh?: boolean; material?: Material | Material[] };
      if (!mesh.isMesh) return;
      state.meshes++;
      const materials = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : [];
      if (isEffectivelyVisible(mesh) && materials.some((material) => material.visible)) state.visibleMeshes++;
    });
  }
  return state;
}

/** Toggle complete equipment roots without editing meshes, bindings or clips. */
export function setCompanionArmorVisible(root: Object3D, visible: boolean): CompanionArmorState {
  for (const outfit of armorRoots(root)) outfit.visible = visible;
  return inspectCompanionArmor(root);
}
