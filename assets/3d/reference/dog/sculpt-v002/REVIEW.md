# Fenn — v002 review

Status: delivered local high-poly review model; technical checks passed within
the bounds below. Final human likeness and mobile-performance acceptance remain
open. The unchanged [portrait](original.png) is the identity authority.

## Reference-led changes

- Continuous golden puppy anatomy, cream muzzle/paws/bib, folded brown-tipped ears, blue eyes and directional coat relief.
- Lower navy collar, visible round moon/star medallion, shallow seated crescents and a fully closed cream-tipped curled tail.

Corrected detached-looking ear roots, intersecting orbital edges, unsupported nape chips, a bib-obscured medallion and crescent markings hidden by fur.

## Measured delivered asset

| Property | Result |
| --- | ---: |
| Imported triangles | 1,325,462 |
| Imported vertices | 665,293 |
| GLB bytes | 15,841,868 |
| Exported bones | 13 |
| Material primitives | 11 |
| Separately editable master meshes | 200 |
| Clips | 9 |

One self-contained Meshopt mesh/skin; no embedded images, projection, exported
cameras or lights. The [manifest](../../../source/dog/sculpt-v002/manifest.json)
records exact master, GLB, reference and dependent-builder SHA-256 values.
The export index count (1,325,472) differs slightly from the imported face
count because degenerate triangles can be discarded during import.

## Inspected evidence

- Four source views: [hero](dog-sculpt-hero.png),
  [front](dog-sculpt-front.png), [side](dog-sculpt-side.png),
  [rear](dog-sculpt-rear.png), rendered at 1600 px / 64 samples.
- Independent actual-GLB import: [hero](import-review/dog-sculpt-hero.png),
  [rear](import-review/dog-sculpt-rear.png) and
  [closed blink](import-review/dog-blink-sculpt-front.png), 1200 px / 32 samples.
  No missing parts, exposed iris in the closed-blink view or gross collapse found.
- [Import report](import-validation.json): all 19 checks passed. Reopened master
  and imported GLB are hash-bound; finite geometry, normalized known-bone weights,
  at most four influences, nine clips and both moving eyelids were checked.
- [Six-frame motion sheet](motion/dog-v002-motion-contact-sheet.png),
  individually rendered at 800 px / 32 samples: idle 1, blink 10, happy 31,
  eat 46, sleep 61 and walk 13. All 665,293 evaluated vertices were finite
  in every sample; no exposed iris in the inspected blink/sleep samples.
- [Motion report](motion-validation.json): every evaluated vertex was compared
  at idle, sleep and walk endpoints. Maximum displacement is 0.0 for all three
  loops, within the 0.0001 scene-unit tolerance.

Blender 5.2.1 LTS was used. These are local source, render and import checks, not
canonical game-dev CLI receipts. The shared [collection review](../../companions/sculpt-v002/REVIEW.md)
records runtime/build checks separately. See the
[source guide](../../../source/dog/sculpt-v002/README.md) for reproduction.

## Remaining boundaries

Eyes remain large and prominent, coat locks and relief are regularized, and the tail is smoother. The front collar and neutral pose simplify the reference.

Single-view hidden surfaces are interpretations, not exact 1:1 reconstruction.
Six motion samples and endpoint equality do not prove every frame, transition,
collision, ground contact, biomechanical gait or frame rate. Small negative Z
bounds can occur in the motion reports; this is not a ground-contact acceptance.
2D remains the default and reduced-motion/loading/error fallback. No paid
provider, authentication change, deployment or Git push was performed.

