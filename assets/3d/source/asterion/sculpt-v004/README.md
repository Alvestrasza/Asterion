# Asterion v004: rounded face, fitted dorsal scales, detachable armor

This pass starts from an unchanged v003 master. Head hair remains omitted; the
native and portable tail groom and all original animation data are preserved.
It addresses the user's pointed muzzle, floating nape/back scales, and the
request for separately replaceable armor. It does not implement an inventory,
quest rewards, persistence, or new animations.

## Geometry and equipment boundary

The lower muzzle is compressed monotonically and broadened, with localized
surface smoothing, a rounded triangular nose and a shorter surface-fitted lip
line. Eye geometry stays unchanged. Twenty-one shallow, overlapping, closed
shield scales replace the free-standing nape/back spikes. Their rims follow
the actual skin surface; skin attachment weights come from the underlying
anatomical meshes.

The source keeps 55 editable armor pieces in the collection
`AST_Equipment_Ceremonial_Gold_v1`. These include chest and shoulder plates,
bracelets, decorative hip/tail fittings and the small forehead diadem. Horns,
dragon ears, their natural gold inlays, claws, throat plates and anatomical
scales remain part of the body. The complete underlying body is retained.

The GLB contains two separate skinned mesh nodes, `asterion_body` and
`asterion_armor`, using the same 22-bone skeleton and nine clips. The armor is
one replaceable **outfit**, not yet separate independently selectable slots.
Its stable glTF extras are:

```json
{
  "asterion_component": "armor",
  "asterion_equipment_slot": "outfit",
  "asterion_equipment_id": "ceremonial-gold-v1",
  "asterion_rig": "asterion-rig-v1"
}
```

Future outfits need compatible bone names, rest transforms, bind matrices,
coordinate space and skin weights. Matching only the ID is not sufficient.
No separately loaded replacement outfit or reward entitlement is implemented
yet. The preview toggles the loaded equipment root through these metadata;
material color is never used to guess what belongs to armor. Normal Tamagotchi
presentation stays equipped by default, with the existing 2D default/fallback.

## Reproduce and validate

Run from the repository root with local Blender and Python available. Choose
fresh private directories; existing destinations are never overwritten.

```powershell
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/asterion/sculpt-v004/build_v004.py -- --output .private/3d-work/asterion/sculpt-v004/candidate02 --resolution 1600 --samples 64
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/asterion/sculpt-v004/validate_v004.py -- --source .private/3d-work/asterion/sculpt-v004/candidate02/asterion-sculpt-v004.blend --model .private/3d-work/asterion/sculpt-v004/candidate02/asterion-sculpt-v004.glb --output .private/3d-work/asterion/sculpt-v004/validation02
```

Review the source and fresh-import images, both with and without armor, plus
all numerical checks before staging the handoff:

```powershell
python assets/3d/source/asterion/sculpt-v004/deliver_v004.py --candidate .private/3d-work/asterion/sculpt-v004/candidate02 --validation .private/3d-work/asterion/sculpt-v004/validation02
```

The staging helper verifies hashes, rejects conflicting existing artifacts and
rolls back partial writes. Use a new version for later model changes. All
historical source/export files stay unchanged. The separate Game-Dev CLI is
not required by this local Blender implementation.

## Compression and acceptance limits

Blender's existing Meshopt encoder uses precision-reducing EXPONENTIAL and
QUATERNION filters. This pass preserves that behavior for compatibility; it
does **not** claim lossless delivery. Complete source action data is compared
exactly and the imported animation is separately sampled against v003.

See `manifest.json`, `build-report.json` and the
[review](../../../reference/asterion/sculpt-v004/REVIEW.md) for measured evidence.
Contact checks measure stored rest geometry, not collision-free animation.
Human identity acceptance and representative mobile performance remain open.
