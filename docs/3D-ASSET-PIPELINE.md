# Asterion 3D asset pipeline

## Goal

Create expressive, rigged 3D companions for the web application without losing their approved storybook identity. Use the explicitly approved reference for each reconstruction. For Asterion's current `sculpt-v006` facial revision, the authority remains the unchanged user-provided four-view turnaround at `assets/3d/reference/asterion/sculpt-v004/asterion-approved-turnaround.png`; temporarily omitting head hair is the user's explicit exception. Blender sources are editable geometry authorities, and separately prepared glTF Binary files are delivery artifacts.

Asterion's current work is a fully volumetric high-poly sculpt. It does not use the old portrait as a projected relief surface. The existing 2D implementation remains the default and production fallback; representative mobile-performance acceptance is still outstanding.

## Asset layout

Keep approved references, editable sources, and delivery artifacts separate:

```text
assets/3d/reference/<companion>/   approved turnarounds and color references
assets/3d/source/<companion>/      Blender source and linked source textures
public/assets/3d/<companion>/      optimized browser-ready GLB and textures
```

Large `.blend`, `.glb`, and `.fbx` files should use Git LFS. Do not commit Blender autosaves, render caches, simulation caches, or redundant exports.

## Publication privacy and provenance

Blender UI state, render PNG metadata, scene extras and historical JSON reports
can contain private authoring paths. Audit them before any upload. Prepare
separate, explicitly authorized publication copies and retain the original
bytes privately. Require unchanged asset semantics, unchanged decoded image
pixels, and a fresh independent metadata audit before replacing distribution
files. A successful render or test suite alone does not clear this gate.

The [2026-09-07 publication amendment](../assets/3d/publication/2026-09-07/README.md)
distinguishes current distribution bindings from original authoring evidence.
Do not describe amended file hashes as a rerun of the historical builders or
validators. Preserve exact public-safe original receipts; retain unsafe ones
privately and disclose their omission with their original hashes. Geometry,
animation and likeness measurements must never be changed to fit new file bytes.
See [publication tooling](../scripts/asset-publication/README.md).

## Production stages

### 1. Identity reference

Build an approved character sheet containing front, side, rear, and three-quarter views. Record the non-negotiable silhouette, proportions, palette, face, horns or ears, clothing or armor, and characteristic markings.

Generated reference art is exploratory until visually approved. Do not silently replace the canonical companion design.

### 2. Blockout

Model primary volumes at neutral pose and real scene scale. Validate the silhouette from the intended web-camera distance before adding surface detail.

For Asterion, validate these features first:

- compact quadruped proportions
- large expressive head and blue eyes
- layered gold horns and crest
- dark blue body with gold armor language
- pale mane and tail tuft
- readable paws and silhouette at small display sizes

### 3. Retopology and UVs

Use animation-friendly edge flow around shoulders, hips, mouth, eyelids, tail, and horn bases. Prefer a compact mobile-ready mesh over sculpt-level density.

Initial performance targets for ordinary companions:

- 10,000 to 30,000 rendered triangles per companion
- one primary 1K or 2K texture set
- as few materials and draw calls as the design permits
- no hidden geometry that cannot affect the final presentation

These are starting budgets, not excuses to damage the silhouette. At the user's explicit direction, Asterion's volumetric sculpt deliberately exceeds the ordinary web budget. Record final triangle, vertex, material, mesh, and transfer-size counts in the generated validation report after export. Merging source parts into one delivery mesh and applying Meshopt compression reduce delivery overhead; neither operation proves mobile performance. The sculpt remains an opt-in high-end presentation until it is measured on representative mobile hardware.

### 4. Materials and textures

Use a stylized physically based material with painted color variation. Bake reusable detail instead of shipping heavy procedural node graphs. Keep transparent materials exceptional because they increase sorting and overdraw costs in browsers.

### 5. Rigging

