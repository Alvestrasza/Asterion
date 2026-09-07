# Asterion reference refinement v002

This revision loads a copy of the unchanged `sculpt-v001` master and refines
the approved four-view reconstruction. It targets approximately five million
**delivered mesh triangles, including portable hair geometry**. Native Blender
hair is counted separately as strands and control points, not as triangles.

The original master, original GLB, approved turnaround and all seven other pets
are preserved. `manifest.json` records measured counts and hashes; the linked
independent validation report, not an earlier version's metrics, is authoritative.

## Changes and source organization

- `refine_geometry.py`: compact wedge muzzle and shorter mouth; fuller blue
  irises; less inflated brows; flattened, longitudinally faceted horns; softer
  anatomical scales and fitted rear-skull/temple lamellae; shallow blue armor
  detail; shorter, seated claws. This is not subdivision alone.
- `hair_groom.py`: deterministic, surface-rooted ivory mane/cheek/tail groom.
  Five native `CURVES` objects are visible and editable in Blender. Five paired
  tube meshes start hidden in the master and are used only for portable export.
  Their centers and radii come from the exact same strand data.
- `build_refinement.py`: opens the historical master, performs the refinement,
  exports a temporary joined copy, renders five views and saves a new master.
- `validate_refinement.py`: independently reopens the master and imports both
  historical and new GLBs. It checks full original action/rest fingerprints,
  native/tube correspondence, finite geometry, weights and sampled motion.
- `deliver_refinement.py`: hash-bound preflight and staged local handoff. It
  refuses different existing v002 artifacts and never targets historical files.

The `AST_Groom_v002_*_native` objects are the actual editable Blender hair.
The `*_export` equivalents are ordinary skinned mesh strands, not hair cards,
billboards, textures or browser physics. Do not display both versions together
in Blender: that would double the hair surface. Native and export strands use
plain portable materials; Blender's specialized hair shader is not claimed to
survive glTF export.

## Animation boundary

No actions, keyframes, bone rest transforms or new animation clips are authored
by this revision. Hair attaches rigidly to existing `head` and `tail.01` bones;
it has no simulation or secondary-motion animation. The nine existing clips
remain `idle`, `blink`, `happy`, `eat`, `play`, `pet_reaction`, `sleep`, `wake`,
and `walk`. Their artistic refinement is explicitly deferred by the user.

Source action equality is strict. Export/import timing and transforms are a
different evidence level: the new export is sampled against a fresh import of
the historical v001 GLB, using the same Blender version and frame rate. The
validator separately records the historical source-to-export discrepancy; it
does not weaken source equality to accommodate that discrepancy. Sampling is
not a guarantee of collision-free motion at every frame.

## Reproduce locally

Run from the repository root. Use a **new** output directory each time.
The following example path must not already exist:

```powershell
$blender = '<path-to-blender-executable>'
$review = Join-Path (Get-Location) '.private/3d-work/asterion/sculpt-v002/new-review'
& $blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/asterion/sculpt-v002/build_refinement.py -- --output $review --resolution 1600 --samples 64 --views hero,front,side,rear,face
& $blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/asterion/sculpt-v002/validate_refinement.py -- --master "$review\asterion-sculpt-v002.blend" --glb "$review\asterion-sculpt-v002.glb" --output "$review\validation" --resolution 1200
```

Inspect all source views and independent import views before local packaging:

```powershell
python assets/3d/source/asterion/sculpt-v002/deliver_refinement.py --input $review
```

Run the small Blender API tests separately with `--background --factory-startup
--python-exit-code 1 --python <test-file>`:

- `test_hair_groom_api.py`: actual native/tube layout and posed correspondence.
- `test_material_export_api.py`: actual glTF export preserves the navy palette
  and vertex-level detail. Legacy MixRGB silently lost both; the supported
  modern RGBA Mix node is regression-tested.

The stdlib `test_refinement_validator.py` and `test_refinement_delivery.py`
cover fingerprint and delivery failure gates. The repository's
`tests/asterion-refinement.test.mjs` binds the final runtime artifact and evidence.

## Acceptance and provenance

This is local Blender authoring; no paid generation provider or external asset
upload is involved. It is not a canonical Game-Dev-CLI package receipt, and no
new third-party distribution license is granted. The game-asset workflow keeps
reference, editable authority, portable export and independent checks separate.

The four-view sheet guides the modeled interpretation, but exact 1:1 likeness
and human approval are not asserted. The five-million-triangle budget is an
explicit high-end request, not mobile optimization. The 2D default/fallback and
opt-in `NEXT_PUBLIC_ASTERION_3D_ENABLED` policy remain unchanged. No deployment,
Git commit or push is part of this handoff.
