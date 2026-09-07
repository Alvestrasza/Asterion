# Remaining companion refinements — v002

This source package coordinates the second reference-led pass for Nyra (cat),
Brumo (orc), Selya (fairy), Fenn (dog) and Aelira (elf). Caelo and Liora retain
their previously delivered v002 builders and files. Asterion is unchanged.

## Design and acceptance contract

The unchanged portraits in `public/assets/companions/<kind>.png` govern identity.
The requested outcome is the same high-detail review standard as Caelo and
Liora, with meaningful shape and surface changes, not a polygon-count-only pass.
Unseen surfaces remain interpretations of single-view art. No exact 1:1 likeness,
human approval, new distribution license or mobile performance is asserted.

| Figure | Distinctive reference requirements |
| --- | --- |
| Nyra | Charcoal/silver coat, swept crest and curled plume, emerald eyes, copper and deep teal armor, rounded paws |
| Brumo | Olive skin, amber eyes, swept plum hair/topknot, small upward tusks, fitted plum armor, leather and fur trims |
| Selya | Warm amber skin, teal eyes, coral/gold flowing hair, four pearl-mint veined wings, layered petal dress and leaf jewelry |
| Fenn | Golden puppy coat with cream bib, brown-tipped hanging ears, blue eyes, curled tail, navy collar and round moon/star tag |
| Aelira | Warm face and violet eyes, deep green hair and braid, tailored ivory tunic, forest mantle, leaf embroidery and leather boots |

All geometry is volumetric. Editable source meshes retain meaningful names and
deformation parts. Only export copies are merged to one skinned mesh. The common
nine presentation clips and their names remain stable. Dimensions are consistent
stylized Blender scene units; no real-world manufacturing scale is specified.
Roughly one million useful triangles per figure is an authoring target, not a
substitute for visible detail. Final counts and transfer sizes belong in each
generated manifest. Self-contained Meshopt GLB, fewer than 40 material primitives,
normalized weights and at most four influences preserve the delivery contract.
The bounded authoring ceiling is 1.5 million triangles per new figure, with a
1.6 million exception for Aelira's folded mantle and modeled leaf embroidery.
Transfer size remains below 20 MB per figure. These are high-poly review budgets,
not the ordinary mobile targets or evidence of acceptable frame rate.

## Reproduction

Blender 5.2.1 LTS and its bundled Python, Cycles, glTF and Meshopt support are
sufficient. The `game-dev` CLI is unavailable on this workstation. These are
local, hash-checked assets, not canonical plugin packages or provider receipts.
No paid generation, external account or new dependency is needed.

Run from the repository root, with Blender on PATH. Replace placeholders with
absolute paths to **fresh** local output directories. The build refuses existing
masters/GLBs, and delivery refuses replacing different existing artifacts.

```powershell
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/companions/sculpt-v002/build.py -- --kind cat --output <absolute-review-root>/cat --views hero,front,side,rear --resolution 1600 --samples 64
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/companions/sculpt-v002/validate_collection.py -- --glb <absolute-review-root>/cat/cat-sculpt-v002.glb --output <absolute-review-root>/cat/validation --resolution 1200
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/companions/sculpt-v002/inspect_motion.py -- --glb <absolute-review-root>/cat/cat-sculpt-v002.glb --output <absolute-review-root>/cat/motion --resolution 800 --samples 32
python assets/3d/source/companions/sculpt-v002/deliver.py --kind cat --input <absolute-review-root>/cat
```

Repeat for `orc`, `fairy`, `dog` and `elf`. Their exclusive `model.py` builders
reside in each pet's `assets/3d/source/<kind>/sculpt-v002/` directory. Keep the
historical shared geometry/rig utilities alongside these sources when moving
the package. Per-asset manifests record the exact dependent builder hashes.

Before delivery, inspect all four source views, the independent imported hero,
rear and closed-blink views, and the six rendered full-mesh motion samples.
Numeric import checks and vertex-level loop equality supplement, not replace,
visual inspection. The latter does not prove collision-free motion, biomechanical
gait, every possible transition, representative mobile FPS or final identity.

The optional `render_gallery.py` imports the five actual final GLBs from the
public asset tree into one Blender scene. It does not use portrait billboards.
The website keeps 2D as its default and as reduced-motion/loading/error fallback.
No authentication, database, deployment, publication or Git operation is part
of this asset handoff.

Delivery preflights every source, hash and destination (including generated
metadata), stages exact content and rolls back ordinary commit failures.
This is not a crash-atomic filesystem transaction. Its focused regression checks
run without Blender: `python assets/3d/source/companions/sculpt-v002/test_delivery.py`.
The fresh-import report binds both the reopened master and GLB hashes; only known
armature display helpers are excluded, so real unweighted meshes cannot be hidden
from geometry checks or review renders.
