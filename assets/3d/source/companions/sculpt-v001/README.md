# Companion sculptures — v001

Seven individually modeled figures extend the existing Asterion master:
Liora (rabbit), Nyra (cat), Brumo (orc), Caelo (pony), Selya (fairy),
Fenn (dog), and Aelira (elf).

The authority for each figure is `public/assets/companions/<kind>.png`.
These are single-view references: unshown sides, backs, clothing construction
and movement are artistic interpretations. No 1:1 likeness or user acceptance
of these new figures is asserted. No reference images are projected onto the
models. All anatomy, ears, hair/fur, clothing, armor, ornaments and wings are
mesh geometry. Irises use authored vertex colors and zero emission.

## Files

- Editable masters: `assets/3d/source/<kind>/sculpt-v001/<kind>-sculpt-v001.blend`.
- Runtime exports: `public/assets/3d/<kind>/<kind>-sculpt-v001.glb`.
- Exact reference copies, four source views, three fresh-import views and checks:
  `assets/3d/reference/<kind>/sculpt-v001/`.
- Per-figure manifest beside each master; collection manifest and gallery:
  `assets/3d/reference/companions/sculpt-v001/`.

The source preserves editable component meshes, named materials and the rig.
Only temporary weighted copies are merged for the single-mesh Meshopt GLB.
Asterion's accepted source and GLB are not modified by these builders.

## Reproduction

Blender 5.2.1 LTS with its bundled Python, Cycles, glTF exporter and Meshopt
encoder is sufficient. No paid generation provider, external add-on or new
account is required. `woodland.py`, `humanoids.py` and `sky_folk.py` contain the
separate character builders. `common.py` imports the existing Asterion geometry
and export helpers; retain those files when moving this source package.

Use an absolute **fresh** output directory; existing GLB files are refused:
run from the repository root with Blender on PATH, replacing
`<absolute-output-root>` with your chosen local output directory.

```powershell
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/companions/sculpt-v001/build_collection.py -- --kind rabbit --output <absolute-output-root>/rabbit --views hero,front,side,rear --resolution 1400 --samples 64
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/companions/sculpt-v001/validate_collection.py -- --glb <absolute-output-root>/rabbit/rabbit-sculpt-v001.glb --output <absolute-output-root>/rabbit/validation
```

`package_collection.py` copies seven validated build folders into their
versioned delivery paths, checking reference, master and GLB hashes. It refuses
to replace a different existing binary. Reports use repository-relative paths.
For a pre-handoff refinement only, `--kinds cat dog --previous <previous-build-root>`
permits replacement when each existing binary or render still matches the exact
previous build. An externally changed file is refused; private previous builds
remain recoverable.
`render_gallery.py` imports the seven actual GLB files and renders them together;
the gallery does not substitute source illustrations for models.

## Animation and acceptance boundaries

Each figure contains `idle`, `blink`, `happy`, `eat`, `play`, `pet_reaction`,
`sleep`, `wake`, and `walk`. They are gentle stylized presentation gestures:
head tilts/nods, small limb swings, tail/ear/wing motion and moving eyelid covers.
They are not biomechanical walking cycles, complex facial rigs or clothing
simulations. Parts are predominantly rigid-weighted to their logical bones.

Fresh checks reopen each saved master to verify retained actions and editable
parts, then separately import the GLB. They check nine retained actions, volume
in all axes, normalized skin weights, both eyelids, finite vertices and finite
bone matrices sampled at five times per clip. These checks do not establish
collision-free deformation at every possible transition. Source and imported
hero/rear/blink images remain separate visual evidence.

The opt-in `/3d-preview` selector exposes all eight pets. The existing 2D default,
loading/error/unsupported-WebGL fallback and reduced-motion fallback remain.
These high-poly figures have **not** passed representative mobile performance
acceptance. A lower-cost LOD/bake is a separate release step.

This is a manually validated local handoff, not a canonical game-dev CLI asset
package or license receipt. The repository's existing artwork is the provenance;
no new commercial distribution license is granted. Source binaries follow the
existing LFS patterns. No commit, push, publication or deployment is performed.
