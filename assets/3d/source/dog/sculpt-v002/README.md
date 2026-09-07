# Fenn — sculpt-v002

This is the editable, fully volumetric refinement of Fenn. The unchanged
`public/assets/companions/dog.png` is the identity and palette authority. The
sculpt-v001 source remains available as historical work and is not overwritten.

## Source

- `model.py`: continuous puppy anatomy and cream muzzle/paw fields, folded
  hanging ears with dark gradients, directed short fur, a layered cream bib,
  navy star collar, connected celestial medallion, seated markings, and a full
  curled tail.
- `fenn_detail.py`: local mesh, clean-support, sculpt, material and eye helpers.
- `dog-sculpt-v002.blend`: editable master when the verified build is packaged.

No image is projected onto the character. Fur relief is real geometry on the
closed body, ear and tail surfaces. Larger shallow strands follow the clean
support along their complete length. The paws use a continuous coat transition,
not floating cream patches. Crescents are shallow closed ornaments fitted to one
body surface. The navy collar and medallion retain Fenn's distinct reference
language rather than reusing another companion's armor.

Independent convex eyes sit in boolean-cut sockets and meet the skin at a shared
non-overlapping boundary. Vertex-colored irises use no emission. Separate eyelid
geometry supports the standard 13-bone quadruped rig and nine presentation clips:
`idle`, `blink`, `walk`, `happy`, `eat`, `play`, `pet_reaction`, `sleep`, and `wake`.

## Rebuild and acceptance

Run the shared `assets/3d/source/companions/sculpt-v002/build.py` in Blender with
`--kind dog --output <fresh-absolute-review-directory>`. It imports the local
model and the preserved companion/Asterion toolkit. Never overwrite an existing
review or accepted build. Use the shared delivery and motion-inspection scripts
to check the exported GLB, reimported views, blink coverage, all clips, bounds,
finite geometry and material attributes before packaging.

Use generated build and validation reports for exact triangle, byte, editable
object and hash values. The browser export is merged for delivery efficiency;
the Blender master keeps editable source meshes. Hidden views and gestures are
single-view interpretations, not exact 1:1 reconstruction claims. Human likeness
and mobile performance acceptance remain separate gates. The default-off 3D
feature flag and existing 2D fallback are preserved.
