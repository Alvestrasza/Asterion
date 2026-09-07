# Selya — v002 review

Status: delivered local high-poly review model; technical checks passed within
the bounds below. Final human likeness and mobile-performance acceptance remain
open. The unchanged [portrait](original.png) is the identity authority.

## Reference-led changes

- Rebuilt warm face, pointed cupped ears, hands, toes, coral hair foundation, crown waves and gold botanical jewelry.
- Four volumetric pearl-mint wings with modeled gold branches, layered folded petal clothing, fitted leaf cuffs and sandals.

Corrected hair-cap intersections, detached hook-like locks, blunt/flipped petal construction and buried sandals. Reduced oversampled hidden geometry while retaining wing branches and visible clothing detail.

## Measured delivered asset

| Property | Result |
| --- | ---: |
| Imported triangles | 1,426,998 |
| Imported vertices | 766,139 |
| GLB bytes | 15,148,892 |
| Exported bones | 12 |
| Material primitives | 19 |
| Separately editable master meshes | 1035 |
| Clips | 9 |

One self-contained Meshopt mesh/skin; no embedded images, projection, exported
cameras or lights. The [manifest](../../../source/fairy/sculpt-v002/manifest.json)
records exact master, GLB, reference and dependent-builder SHA-256 values.
The export index count (1,427,002) differs slightly from the imported face
count because degenerate triangles can be discarded during import.

## Inspected evidence

- Four source views: [hero](fairy-sculpt-hero.png),
  [front](fairy-sculpt-front.png), [side](fairy-sculpt-side.png),
  [rear](fairy-sculpt-rear.png), rendered at 1600 px / 64 samples.
- Independent actual-GLB import: [hero](import-review/fairy-sculpt-hero.png),
  [rear](import-review/fairy-sculpt-rear.png) and
  [closed blink](import-review/fairy-blink-sculpt-front.png), 1200 px / 32 samples.
  No missing parts, exposed iris in the closed-blink view or gross collapse found.
- [Import report](import-validation.json): all 19 checks passed. Reopened master
  and imported GLB are hash-bound; finite geometry, normalized known-bone weights,
  at most four influences, nine clips and both moving eyelids were checked.
- [Six-frame motion sheet](motion/fairy-v002-motion-contact-sheet.png),
  individually rendered at 800 px / 32 samples: idle 1, blink 10, happy 31,
  eat 46, sleep 61 and walk 13. All 766,139 evaluated vertices were finite
  in every sample; no exposed iris in the inspected blink/sleep samples.
- [Motion report](motion-validation.json): every evaluated vertex was compared
  at idle, sleep and walk endpoints. Maximum displacement is 0.0 for all three
  loops, within the 0.0001 scene-unit tolerance.

Blender 5.2.1 LTS was used. These are local source, render and import checks, not
canonical game-dev CLI receipts. The shared [collection review](../../companions/sculpt-v002/REVIEW.md)
records runtime/build checks separately. See the
[source guide](../../../source/fairy/sculpt-v002/README.md) for reproduction.

## Remaining boundaries

Hair is broader and straighter than the painted waves; eyes are paler mint, and the petal pattern, hands and ankles remain stylized.

Single-view hidden surfaces are interpretations, not exact 1:1 reconstruction.
Six motion samples and endpoint equality do not prove every frame, transition,
collision, ground contact, biomechanical gait or frame rate. Small negative Z
bounds can occur in the motion reports; this is not a ground-contact acceptance.
2D remains the default and reduced-motion/loading/error fallback. No paid
provider, authentication change, deployment or Git push was performed.