Use one deforming armature per companion, clean normalized weights, and stable bone names. Apply transforms before export and keep non-deforming control bones out of the exported deformation set when possible.

Minimum animation clips:

- `idle`
- `blink`
- `happy`
- `eat`
- `play`
- `pet_reaction`
- `sleep`
- `wake`
- `walk`

Loops must be seamless where appropriate. The first and last frame should not produce a visible pause or root jump.

### 6. GLB export

Export one self-contained `.glb` per companion prototype with:

- only required meshes, armature, materials, and animation clips
- applied coordinate and scale conventions
- embedded or deliberately colocated optimized textures
- no cameras, lights, helpers, or editor-only collections
- deterministic, lowercase asset names

Record the Blender version and export settings in the asset's review note. Re-export from the `.blend` source rather than editing generated GLB files manually.

### 7. Web integration

Load 3D only in the client and only when needed. Preserve:

- the current 2D fallback
- useful alternative text and non-visual status feedback
- `prefers-reduced-motion` behavior
- lazy loading and a visible loading state
- cleanup of WebGL resources when changing companions
- graceful fallback when WebGL or the asset fails

The server-authoritative care model does not need to change. Existing mood and action results should select animation clips without moving companion state into the browser.

## Acceptance checks

### Visual identity

- The companion is immediately recognizable beside the approved 2D reference.
- Silhouette, palette, eyes, face, and signature features remain consistent.
- No chroma fringe, texture seams, inverted normals, or unintended transparency is visible.

### Animation

- All required clips exist under stable names.
- Limbs, face, mane, tail, armor, and clothing deform without obvious collapse.
- Loops do not jump and one-shot actions return cleanly to idle.
- Reduced-motion mode can present a still or substantially calmer alternative.

### Technical

- The asset loads as GLB without console errors.
- Materials and animation clips survive a clean export and fresh browser load.
- File size, triangle count, texture memory, draw calls, and load time are recorded.
- Desktop and representative mobile browsers retain an acceptable frame rate.
- A missing or corrupt model falls back to the 2D companion.

### Repository and release

- Source and export are traceable to one reviewed commit.
- Binary assets use the agreed LFS policy.
- Tests, type checks, and production build still pass.
- Deployment uses the same immutable application artifact on both web nodes.

## Current face-only round

The preview selects Asterion `sculpt-v006` and the seven other pets'
`sculpt-v005` files. This round changes only faces: ocular shape and pigment,
skin/lid transitions, cheeks, nose and mouth. The previous body, ears, hair,
crown, outfit and nonfacial material graphs are protected by exact source
signatures, checked again after reopening the saved Blender masters.

See the [face-round source contract](../assets/3d/source/companions/sculpt-v005/README.md)
and [original / previous / new facial comparisons](../assets/3d/reference/companions/sculpt-v005/REVIEW.md).
Each figure has six source and six freshly imported facial views, matching old
GLB closeups, whole-body views and an outfit-off check. Original rig/action/
driver fingerprints and nine sampled skin matrices per clip remain unchanged.
Nine additional source blink frames are evaluated for finite geometry.

Lid geometry is fitted around the unchanged original center-scale pivots;
anatomical blinking is not introduced. Finite poses do not establish perfect
all-angle closure or collision-free animation. The same desktop review budgets,
2D fallback and outstanding human/mobile acceptance boundaries apply.

## Preserved reference-likeness round

The preceding body-likeness round uses Asterion `sculpt-v005` and the other seven pets'
`sculpt-v004` files. The preceding editable masters, GLBs and approved images
remain immutable inputs. Species-specific primary-form, ocular, pigment,
hair/fur and costume edits are documented in the
[shared source guide](../assets/3d/source/companions/sculpt-v004/README.md) and
[collection comparison](../assets/3d/reference/companions/sculpt-v004/REVIEW.md).
This is not a claim of exact likeness: painted surfaces and inferred hidden
views still differ. No reference-image projection or replacement art is used.

