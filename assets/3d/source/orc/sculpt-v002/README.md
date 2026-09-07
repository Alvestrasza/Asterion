# Brumo — reference-led sculpt v002

The unchanged `public/assets/companions/orc.png` portrait governs Brumo's
identity: olive skin, amber eyes, swept plum hair and topknot, short upward tusks,
plum armor, warm leather, gold fittings and cream fur trim. It is a single view,
not a multi-view construction drawing. The neutral stance, rear hair, garment
backs and hidden anatomy are inferred. The historical v001 sources and assets
are preserved.

## Modeled changes

- A rebuilt broad face with joined cheeks, nose and jaw; recessed amber ocular
  surfaces, cupped pointed ears, shaped brows, a seated smile and upward tusks.
- Tapered, scored swept locks over the forehead, temples and nape; a closed
  crown under-volume, overlapping gathered crown locks and a bound topknot.
- Curved shoulder plates with broad forged gold borders, fitted cross straps,
  seated shallow chest and belt settings, and curved hip armor panels.
- Separate scored wrist and boot fur locks; shallow modeled leather/cloth
  variation and exportable authored vertex colors on skin, hair and clothing.

These are editable volumetric meshes, not projected portrait billboards or
relief copies. Polygon count is not an identity acceptance criterion. Remaining
artistic differences include regularized hair/fur groups, a more circular
wide-open eye expression, simplified ornamentation and the neutral pose.

## Reproduction and deliverables

`model.py` is the pet-specific builder. Its local `sculpt_helpers.py` contains
the eye, ear, scored-lock, fitting and surface-color construction. Historical
companion geometry and rig utilities remain required read-only dependencies.
Use the [shared v002 reproduction pipeline](../../companions/sculpt-v002/README.md)
with `--kind orc` and fresh absolute output directories.

The Blender master preserves named, separately editable objects. The GLB is a
separate browser-delivery export containing a skinned mesh and nine presentation
clips: idle, blink, happy, eat, play, pet_reaction, sleep, wake and walk. Generated
manifests and review reports, rather than this source README, record actual
counts, hashes, import results and sampled motion observations.

Exact 1:1 likeness, human approval, collision-free motion, representative mobile
performance and production acceptance are not asserted. The website's 2D
default and fallback remain separate from this high-poly review asset. This is
local procedural Blender work; no paid provider, deployment, publication or Git
operation is part of this source package.
