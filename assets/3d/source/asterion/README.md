# Asterion 3D sources

## Identity authority

The current reconstruction authority is the user-approved four-view attachment, preserved as `assets/3d/reference/asterion/sculpt-v001/asterion-approved-turnaround.png`. It supplies front, side, rear, and three-quarter views. Preserve its compact wingless quadruped anatomy, expressive blue eyes, swept gold horns, navy dragon ears, cream mane and tail tuft, layered blue scales, gold-edged armor, cyan chest crystal, and gold claws.

`public/assets/companions/asterion.png` remains the existing 2D fallback. Its earlier 192×208 relief reconstruction was rejected by the user and is not the authority for `sculpt-v001`. The sculpt is a modeled interpretation of the four-view sheet; no exact 1:1 likeness is claimed.

## Versioned sources

- `sculpt-v004/asterion-sculpt-v004.blend` is the current fitted-scale, rounded-muzzle and modular-armor revision. Its [source guide](sculpt-v004/README.md) documents 55 individually editable armor pieces in a separate collection, exported as one outfit mesh beside the body. The shared rig, nine actions and tail hair remain unchanged; head hair stays omitted. The delivery has 3,049,212 triangles.
- `sculpt-v003/asterion-sculpt-v003.blend` is the preserved temporary head-hair-free study requested by the user. Its [source guide](sculpt-v003/README.md) documents the removal of mane and cheek hair only; tail hair, retained geometry and animations remain unchanged. The resulting delivery has 3,051,226 triangles.
- `sculpt-v002/asterion-sculpt-v002.blend` is the preserved refined volumetric master with the complete editable native Blender groom and approximately five-million-triangle browser export. Its [source guide](sculpt-v002/README.md) covers reproduction, validation and the unchanged animation boundary.
- `sculpt-v001/asterion-sculpt-v001.blend` is the preserved baseline master. Anatomy, horns, mane, ears, eyes, scales, armor, and ornaments remain separate editable source objects.
- `sculpt-v001/build_sculpt.py` constructs the anatomy, face, horns, mane, scales, materials, and review scene.
- `sculpt-v001/armor.py` and `sculpt-v001/ears.py` construct curved ceremonial armor and solid concave dragon ears.
- `sculpt-v001/rig_delivery.py` prepares the armature, weights, stable clips, and browser export.
- `sculpt-v001/validate_sculpt.py` inspects the exported delivery independently.
- `sculpt-v001/render_motion.py` produces motion-review evidence.

The runtime path is `public/assets/3d/asterion/asterion-sculpt-v004.glb`. It contains separate body and armor meshes sharing one skin; the source remains fully volumetric and individually editable. The preview can hide the whole armor outfit without hiding natural horns, ear inlays or claws. Replacement-outfit loading, individual equipment slots and reward ownership are not implemented. Native tail hair is retained in Blender and exported as matching static strands, not as native glTF hair. Never edit the GLB directly. Make changes in versioned sources and re-export.

## Animation contract

The stable clips are `idle`, `blink`, `happy`, `eat`, `play`, `pet_reaction`, `sleep`, `wake`, and `walk`. Loop policy is defined in `app/asterion-model.tsx`.

## Validation boundary

Use the final generated reports for exported counts, hashes, rig checks, and import results. Do not transfer a previous version's metrics to this asset. Review front, side, rear, three-quarter, and motion evidence against the supplied sheet. A completed source render or valid GLB does not prove human identity acceptance or mobile performance.

Representative mobile-performance acceptance is outstanding. The feature flag remains off by default; approved 2D assets remain the loading, error, unsupported-WebGL, and reduced-motion fallback.

## Historical checkpoints

`asterion-canonical-highpoly-v001.blend`, `build_asterion_canonical_v001.py`, and their validation artifacts document the user-rejected portrait relief approach. Its exact single-view alpha-mask metric does not prove a faithful volumetric creature. Retain these files as historical evidence, not as current design authority.

`asterion-highpoly-v005.blend`, `asterion-web-highpoly-v001.blend`, and the earlier `asterion.blend` are also superseded comparison checkpoints. The generated `asterion-turnaround-guidance-v001.png` is earlier exploratory guidance, not the approved four-view attachment for the current sculpt.