Each new master is reopened, hashed and checked against its original full
action/rest/driver data. Historical and candidate GLBs are freshly imported;
all nine clips receive nine sampled skin-matrix comparisons. Two independent
body/outfit mesh nodes share the original skin. Natural markings, wings and
complete base clothing remain on the body. Original animations are not
reauthored. Head mane remains omitted for Asterion; native tail curves and
exported strand rings agree within the explicit `1e-5` geometric tolerance.

These are high-poly desktop review assets, not mobile production models.
Budgets are below 2 million triangles / 25 MB per other pet, below 8 million /
80 MB for Asterion, and below 40 material primitives each. Exact counts and
hashes are in per-figure manifests. Delivery validates a fixed evidence set,
actual GLB structure and unchanged input hashes before staging. The default
feature flag remains off; reward logic, authentication, Linux deployment and
mobile acceptance remain separate.

## Preserved Asterion sculpt-v004 fitted scales and modular armor

This preserved revision is `public/assets/3d/asterion/asterion-sculpt-v004.glb`.
Twenty-one shallow overlapping nape/back shields follow the actual anatomical
surface. The lower muzzle is shorter and wider, with a smaller fitted nose and
shorter mouth line. Head hair remains omitted; the tail groom is unchanged.

Body and armor are separate meshes in one GLB, with the same 22-bone skin and
nine original clips. The master retains 55 individual armor objects in a
dedicated collection. Explicit equipment metadata identifies one whole outfit;
the preview toggles its visibility without reloading the model or resetting
animation. No inventory, reward system or replacement-outfit loader is included.
The delivery contains 3,049,212 triangles and 40,099,324 bytes. Meshopt retains
the prior precision-reducing filter configuration; it is not claimed lossless.
See the [source guide](../assets/3d/source/asterion/sculpt-v004/README.md) and
[review](../assets/3d/reference/asterion/sculpt-v004/REVIEW.md) for measured surface
contact, source action equality, clean import and browser evidence. Earlier
versions and the other seven companions remain unchanged.

## Preserved Asterion sculpt-v003 head-hair-free study

The preserved study is `public/assets/3d/asterion/asterion-sculpt-v003.glb`.
Only four mane/cheek groups were removed from an in-memory copy of v002, both
native curves and matching mesh strands. Tail hair, all retained geometry,
materials and animations remain unchanged. The count falls to 3,051,226
triangles; the previous five-million-triangle requirement is not met by padding
geometry in this temporary study. The complete v002 master/export are preserved.
See the [source guide](../assets/3d/source/asterion/sculpt-v003/README.md) and
[review](../assets/3d/reference/asterion/sculpt-v003/REVIEW.md) for reproduction,
exact geometry/action comparisons, fresh imports and exposed neck-plate gaps.

## Preserved Asterion sculpt-v002 refinement

The preserved full-groom master and GLB live under `assets/3d/source/asterion/sculpt-v002/`
and `public/assets/3d/asterion/asterion-sculpt-v002.glb`. The user explicitly
requested approximately five million triangles and deferred animation changes.
The refinement updates facial planes, iris proportions, horn facets, anatomical
scales, armor detail and claws, and replaces the modeled ivory locks with native
Blender hair. Matching mesh strands provide the portable browser equivalent.
The original rest rig and full action data are strictly preserved; no hair
physics or new motion is introduced.

The [v002 source guide](../assets/3d/source/asterion/sculpt-v002/README.md),
[manifest](../assets/3d/source/asterion/sculpt-v002/manifest.json) and
[review](../assets/3d/reference/asterion/sculpt-v002/REVIEW.md) distinguish
source rendering, native/export correspondence, fresh GLB import, sampled
historical-motion regression and browser verification. A five-million-triangle
budget does not establish exact likeness or mobile performance. All earlier
Asterion files and all seven other pet deliveries are preserved.

## Historical Asterion sculpt-v001 handoff

