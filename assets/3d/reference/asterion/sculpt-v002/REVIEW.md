# Asterion v002 refinement review

Date: 2026-09-05. Authority: the unchanged user-approved four-view turnaround.
This is a closer modeled interpretation, **not accepted as an exact 1:1 copy**.

## Delivered result

| Measurement | Actual result |
| --- | ---: |
| Delivered and independently imported triangles | 4,999,970 |
| Body, horns, armor and other non-hair triangles | 2,564,074 |
| Portable hair triangles | 2,435,896 |
| Native Blender hair strands | 17,911 |
| Native hair control points | 250,754 |
| Native groom groups / matching export meshes | 5 / 5 |
| Separately editable solid source meshes | 149 |
| Imported vertices | 2,588,186 |
| GLB materials / material primitives | 18 / 18 |
| Bones / existing clips | 22 / 9 |
| GLB bytes | 51,800,360 |
| Editable master bytes | 108,246,076 |

The [manifest](../../../source/asterion/sculpt-v002/manifest.json) binds the
master, export, approved image, historical animation-calibration GLB and builder
dependencies. The [independent report](refinement-validation.json) binds the
actual master/GLB and validator. Historical Asterion and all other pet artifacts
remain unchanged; the repository tests verify those preservation hashes.

## Visual review and corrections

The source views cover [hero](asterion-sculpt-hero.png),
[front](asterion-sculpt-front.png), [side](asterion-sculpt-side.png),
[rear](asterion-sculpt-rear.png) and [face](asterion-sculpt-face.png).
Independent renders of the actual delivered GLB cover
[hero](import-review/asterion-hero.png), [rear](import-review/asterion-rear.png),
[face](import-review/asterion-face.png) and
[closed blink](import-review/asterion-closed_blink_front.png).

The refinement makes the lower muzzle more compact, enlarges the blue irises,
reduces tubular brow inflation, flattens the broad horn planes and adds shallow
fitted scale/enamel detail. Rear-skull coverage and armor-edge protrusions were
corrected after the geometry preview. The first native groom still formed near-
horizontal brush-like tiers; the second uses diagonal overlapping lower locks,
staggered upper flicks and a fuller surface-rooted tail transition.

The first full export also revealed a real material failure: legacy MixRGB
rendered correctly in Blender but exported white surface factors. The corrected
modern RGBA Mix setup passed a real small export regression test, followed by
inspection of the complete exported palette and all four independent renders.

## Fresh verification

- All 30 independent acceptance checks passed. Exported and imported triangle
  counts match exactly in this delivered file; no importer-loss allowance was
  used for acceptance.
- Original rest hierarchy, transforms, constraints/drivers, nine complete
  actions and their key/handle data compare equal. No animation redesign.
- All 250,754 native points correspond to their paired tube rings. Worst center
  error is below 0.00000051 world units; radius error is below 0.00000095.
- All imported vertices are finite and have normalized known weights with at
  most four positive influences. The exporter normalizes/truncates interpolated
  source influences to its existing four-weight delivery contract.
- Nine samples per clip, 81 times total, match the freshly imported historical
  GLB with zero measured world skin-matrix and duration difference. This is a
  bounded regression check, not exhaustive per-frame collision acceptance.
- Factory-startup Blender API tests: 2 groom tests and 1 actual material-export
  regression passed. Stdlib checks: 11 fingerprint/import-count tests, 8
  Asterion-specific delivery tests and 11 shared staged-delivery tests passed.
- Repository: `pnpm test` 38/38 passed; `pnpm check` and `pnpm build` passed.
- HTTP served 51,800,360 bytes with the manifest GLB hash. The standalone build
  contains an identical-hash copy of the same v002 GLB.
- Integrated browser `/3d-preview`: new Asterion reached `ready` with one WebGL
  canvas, all four fixed views were inspected, the existing sleep clip rendered,
  and Reduced Motion switched to the original complete 192-pixel portrait with
  zero canvases. Disabling it restored one ready canvas. Final state is Asterion,
  three-quarter view, idle. No error overlay or fresh warning/error log entries.
  A stale tab initially reported connection refused after the server restart;
  a fresh tab loaded successfully after the server responded HTTP 200.

## Remaining boundaries

More polygons do not guarantee likeness. The reference still has different
head/body proportions, a more tightly designed eye/lid contour, less regular
scale placement and more painterly horn/armor transitions. The mane is now real
editable strand geometry but remains a stylized authored groom. Native curves
and five-sided browser strands can produce different fine highlights; very
small screen sizes can make dense strands look grainy. These are visible art
and rendering considerations, not solved by another subdivision level.

The user deferred animation refinement. Existing gesture quality, full-frame
hair/body intersection checks, exact likeness approval, and representative
mobile/frame-rate acceptance are not claimed. The 2D default/fallback remains
unchanged. No simulation, paid provider, reference upload, canonical Game-Dev-CLI
package receipt, deployment, commit or push was performed.
