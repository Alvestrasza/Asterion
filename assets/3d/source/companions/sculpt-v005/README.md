# Face-only refinement round

This local authoring round creates Asterion `sculpt-v006` and the other seven
companions `sculpt-v005` from the unchanged immediately preceding Blender
masters. Approved 2D references remain unchanged. This is an interpreted
sculpture study, not a 100-percent likeness or mobile-production acceptance.

## Scope

Only facial skin, cheeks/muzzle, nose/nostrils, mouth, eyes, lids, lashes and
facial markings change. Hair, ears, crown, body, tail, clothing, armor, original
rig, drivers, constraints and nine actions remain protected. The existing
head-mane omission and native static tail groom for Asterion are preserved.
All accessories still belong to the separate outfit component.

Species modules:

- [Asterion](../../asterion/sculpt-v006/face.py): broader azure eyes, rounded
  nasal volume, softer cheek/chin fields and surface-fitted lip arcs. An
  asymmetric skin-seated orbital transition accounts for the receding temple;
  lower rim sweep ends are closed.
- [Caelo and Liora](equine_lapine_faces.py): rebuilt recessed arched eyes,
  blue/lavender irises, tapered lashes and refined muzzle/nose/pad anatomy.
- [Nyra and Fenn](feline_canine_faces.py): integrated eye surrounds, richer
  green/blue pupils, softer feline/canine muzzle and attached lash tips.
- [Brumo, Selya and Aelira](folk_faces.py): seated facial relief, shaped ocular
  transitions and species-specific amber, mint and violet irises.

## Reproduction

Use local Blender 5.2 LTS, its bundled Python/numpy and the existing glTF
exporter. The lightweight delivery gates use Python's standard library;
review layout additionally uses Pillow. No paid provider is used. The local
game-dev CLI was unavailable on this workstation, so these are hash-checked
local Blender deliveries, not canonical game-dev receipt packages.

Run from the repository root, with the Blender executable available on PATH:

```powershell
blender -b --python assets/3d/source/companions/sculpt-v005/build.py -- --kind pony --output .private/3d-work/companions/sculpt-v005/pony-new-review
python -B assets/3d/source/companions/sculpt-v005/deliver.py --kind pony --input .private/3d-work/companions/sculpt-v005/pony-new-review
python -B assets/3d/source/companions/sculpt-v005/test_guards.py
python -B assets/3d/source/companions/sculpt-v005/test_delivery.py --kind pony --review .private/3d-work/companions/sculpt-v005/pony-new-review
python -B assets/3d/source/companions/sculpt-v005/gallery.py
python -B assets/3d/source/companions/sculpt-v005/test_gallery.py
pnpm test
pnpm check
pnpm build
```

Choose a fresh private directory for each attempt. An existing different final
asset is rejected. Only a matching previous private report supplied through
`--previous` may replace exact preceding new-version bytes. Historical inputs
are never output targets. Gallery `--replace-verified` is limited to the ten
exact layout files bound by its preceding receipt, not models or source art.

## Evidence and limits

`contract.py` fixes all required input paths, revisions and evidence sets.
`guards.py` independently compares actual before/after/reopened source geometry,
material node graphs, weights, attachments and original lid pivots. An explicit
facial allowlist cannot admit ears, mane, crown, outfit or arbitrary body parts.
Unchanged shared material graphs prevent a facial recolor from affecting the
body. Geometry refinement must include measured shape changes, not merely new
shader names or extra subdivisions.

Each source has front/hero/side facial views, three blink views, whole-body
hero/rear and outfit-off hero. The historical and new GLBs are freshly imported
and rendered in the same studio. All nine clips are compared at nine skin-matrix
samples each. Nine additional source blink frames are evaluated for finite
geometry. Every output and fixed input is hash-bound before staged delivery.
Node tests independently decode both GLBs, compare sampled skin matrices and
exercise the live outfit toggle.

The inherited blink uniformly grows a curved eye cover from its original
center. It is not an anatomical upper-lid rig. Its curves and pivots are
deliberately unchanged; finite partial-frame geometry does not prove perfect
coverage or collision-free animation. High-poly GLBs use the existing lossy
Meshopt export and can show small shading/edge differences from source renders.
These remain desktop art-review assets; the 2D fallback stays default.

See the [face comparisons and review](../../../reference/companions/sculpt-v005/REVIEW.md)
for visible changes and remaining differences. Earlier revisions are preserved.
