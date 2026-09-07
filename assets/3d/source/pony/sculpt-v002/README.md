# Caelo — reference-led sculpt v002

This revision reworks Caelo first in the requested second pass over the pet
collection. The authoritative artwork is the unchanged
`public/assets/companions/pony.png`. It is not an approved multi-view turnaround;
hidden anatomy, mane and harness surfaces remain an interpretation.

The historical `sculpt-v001` master, export and review images are preserved.
Other pets retain their current versions until individually revised.

## Authored changes

- Continuous equine torso/limbs with blended skin weights; refined muzzle and
  smaller smile, cupped elongated ears and ivory fetlock feathering.
- Recessed blue eyes with modeled upper lashes, separate lower lids, eyebrow
  strokes, iris fibers and a closed-eye lash for blink/sleep.
- Independently editable flowing mane and tail volumes, with sculpted channels
  and exportable blue/periwinkle vertex-color variation.
- Broad chamfered gold tiara, stars, shaped blue shoulder/saddle armor,
  shield-shaped faceted breast crystal, fitted harness and diamond anklets.

These are actual volumetric meshes. No source portrait is projected onto a plane
or a relief shell. High polygon count is not itself evidence of likeness.

## Reproduction

Use Blender 5.2.1 LTS or a separately verified compatible runtime. The build uses
the unchanged Asterion geometry/export toolkit and companion presentation rig.
All review outputs must use new, absolute directories outside the source tree.

```text
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/pony/sculpt-v002/build.py -- --output /absolute/new/caelo-review --resolution 1600 --samples 64
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/companions/sculpt-v001/validate_collection.py -- --glb /absolute/new/caelo-review/pony-sculpt-v002.glb --output /absolute/new/caelo-review/validation --resolution 1200
blender --background --factory-startup --python-exit-code 1 --python assets/3d/source/pony/sculpt-v002/inspect_motion.py -- --glb /absolute/new/caelo-review/pony-sculpt-v002.glb --output /absolute/new/caelo-review/motion --resolution 800
python assets/3d/source/pony/sculpt-v002/deliver.py --input /absolute/new/caelo-review
```

`deliver.py` checks source/reference/export hashes, current builder hashes, four
principal renders, fresh-import evidence and sampled motion evidence. It refuses
to replace existing different output files. A pre-handoff correction may supply
`--previous /absolute/exact/previous-review`; replacement is then allowed only
when the destination still matches that preserved previous file byte for byte.
Already handed-off revisions should receive a new version.

The Blender file preserves separate editable objects. Export merges weighted
copies into one self-contained Meshopt-compressed mesh and retains nine clips:
idle, blink, happy, eat, play, pet_reaction, sleep, wake and walk.

## Evidence boundaries

The manifest and review reports record actual counts, hashes and check outcomes.
The motion inspection evaluates every mesh vertex at six selected frames and
compares all vertices at the endpoints of idle, sleep and walk. It does not prove
collision-free animation or physically correct foot contact. Clips remain gentle
presentation gestures rather than biomechanical gait simulation.

The default app remains 2D, including reduced-motion and error fallbacks. The
high-poly model is an opt-in review asset; human likeness approval, representative
mobile performance and production deployment are separate, unclaimed gates.
No paid provider was used. This is a local hash-checked delivery, not a canonical
game-dev CLI package receipt; that CLI was unavailable on the working machine.
