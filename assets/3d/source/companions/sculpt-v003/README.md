# Modular companion refinement v003

This local Blender pass brings Caelo, Liora, Nyra, Fenn, Brumo, Selya and Aelira
onto the same **body / removable outer outfit** contract as Asterion v004.
Asterion itself is not changed. Original v001/v002 masters, GLBs, builders and
approved portraits remain immutable comparison checkpoints.

## Geometry and equipment

- Caelo: fuller scored blue locks, shaded roots and a less projecting lower muzzle.
- Liora: shortened, plumper cheek fans and directional cream-fur relief.
- Nyra: shorter silver cheek blades and less projecting lower muzzle/nose.
- Fenn: plush ear/bib relief and a shorter smile seated on the actual muzzle.
- Brumo: scored plum hair and a separate forged/leather outfit over an opaque
  under-tunic and shorts. The plain collar rim belongs to the base clothing.
- Selya: scored copper locks and coherent curled coral outer petals. Mint/ivory
  base dress, sandals and biological wings remain on the body.
- Aelira: green lock/braid relief and relaxed cape folds with attached edging.
  Tunic, trousers and closed boots remain on the body.

The original eyelid geometry, ocular colors/weights, rig, source actions, keys,
handles, constraints and drivers are preserved. Existing topology receives
shape and color-field edits, not uniform subdivision. Brumo additionally needs
base clothing beneath his removable cuirass. No physics or new animations are
introduced. This is an incremental refinement, not a claim of 1:1 likeness.

The source keeps individual meshes in named body/armor collections. Delivery
joins only temporary copies into two skinned meshes on the same original rig.
The stable metadata is:

| Node | Metadata |
| --- | --- |
| Body | `asterion_component=body`, `asterion_rig=<kind>-rig-v1` |
| Outer outfit | `asterion_component=armor`, same rig, `asterion_equipment_slot=outfit`, `asterion_equipment_id=<kind>-outfit-v1` |

The project-wide `asterion_` namespace is intentional. Runtime consumers use
these extras, never names or colors. An outfit ID is not cross-species rig
compatibility. Individual garment slots, reward inventories, replacement
outfits and persistence are not implemented by this pass.

## Reproduce locally

Use the installed Blender 5.2 LTS executable and a fresh private destination:

```powershell
& $blender --background --factory-startup --python-exit-code 1 `
  --python assets/3d/source/companions/sculpt-v003/build.py -- `
  --kind pony --output .private/3d-work/companions/pony-fresh-review `
  --resolution 1200 --samples 40
```

The builder refuses an existing output directory. It hashes the original blend,
GLB, portrait and every builder dependency; edits an in-memory copy; exports;
renders six source views; saves and reopens the master; and independently imports
both old and new GLBs. Four imported views include the hidden outfit and blink.
It writes `validation.json` and fails if any acceptance gate fails.

Review the actual images against the unchanged portrait before delivery:

```powershell
python assets/3d/source/companions/sculpt-v003/deliver.py `
  --kind pony --input .private/3d-work/companions/pony-fresh-review
```

Delivery rechecks all hashes and image receipts before staging any write. It
uses the historical rollback helper, refuses different existing v003 content,
and never targets v001/v002 or Asterion. Review images, manifests and compact
validation evidence are public-safe; full RNA snapshots stay in the private
review. The game-dev CLI was unavailable on this workstation. These are local
hash-checked Blender deliveries, **not canonical game-dev package receipts**.

For a correction before handoff, `--previous <exact-private-review>` permits
replacement only when every existing destination matches either that exact
previous artifact or the new artifact. Historical builder hashes are not fresh
acceptance evidence; the new review must pass all current input-hash gates.
Earlier private reviews remain available for recovery. `gallery.py` assembles
hash-verified imported outfit/body views without changing the input images.

## Acceptance boundaries

- Technical authoring budget: fewer than 2 million triangles, 25 MB and 40
  material primitives per GLB; no projected textures or external resources.
- Source animation data compared exactly. Imported deformation compared at
  nine normalized times for each of nine clips, tolerance `2e-4` per world
  skin-matrix component. This is not an exhaustive collision/gait check.
- Meshopt uses the existing Blender encoder, including precision-reducing
  filters. No lossless compression claim is made.
- Fresh import checks finite geometry, known normalized weights (at most four),
  two independent components, shared rig, all clips and bounded importer face
  count differences.
- Runtime tests decode the actual delivered GLBs with Three.js/Meshopt and
  toggle outfits while the existing skeleton and animation continue.
- `/3d-preview` keeps visibility independently for each pet, for the current
  page session only. The 2D default and reduced-motion/error fallback remain.
- Hidden reference views are inferred. Final human likeness acceptance,
  representative mobile performance and production deployment remain pending.