The preserved baseline master is `assets/3d/source/asterion/sculpt-v001/asterion-sculpt-v001.blend`. It reconstructs the front, side, rear, and three-quarter appearance of the user-approved turnaround with actual volume. Anatomy, concave dragon ears, layered horns and mane, scales, curved armor, faceted chest crystal, paws, and tail remain separately editable in the source. This is a reference-based reconstruction, not a claim of exact 1:1 identity.

The source directory contains `build_sculpt.py`, `armor.py`, `ears.py`, `rig_delivery.py`, `validate_sculpt.py`, and `render_motion.py`. These keep geometry construction, rig/export, validation, and motion-preview generation reproducible. The delivery path is `public/assets/3d/asterion/asterion-sculpt-v001.glb`. Its single merged mesh is an export optimization, not a flattened model or a replacement for the editable Blender master. The animation names remain `idle`, `blink`, `happy`, `eat`, `play`, `pet_reaction`, `sleep`, `wake`, and `walk`.

The v001 reference and review renders live in `assets/3d/reference/asterion/sculpt-v001/`. Review all four principal views and motion previews, then check the actual exported GLB independently. Source renders, static GLB inspection, Blender re-import, browser rendering, animation behavior, human identity acceptance, and mobile performance are separate evidence levels. Consult the generated final reports for counts and validation results; a successful source build alone is not acceptance of the delivery.

The opt-in `/3d-preview` route offers fixed three-quarter, front, side, and rear cameras, pointer orbit, clip replay, and reduced-motion review. Camera fitting accounts for portrait aspect ratios. `NEXT_PUBLIC_ASTERION_3D_ENABLED` stays off by default, and the previous 2D fallback behavior is preserved. No representative mobile-performance acceptance is claimed.

## Additional companion sculptures

### Preserved modular refinement: sculpt-v003

This round brought all seven additional pets to Asterion's body/outfit contract.
Each v003 GLB has two independently visible meshes on its original shared rig;
all nine source clips remain unchanged. Species-specific fur/hair relief,
selected lower muzzles and cloth families received geometry edits. Brumo has a
closed under-tunic and shorts beneath his removable outfit; Selya retains her
mint/ivory base dress and wings; Aelira retains tunic, trousers and closed boots.

The versioned workflow is `assets/3d/source/companions/sculpt-v003/README.md`.
Each delivered master is reopened, both old/new GLBs are freshly imported,
complete source animation fingerprints are compared, and deformation is sampled
at nine times for all nine clips. Six source and four independent import views
include outfit-off and blink checks. Meshopt decoding and actual equipment
visibility are tested through Three.js. The preview stores visibility per pet
for the current page session only. Inventory and reward logic remain out of scope.

These approximately 1.20–1.52 million-triangle assets are high-poly desktop
review models, not accepted mobile deliveries or exact 1:1 reconstructions.
That round preserved all earlier versions, portraits and Asterion v004. Its
files remain available beside the current likeness round described above.
The following sections describe the preserved earlier passes.

The initial pass produced seven distinct `sculpt-v001` Blender masters and
GLB exports: Liora/rabbit, Nyra/cat, Brumo/orc, Caelo/pony, Selya/fairy, Fenn/dog,
and Aelira/elf. Their single-view portraits in `public/assets/companions/` govern
identity; hidden surfaces are inferred, not asserted as exact matches.

Shared reproducible builders and instructions live in
`assets/3d/source/companions/sculpt-v001/`. Each master has its own source folder
and hash manifest. Reference copies, four principal renders, independent GLB
re-import checks and blink views live in each pet's reference folder. The
collection gallery and aggregate manifest live under
`assets/3d/reference/companions/sculpt-v001/`.

The `/3d-preview` pet selector and opt-in Tamagotchi model mapping now cover all
eight pets, preserving Asterion's current file and the unchanged default 2D
behavior. The new figures provide nine simple presentation clips, not simulated
gaits or collision-free cloth motion. Fresh technical checks, visual review,
human likeness acceptance and representative mobile performance remain distinct.
The latter two are explicitly not marked accepted for the new collection.

