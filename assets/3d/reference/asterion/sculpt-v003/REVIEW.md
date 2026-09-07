# Asterion v003 head-hair study review

## Scope and measured evidence

Only the four mane/cheek groom groups were removed from a copy of v002, both
native Blender curves and browser meshes. Tail hair, anatomy, armor, materials
and all original animations remain unchanged. The previous complete groom
remains in the byte-identical v002 master and GLB.

`validation.json` records 24 passing checks: saved-master reopen, exact stored
geometry comparisons for every retained object, complete source action-data
identity, nine imported clips sampled at nine corresponding times, finite
normalized skinning, exact triangle subtraction, material preservation, and
native/export tail-strand correspondence. The result has 3,051,226 triangles
and 1,585,156 imported vertices; its GLB is 40,261,464 bytes.

Five source renders and four fresh-GLB-import renders are hash-bound in the
report. All nine renders were visually inspected: the head hair is absent,
the ivory tail groom remains, and the imported closed-blink view is intact.

## Application handoff

All 41 application tests, the TypeScript check and the local Windows production
build passed. The added tests decode the actual meshopt GLB through Three.js
and require every remaining groom vertex to be bound only to the tail bone;
they also verify that the complete v002 master/export remain byte-identical.

The local browser loaded v003 and displayed front, side, rear and three-quarter
views. Reduced Motion removed the canvas and loaded the existing 192-pixel-wide
2D artwork; disabling it restored exactly one ready canvas. No warning/error
logs or framework error overlays appeared during these checks. The home route
displayed the existing sign-in page without an error overlay. No authentication
or database workflow acceptance is implied.

The served GLB returned HTTP 200 and 40,261,464 bytes. Its hash and the copied
standalone-build asset hash match the manifest. This is local delivery evidence,
not Linux deployment acceptance. The opt-in 3D feature flag and 2D default remain
unchanged in project configuration.

## Visual limitation exposed by removal

The side view reveals that the pre-existing dorsal neck plates stand away
from the neck where the mane previously concealed them. This is deliberately
recorded rather than presented as finished anatomy: the requested hair-free
intermediate retains v002 geometry exactly. A subsequent form-refinement pass
should fit those plates to the actual neck and reassess the head silhouette.
No exact 1:1 likeness or representative mobile-performance acceptance is claimed.

![Head-hair-free source view](source-views/asterion-sculpt-hero.png)
