# Nyra — sculpt-v002

This is the editable, fully volumetric refinement of Nyra. The unchanged
`public/assets/companions/cat.png` is the identity and palette authority. The
sculpt-v001 source is preserved as historical work; it is not overwritten.

## Source

- `model.py`: fused feline anatomy, recessed ears, layered crest and cheek coat,
  short directional fur relief, fitted teal/copper armor, faceted emerald
  pendant, rounded copper toe sheaths, and a continuous curled plume.
- `nyra_detail.py`: local mesh, clean-support, sculpt, material and eye helpers.
- `cat-sculpt-v002.blend`: editable master when the verified build is packaged.

The portrait is not projected onto geometry. Body and face have authored vertex
color and real short-fur relief. Silver regions follow three-dimensional locks
and the closed tail surface. Broad shoulder shells use a smooth analytical
envelope fitted to clean anatomy; the tail's copper accents use the analytical
tail surface instead of copying small fur grooves.

Eyes are independent convex surfaces seated in boolean-cut sockets, with a
continuous skin transition, real eyelid geometry and a separate blink state.
Their vertex-colored materials do not use emission. The existing quadruped rig
contract provides 13 exported bones and the nine presentation clips: `idle`,
`blink`, `walk`, `happy`, `eat`, `play`, `pet_reaction`, `sleep`, and `wake`.

## Rebuild and acceptance

Run the shared `assets/3d/source/companions/sculpt-v002/build.py` in Blender with
`--kind cat --output <fresh-absolute-review-directory>`. It imports the local
model and the preserved companion/Asterion toolkit. Existing build outputs must
not be overwritten. Use the shared delivery and motion-inspection scripts to
verify the exported GLB, its material attributes, imported views, blink coverage,
all clips, bounds and finite geometry before packaging.

Exact triangle, byte, object and hash values belong to the generated build and
validation reports, not to assumptions in this source document. The browser GLB
is merged for delivery efficiency; the Blender source retains editable objects.
Hidden views and movements are interpretations of a single-view illustration,
not an exact 1:1 claim. Mobile performance and human likeness acceptance remain
separate gates. The default-off 3D feature flag and existing 2D fallback are
preserved.
