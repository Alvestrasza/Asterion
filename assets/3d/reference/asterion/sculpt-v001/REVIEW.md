# Sculpt v001 review — 2026-09-05

## Authority and construction

The user supplied the four-view attachment and explicitly requested a new,
detailed 3D Asterion. The previous portrait relief was rejected. This candidate
uses actual sculpted quadruped anatomy and modeled ornaments. The source image
is preserved, not projected onto the visible surface. No paid generation
provider was used. The source is reproducible with the adjacent Blender scripts.

| Artifact | Verified result |
| --- | --- |
| Editable master | 241 mesh objects; 769,383 vertices; 1,496,672 triangles |
| GLB | 14,130,508 bytes; one merged mesh; 18 materials/primitives |
| Deformation | One armature, 22 bones, nine named clips |
| Delivery | Self-contained Meshopt GLB; no image textures, cameras or lights |
| Motion evidence | H.264, 720×720, 96 frames at 24 fps; actual idle and blink |

Reference SHA-256:
`FE91A72F21A139CB4443E7BDE99498FC7AF7D07B8784A5F4A0B48CC37A141AEC`

Master SHA-256:
`AD7976E6715D5528E67959E6B8C29B6B42D9C3C699CCBAB085AC3A47593D42E0`

GLB SHA-256:
`EE133C744A11C37FDC447963094E2C4F7614441FC6CDC5127960FFD7135FD165`

Movie SHA-256:
`3C81C1512D5608669F67E3D7F60A49A86057E985C38395AE889392125995FC41`

## Fresh evidence

- Blender 5.2.1 LTS generated five 1600px source views.
- A fresh scene imported the exported GLB, checked all nine clips and sampled
  transforms, normalized weights, four distinct weighted paws and full XYZ
  volume. All automated checks passed. Three fresh-import renders are retained.
- The independent motion renderer left the master unchanged. Six decoded movie
  frames show both sides, the rear, front and blink. Corrected gold tail inlays
  follow the tail instead of leaving detached rods.
- The browser preview loaded the actual GLB, retained cyan eye color, switched
  fixed views, played the walk clip and restored the static 2D fallback with
  Reduced Motion. No application error or framework error overlay was observed.
  The WebGL driver emitted a non-fatal precision warning while compiling the
  studio environment shader; this is not a warning-free certification.
- The separate home-route smoke check reached the login screen but reported
  `MissingSecret` and a development performance-timing error. Authentication
  was not configured or changed for this asset-only workstation task; the
  passing 3D-preview check must not be represented as full application acceptance.
- Nineteen deterministic tests, TypeScript checking and a local production
  build passed during this change. These do not establish Linux deployment,
  mobile performance, authentication or database acceptance.

The eye material intentionally has zero emission. Vertex-colored emission is
not representable in this GLB workflow and had exported as uniform gray. The
regression test rejects that gray-emission material.

## Visual acceptance remains separate

This is a complete volumetric candidate, not a proven 1:1 reconstruction or a
record of user approval. Remaining differences include the softer, broader
smiling face; larger, more regular mane locks; simplified horn/armor facets;
and a broad smooth rear-skull patch around the central ridge. A tiny pale seam
can remain at the far eye's inner corner during peak blink. The surface reads
more like a sculpted figure than the reference's painterly layering.

Do not use triangle count or a successful import as proof of likeness. The 2D
presentation and default-off feature flag remain. Representative mobile
performance and human likeness acceptance are outstanding. No commit, push or
deployment was performed for this handoff.
