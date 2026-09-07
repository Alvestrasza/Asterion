# Reference-likeness round

This round authors substantial primary-form changes on the preceding immutable
Blender masters: `sculpt-v003` for the seven companions and `sculpt-v004` for
Asterion. Delivery versions are respectively `sculpt-v004` and `sculpt-v005`.
Original approved portraits remain authoritative; Asterion uses the supplied
four-view turnaround. No replacement illustration, image projection, provider
generation or automatic subdivision inflation is used.

## Changes and boundaries

- Caelo: diagonal rolled forelock, shaped neck locks, fuller curved tail and
  coordinated eye/socket/lid shaping.
- Liora: swept guarded ears, fuller haunch, overlapping cheek fur, cotton-tail
  plume and lavender-blue eyes.
- Nyra: swept silver crest, triangular ears, feline eye surround and S-tail.
- Fenn: continuous ear volumes, complete cream bib, fuller curled tail and
  physical clearance between fur and the complete detachable pendant family.
- Brumo: compact broader proportions, a rising staggered plum quiff and closed
  shoulder/wrist/ankle transitions beneath the removable outfit.
- Selya: curled copper hair, golden forelock, fitted botanical waist and
  pearl/mint wing pigment.
- Aelira: arched parting, temple ringlets, softened braid, broad cape folds and
  closed tunic armholes, wrists and base trouser seat beneath the outer costume.
- Asterion: swept-back crown, shorter ears, fuller cheeks/nose and upper chest,
  shallow coherent navy scales, fitted rear collar and fuller golden claws.
  The earlier temporary head-mane omission is retained. Native tail curves and
  portable strands receive matching centerline edits with circular radii intact.

These are editable volumetric sculptures, not exact reproductions of painted
pixels. Precise facial character, painterly highlights, fur transitions and
some proportions remain different. Hidden views are inferred. The manifests
explicitly keep `human_likeness_accepted` and `mobile_performance_accepted` false.

Every figure keeps two independently visible components on its original shared
skeleton. Natural markings, wings and complete opaque base clothing remain on
the body. Original nine actions, keys, handles, rest bones, constraints and
drivers are not reauthored. This does not establish collision-free motion or
provide interchangeable reward items, inventory logic or persistent equipment.
The added body-joint shells are independently closed and use normalized weights
on the existing bones; they are fitted overlapping surfaces, not a watertight
union of every body part or a 3D-printing mesh.

## Reproduce locally

Use the repository's configured Blender executable and a fresh private review
directory. The builder refuses an existing review destination.

```text
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/companions/sculpt-v004/build.py -- --kind pony --output .private/3d-work/companions/sculpt-v004/pony-new-review --resolution 1200 --samples 40
python assets/3d/source/companions/sculpt-v004/deliver.py --kind pony --input .private/3d-work/companions/sculpt-v004/pony-new-review
python assets/3d/source/companions/sculpt-v004/test_delivery.py --review .private/3d-work/companions/sculpt-v004/pony-new-review
python assets/3d/source/companions/sculpt-v004/gallery.py
python assets/3d/source/companions/sculpt-v004/test_gallery.py
```

The same builder accepts all eight kind identifiers. Species modules own their
shape edits; the common coordinator owns export, evidence and delivery. Helpers
and preceding master/model/reference bytes are bound by SHA-256. A changed
helper requires a fresh build; old evidence cannot certify newly edited code.

Delivery is staged, conflict-checked and rollback-capable. It does not overwrite
historical revisions. `--previous` can replace an already staged *new* revision
only when the supplied earlier private report reconstructs every existing byte.
It is an overwrite baseline, not fresh acceptance evidence. Unknown kinds and
substituted reference authorities fail before writing.
Review layouts also use staged replacement. `gallery.py --replace-verified`
refreshes only the ten layout/receipt files whose existing bytes match the
preceding receipt; it cannot target portraits, models or source files.

## Evidence

Each master is saved and reopened. The original action/rest/driver fingerprints
must match exactly. Intentional ocular geometry changes must survive reopening.
Historical and candidate GLBs are separately imported and compared at nine
normalized times for each of nine clips, with a `2e-4` skin-matrix tolerance.
Imported positions/transforms must be finite and skin weights valid. The small
documented importer triangle-count tolerance is checked, not assumed.

Each figure has six source renders and four fresh-import renders, including
rear, body-only and blink views. The reference comparison layouts bind all
source images by hash; image scaling and Asterion's hero-view crop are disclosed
in the gallery receipt and never used as model textures.

High-poly desktop authoring limits are fewer than 2 million triangles and
25 MB for each other companion, and fewer than 8 million triangles and 80 MB
for Asterion. Every GLB has fewer than 40 material primitives, two skinned mesh
nodes, one shared skin and the original nine clips. Meshopt uses the existing
precision-reducing filters and is not described as lossless.

The local `game-dev` CLI/provider path was unavailable. This is an authorized
local Blender workflow with direct evidence, not a canonical game-dev package.
No provider account, credit, license purchase or network generation was used.

The default 2D presentation/feature flag remains unchanged. Full release/mobile,
authentication, database, multi-node and Linux production acceptance are separate.

See the [collection review](../../../reference/companions/sculpt-v004/REVIEW.md)
and [figure index](../../../COMPANION-FIGURES.md) for the delivered evidence.
