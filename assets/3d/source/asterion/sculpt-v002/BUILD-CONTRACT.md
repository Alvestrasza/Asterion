# Asterion reference refinement — sculpt-v002

The user requests a closer reconstruction of the existing approved four-view
turnaround, approximately five million triangles and real Blender hair where
possible. Animation refinement is explicitly deferred.

## Controlling decisions

- Load the existing sculpt-v001 master as an immutable baseline; save all work
  to a fresh versioned path. The original turnaround remains the identity source.
- Aim for 4.5–5.5 million delivered triangles, including the static browser hair
  geometry. Native Blender hair curves are counted separately as strands/points.
- Improve silhouette, facial planes, horn facets, scale hierarchy, fitted armor
  detail and claws; subdivision without visible purpose is not the outcome.
- Keep the exact existing armature rest structure and nine actions/keyframes.
  Hair follows existing attachments without physics or new secondary animation.
- Retain editable native Hair Curves in the master and derive portable strand
  meshes from the same points/radii for GLB. Do not claim glTF preserves native
  Blender hair or its shader. No image projection or reference replacement.
- Preserve all seven other pets, their builders and their delivered artifacts.
- Keep 2D default/fallback and opt-in 3D. Five million triangles is an explicit
  high-end review budget, not mobile-performance acceptance.

## Evidence and delivery

Inspect source hero/front/side/rear/face views; independently reopen the master
and import the actual GLB. Bind file hashes, compare complete baseline action
and rest-rig data, verify finite geometry, native/tube hair correspondence,
weights, counts, materials and nine clips. Animation sampling is a regression
check only, not a request to redesign existing gestures. Check the actual browser
load and fallback, run repository tests/type check/build, and retain review notes
with remaining likeness/performance limitations.

All work is local Blender authoring, not a paid-provider or canonical game-dev
package receipt. No new public license, authentication change, deployment,
publication or Git commit/push is authorized by this refinement.
