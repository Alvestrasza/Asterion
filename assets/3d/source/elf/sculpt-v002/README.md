# Aelira — reference-led sculpt v002

The unchanged `public/assets/companions/elf.png` portrait governs Aelira's
identity: warm skin, violet eyes, pointed ears, deep green parted hair and braid,
cream embroidered tailoring, a forest mantle and cape, and leather boots. It is
a single-view portrait. The neutral stance, rear construction, hidden anatomy
and braid routing are interpretations. The historical v001 sources and assets
remain preserved.

## Modeled changes

- A rebuilt tapered face with soft cheeks, shaped nose and smile, recessed
  violet ocular surfaces, long cupped ears and tapered brows.
- A raised natural forehead hairline, broad scored crown locks, face-framing
  curls and three crossing braid strands following an inward shoulder route.
- Individually shaped fingers and thumb; curved split-skirt panels with folds;
  raised leaf embroidery fitted to the actual tunic, skirt and vambrace meshes.
- A physically thick folded cape with modeled leaf embroidery along its
  margins and hem, joined visually to a neck-to-shoulder mantle.
- Vertical shaped cream boot cuffs, fitted leather straps, toe stitches and
  shallow garment/boot settings seated on their supporting surfaces.
- Authored skin, hair, leather and woven-cloth vertex-color variation, with
  shallow modeled folds and scored channels rather than subdivision alone.

All main forms are volumetric and independently editable. The portrait is not
projected onto geometry. The stylized expression, regularized hair groups,
inferred hidden surfaces and neutral pose remain likeness limitations; detail
or triangle counts do not establish exact identity acceptance.

## Reproduction and deliverables

`model.py` contains Aelira's builder and garment construction. The local
`sculpt_helpers.py` supplies eye sockets, ears, scored locks, fitting and surface
color helpers; it is an independent copy, not a cross-pet runtime import.
Historical companion geometry and rig utilities are also required. Follow the
[shared v002 reproduction pipeline](../../companions/sculpt-v002/README.md) with
`--kind elf` and fresh absolute output directories.

The Blender master retains named editable objects. The browser GLB is exported
separately with a skinned mesh and nine presentation clips: idle, blink, happy,
eat, play, pet_reaction, sleep, wake and walk. The generated manifest and review
reports record actual counts, hashes and check results. This source description
does not substitute for the independent import, blink and motion inspections.

No exact 1:1 match, human likeness approval, collision-free gait, mobile
performance or production acceptance is claimed. The website keeps its 2D
default and fallback. No paid provider, deployment, publication or Git operation
is part of this locally authored source package.