### Caelo reference refinement

Caelo is the first pet in the requested second refinement pass. His new editable
master is `assets/3d/source/pony/sculpt-v002/pony-sculpt-v002.blend`, with delivery
at `public/assets/3d/pony/pony-sculpt-v002.glb`. The original `pony.png` and every
v001 master/export are retained unchanged. Anatomy, eyelids, cupped ears, flowing
hair volumes, shaped gold fittings and their contact with the body were rebuilt.
The v002 review includes all four principal views, independent GLB import, six
full-mesh animation samples and vertex-level loop endpoint comparisons. These
technical checks do not establish exact likeness, collision-free movement or
mobile performance. Liora is the second pet revised, as described below.

See `assets/3d/source/pony/sculpt-v002/README.md` for reproduction and
`assets/3d/reference/pony/sculpt-v002/REVIEW.md` for the handoff evidence.

### Liora reference refinement

Liora now has the second `sculpt-v002` master and GLB. Her unchanged rabbit
portrait governs the compact anatomy, cream fur, violet ears, expressive eyes
and rose-copper/lavender hardware. Fresh candidates corrected eye-socket color
loss, noisy metal fitting and an incorrectly routed girth before packaging.
Four source views, independent GLB import and full-mesh motion checks accompany
the source. This pass selected the new rabbit GLB while preserving Caelo,
Asterion, original portraits and historical v001 files.

See `assets/3d/source/rabbit/sculpt-v002/README.md` for reproduction and
`assets/3d/reference/rabbit/sculpt-v002/REVIEW.md` for measured evidence and
remaining likeness/performance boundaries.

### Remaining reference refinements

Nyra, Brumo, Selya, Fenn and Aelira now also use `sculpt-v002`. Their editable
masters, self-contained animated GLBs and reference-led builders are packaged
separately. Faces, eyes, hair/fur, clothing, armor and fitted ornaments received
geometry changes rather than subdivision alone. Every original portrait and
v001 master/export is retained; Asterion and the delivered Caelo/Liora assets
remain unchanged.

The five new deliveries contain approximately 1.29–1.52 million imported
triangles and 13.67–16.47 MB each. They are deliberately high-poly review assets,
not accepted mobile models. Each has nine clips, one mesh/skin and fewer than
40 material primitives. Four source views, three independent import views,
19 import checks, six full-mesh motion samples and three vertex-level loop
comparisons accompany every figure. Exact counts and hashes are recorded in
the individual manifests. These checks do not establish exact likeness,
collision-free animation, ground contact or representative mobile performance.

The common workflow is `assets/3d/source/companions/sculpt-v002/README.md`.
The current artifact index is `assets/3d/COMPANION-FIGURES.md`; the new gallery,
aggregate manifest and runtime/build evidence live under
`assets/3d/reference/companions/sculpt-v002/`. That pass selected v002 for all
seven additional companions while preserving Asterion's separate versioned pipeline.
The 2D default, opt-in feature flag and reduced-motion/error fallback remain.

### Historical Asterion reconstructions

`asterion-canonical-highpoly-v001.blend` and its GLB reconstructed the old 192×208 portrait as a dense relief shell. The user rejected that result as an adequate 3D Asterion. Its single-view silhouette and color-registration metrics remain historical evidence for that approach only; they do not establish volumetric likeness or acceptance of the new sculpt.

The relief/canonical-highpoly files, `asterion-highpoly-v005.blend`, `asterion-web-highpoly-v001.blend`, `asterion-highpoly-v001.glb`, and the earlier `asterion.blend`/`asterion.glb` are retained historical checkpoints. None is the current 3D design or runtime authority. The earlier `asterion-turnaround-guidance-v001.png` remains exploratory guidance. `public/assets/companions/asterion.png` remains the existing 2D fallback artwork, while the newly supplied four-view sheet governs the current 3D reconstruction.
