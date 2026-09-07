# Liora — reference-led sculpt v002

Liora is the second pet refined after Caelo. The unchanged original
`public/assets/companions/rabbit.png` governs identity; unseen anatomy and
ornament surfaces are inferred from this single illustration. All v001 files
and Caelo's delivered v002 remain unchanged.

## Modeling scope

- Continuous compact rabbit anatomy, pronounced haunches and rounded, divided
  paws with normalized body/neck/limb skin weights.
- Asymmetric broad lavender ear bowls, thick walls, sculpted rose-copper guards.
- Violet-to-cyan almond eyes with recessed sockets, tapered brown lids, closed
  eyelid covers, a small rose nose and a restrained paired muzzle smile.
- Groomed cream surface relief, overlapping cheek fans, chest bib and a
  volumetric curled cotton tail. Color detail survives as vertex attributes.
- Open forehead diamond, faceted chest crystal and connector, fitted lavender
  shoulder/saddle panels, continuous neck harness and double angular fore-cuffs.

Every view uses genuine three-dimensional geometry. Increasing polygon count
alone does not establish likeness; no source image is projected onto a mesh.

## Reproduce

Use Blender 5.2.1 LTS or independently verify compatibility. The existing shared
toolkit and presentation rig are reused without editing historical sources.
Choose a new absolute review directory for every candidate.

```text
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/rabbit/sculpt-v002/build.py -- --output /absolute/new/liora-review --resolution 1600 --samples 64
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/companions/sculpt-v001/validate_collection.py -- --glb /absolute/new/liora-review/rabbit-sculpt-v002.glb --output /absolute/new/liora-review/validation --resolution 1200
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/rabbit/sculpt-v002/inspect_motion.py -- --glb /absolute/new/liora-review/rabbit-sculpt-v002.glb --output /absolute/new/liora-review/motion --resolution 800
python assets/3d/source/rabbit/sculpt-v002/deliver.py --input /absolute/new/liora-review
```

Packaging requires matching source, reference, builder and delivery hashes,
four principal renders, fresh-import validation and full-mesh motion evidence.
An existing different destination is refused. Before handoff only, an exact
`--previous /absolute/previous-review` permits replacement if every old target
still matches its preserved candidate. Handed-off versions need a new revision.

The Blender authority retains separate editable meshes. Delivery combines
weighted copies into one self-contained Meshopt-compressed GLB with the nine
stable idle, blink, happy, eat, play, pet_reaction, sleep, wake and walk clips.

## Evidence boundaries

The review and manifest distinguish source rendering, independent GLB import,
sampled animation behavior, browser loading and human identity acceptance.
Full-mesh finite-vertex tests and loop endpoint equality do not prove collision-
free movement, biomechanical gait or physical foot contact. These remain gentle
presentation gestures. Exact 1:1 likeness is not claimed.

The default application stays 2D. High-poly rendering remains opt-in, with
reduced-motion and error fallbacks. Representative mobile performance and human
likeness approval are separate acceptance gates. No paid provider, deployment,
authentication change or Git push is part of this local revision.

This is a local hash-checked handoff, not a canonical game-dev CLI receipt;
the CLI is not installed on this workstation. Source artwork remains project-
controlled under the repository's existing UNLICENSED policy.
