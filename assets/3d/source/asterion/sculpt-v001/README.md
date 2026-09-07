# Asterion volumetric sculpt v001

The editable master reconstructs the user-supplied four-view turnaround. This
is a full quadruped sculpture, not an image plane or portrait relief. Source
parts stay separate; the delivery exporter temporarily merges weighted copies.

## Reproduce

Blender 5.2.1 LTS was used. Its bundled Python, Cycles, glTF exporter and Meshopt
encoder are sufficient; no paid generation provider or external add-on is used.
Run from this directory with Blender available on PATH. Choose a fresh output
directory: the exporter refuses to overwrite an existing GLB.

```sh
blender --background --factory-startup --python build_sculpt.py -- --rig --output ./build-v002 --views hero,front,side,rear,face --resolution 1600
blender --background --factory-startup --python validate_sculpt.py -- --glb ./build-v002/asterion-sculpt-v001.glb --output ./build-v002/import-review
```

Motion output requires an absolute output directory, represented below by
`<absolute-motion-directory>`; replace that placeholder before running.

```sh
blender --background ./build-v002/asterion-sculpt-v001.blend --python render_motion.py -- --output <absolute-motion-directory> --frames 96 --fps 24 --resolution 720 --samples 24
```

`reference/asterion-approved-turnaround.png` is an exact local copy of the
approved reference, retained here so the generator can verify its provenance.
It is not used as a projected texture. Eyes use vertex color with zero emission
because glTF cannot reproduce vertex-colored emission; a constant gray export
would wash out the iris and pupil.

## Evidence and limitations

See `build-report.json`, `export-report.json`, and the independent import report
under `assets/3d/reference/asterion/sculpt-v001/`. All report paths are relative
to the repository root. The adjacent review note separates technical checks
from likeness acceptance and mobile performance.

Reference provenance is the user's attachment and explicit reconstruction
request, not a separately verified commercial asset license. No third-party
provider assets were downloaded. No new public distribution license is granted
by this handoff.
