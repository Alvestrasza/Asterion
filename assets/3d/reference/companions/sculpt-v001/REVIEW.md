# Companion collection — local review

Date: 2026-09-05. Blender: 5.2.1 LTS. Status: local sculpt handoff, not a
production/mobile release or a claim of exact reference identity.

## Delivered geometry

| Figure | Triangles | Vertices | Bones | Material draws | GLB bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Liora | 855,478 | 431,791 | 13 | 15 | 6,992,148 |
| Nyra | 752,024 | 380,078 | 13 | 16 | 6,099,384 |
| Brumo | 553,418 | 282,271 | 10 | 18 | 4,399,264 |
| Caelo | 580,972 | 300,665 | 13 | 16 | 4,943,264 |
| Selya | 776,976 | 423,231 | 12 | 21 | 6,788,380 |
| Fenn | 893,720 | 454,834 | 13 | 14 | 7,240,932 |
| Aelira | 567,432 | 288,366 | 10 | 18 | 4,431,420 |

Total: 4,980,020 triangles and 40,894,792 GLB bytes across seven assets. Each
delivery contains one skinned mesh with multiple material primitives. Masters
retain 127–503 separately editable mesh objects. The gallery is rendered from
the actual delivered GLBs, not from reference-image planes.

## Fresh evidence

- Seven saved Blender masters reopened with all nine animation actions intact.
- Seven separate GLB imports passed the recorded structure, volume, finite
  geometry, normalized weighting, known bones and eyelid checks.
- Nine clips per asset sampled at five times for finite bone matrices. Import
  uses 30 FPS before glTF time conversion. Each imported idle ends at frame 121.
- Four source views and imported hero/rear/blink views were inspected. Iteration
  corrected buried eyes, floating eye edges and smiles, armor/cloth intersections,
  pendant clearance, unfitted crescents and mismatched tail fur pieces.
- All final models loaded in the local WebGL viewer. Companion changes retained
  exactly one canvas; there were no model-page console errors or warnings.
- Four view controls and all nine clip controls were exercised on Aelira. Fenn's
  sleep pose was inspected. Reduced Motion removed the canvas, showed the correct
  2D portrait, and restored 3D when switched off.
- `pnpm check`, all 26 tests and `pnpm build` passed. The final public assets were
  recopied into the standalone artifact; public, master, manifest and bundled GLB
  hashes were checked. Asterion's accepted master and GLB hashes are unchanged.

The earlier review caught orphaned Blender actions: setting fake users before
saving fixed the loss of eight clips on reopening. A separate validator timing
issue was corrected by configuring 30 FPS before import rather than afterwards.

## Boundaries

These are stylized full-volume interpretations of single-view artwork. Human
likeness acceptance remains open. The rigs provide simple presentation gestures,
predominantly rigid part weighting and expanding eyelid covers; they are not
biomechanical gaits, elaborate facial rigs or cloth simulations. Sampling finite
bone matrices does not prove collision-free geometry at every animation time.

Representative mobile performance, device-wide GPU memory, full animation
transition acceptance and Linux production acceptance were not measured. The
feature flag remains off by default and existing 2D fallback behavior remains.
No commit, push or deployment was made.

The home route still reaches the login page. Its local Auth.js configuration
reports `MissingSecret`; no authentication configuration was changed and no
authenticated care/persistence workflow is claimed as tested in this review.
The independent model preview does not require this login configuration.

See [collection-manifest.json](collection-manifest.json), the per-pet import
reports and [file index](../../../COMPANION-FIGURES.md). Private iterative builds
are retained as recoverable checkpoints; no user source artifact was deleted.
