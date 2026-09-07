# Asterion sculpt-v003: temporary head-hair-free study

This version implements the user's request to leave out the head hair for now.
It is a copy of v002 with only the left/right mane and cheek groom pairs removed:
four native hair objects and their four portable mesh equivalents. It is not a
new anatomy refinement or a claim of exact reference identity.

- 3,051,226 triangles, exactly 1,948,744 fewer than v002; no subdivision padding.
- 40,261,464-byte GLB, 18 materials, one mesh and skin, 22 bones, nine clips.
- Tail hair remains: 3,582 native strands and matching static export geometry.
- All retained source geometry, materials, rest rig and complete action data
  are unchanged. Sampled imported motion also matches v002 exactly.
- The complete v002 BLEND and GLB remain unchanged and recoverable.

The source is `asterion-sculpt-v003.blend`; the delivery is
`public/assets/3d/asterion/asterion-sculpt-v003.glb`. See `manifest.json` for
hash-bound artifacts and the [review](../../../reference/asterion/sculpt-v003/REVIEW.md)
for evidence and known limitations. Keep the existing 2D default and fallback.

## Reproduce and deliver

From the repository root, with local Blender and Python available, choose a
fresh output directory. Historical builder dependencies and v002 must remain
unchanged. The build reopens the saved master, hashes all retained geometry,
compares complete source actions, freshly imports both GLBs, and renders the
actual exported model independently.

```powershell
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/asterion/sculpt-v003/build_head_study.py -- --output .private/3d-work/asterion/sculpt-v003/candidate02 --resolution 1600 --samples 64
python assets/3d/source/asterion/sculpt-v003/build_head_study.py --deliver .private/3d-work/asterion/sculpt-v003/candidate02
```

Review the images and all validation checks before delivery. Staged delivery
verifies hashes, refuses conflicting existing artifacts, and rolls back a
partial write. Use a new version for any subsequent model change; do not
overwrite reviewed files. The separate Game-Dev CLI was not used for this pass.
