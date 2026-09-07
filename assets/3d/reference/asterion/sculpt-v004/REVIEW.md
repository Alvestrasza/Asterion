# Asterion sculpt-v004 review

## Scope and visual review

The unchanged approved four-view sheet remains the design authority. This
revision addresses the user's nape/back scale and pointed-mouth feedback and
separates the ceremonial armor. Head hair remains intentionally omitted.
Tail hair, eyes, horns, limbs, original rest rig and source actions are preserved.
The seven other companions are outside this revision.

Seven source renders and six renders from a fresh GLB import were inspected:
front, side, rear, three-quarter, face, armor-off views and a closed blink.
The muzzle is shorter and wider with a smaller fitted nose and compact lip
line. The previous raised nape/back plates are replaced by shallow overlapping
shields against the anatomical surface. The unarmored body remains complete;
natural horns, ear inlays, claws and throat scales are not treated as equipment.
The existing collar shape and other armor styling were not redesigned.

Useful comparisons:

- [Approved turnaround](asterion-approved-turnaround.png)
- [Imported armored three-quarter view](import-review/asterion-sculpt-hero.png)
- [Imported face](import-review/asterion-sculpt-face.png)
- [Imported rear](import-review/asterion-sculpt-rear.png)
- [Imported unarmored three-quarter view](import-review/armor-off/asterion-sculpt-hero.png)
- [Imported unarmored side](import-review/armor-off/asterion-sculpt-side.png)
- [Imported closed blink](import-review/blink/asterion-sculpt-front.png)

This is a targeted modeled revision, not a claim of exact 1:1 likeness. Final
artistic acceptance belongs to the user. Missing head hair deliberately changes
the reference silhouette. A successful render is not mobile-performance approval.

## Measured geometry and equipment

The [build report](../../../source/asterion/sculpt-v004/build-report.json),
[manifest](../../../source/asterion/sculpt-v004/manifest.json) and
[independent validation](validation.json) bind the source, export, reference and
builder dependencies by SHA-256.

| Delivery measurement | Result |
| --- | ---: |
| Body triangles | 2,985,588 |
| Armor triangles | 63,624 |
| Total triangles, authored and imported | 3,049,212 |
| Imported vertices | 1,584,221 |
| GLB bytes | 40,099,324 |
| Character meshes / shared skins / bones | 2 / 1 / 22 |
| Unique materials / material primitives | 18 / 23 |
| Individually editable source armor objects | 55 |
| Retained native tail strands | 3,582 |
| Replacement nape / back shields | 11 / 10 |

The front of the head retracts by 0.143004179 model units. The new mouth half
width is 0.355. The maximum new shield rim distance from the anatomical surface
is 0.005001015 model units (gate: 0.007); the previous plates' worst nearest
surface gap was 0.351570606. These are distinct contact diagnostics, not a
percentage improvement or an all-animation collision guarantee. Attachment
weights follow the underlying anatomical mesh.

Armor is a dedicated source collection and a separate `asterion_armor` node in
the same GLB as `asterion_body`. Both reference the original skin. Explicit
extras identify `outfit`, `ceremonial-gold-v1` and `asterion-rig-v1`; material
colors and suggestive names do not classify equipment. There is no inventory,
reward entitlement, individual-slot selector or external replacement loader.
See the [source guide](../../../source/asterion/sculpt-v004/README.md) before
authoring a replacement compatible with the rig and bind transforms.

## Independent validation

Blender 5.2.1 LTS reopened the saved master and freshly imported v003 and v004
GLBs. All 39 independent validation checks passed. Source rest hierarchy,
constraints, drivers and complete data for all nine actions compare unchanged.
Native tail curves and matching export strands compare exactly against v003.
No head hair remains. Geometry and transforms are finite; skin weights are
normalized, known and limited to four influences.

The imported versions have equal world skin matrices at nine corresponding
samples for each of the nine clips, with zero measured component and duration
error. This is sampled imported-motion equality, not GLB byte equality or a
new animation-quality acceptance. Both imported components share one armature.
The imported triangle count equals the authored count without loss.

Meshopt preserves the historical Blender encoder configuration, including
precision-reducing EXPONENTIAL and QUATERNION filters. This delivery is **not
claimed lossless**. Full-resolution source geometry is retained in the master.

## Application verification

All 50 application tests pass, including real Meshopt decoding, shared Three.js
bones, repeated outfit toggles, unchanged body geometry and a running animation
mixer that is not reset. Historical v001/v002/v003 files, original references
and the other pets' existing integrity contracts continue to pass.
`pnpm check` and the Windows `pnpm build` pass. The standalone bundle's GLB and
the HTTP-served GLB both match the manifest SHA-256; the HTTP response is 200
with 40,099,324 bytes.

The local preview was checked in the desktop in-app browser:

- Asterion reaches `ready` with one canvas, one outfit and nine visible armor
  material meshes. Front, side, rear and three-quarter views render correctly.
- `Ohne Rüstung` produces actual scene visibility `hidden`, with zero visible
  armor meshes and the full body still rendered. Re-enabling restores all nine.
- Toggling while `walk` is selected retains that selection and one canvas;
  the real-asset mixer regression test separately proves no animation reset.
- Reduced Motion removes the canvas and displays the unchanged original 2D
  artwork. Returning to 3D restores the chosen hidden-armor state.
- Switching to Liora removes equipment controls and loads her own model;
  returning to Asterion retains the preview armor choice.
- No warning or error was reported by the preview browser console. The page
  was left ready in armored three-quarter view with `idle` selected.

This checks the local asset-review workflow, not an authenticated care session.
The local authentication setup has an existing missing-secret diagnostic and
was not changed as part of this model revision.

The ordinary 2D presentation and feature-flag default remain unchanged. No
authentication, persistence, provider, deployment or reward-system changes are
part of this delivery. Windows build evidence does not replace Linux release
verification or representative mobile measurements.
