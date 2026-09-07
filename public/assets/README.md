# Asterion visual assets

The animation files and sprite atlas in this directory are the approved Asterion v2 companion artwork. The application reuses the existing identity and state animations rather than generating a second visual interpretation.

Runtime state mapping:

| App behavior | Animation asset |
| --- | --- |
| Calm or sleeping | `idle.gif` |
| Feeding and focused attention | `review.gif` |
| Playing | `jumping.gif` |
| Greeting and high wellbeing | `waving.gif` |
| Hungry or requesting attention | `waiting.gif` |
| Very tired | `failed.gif` |

`spritesheet.webp` is also used to provide a non-animated frame when the operating system requests reduced motion.

The `companions/` directory contains the selectable full-body portraits used by the web Tamagotchi. Asterion uses the validated animation set above; the additional companions use their transparent portrait together with the interface's state-specific reaction motion.

`3d/asterion/asterion-sculpt-v006.glb` is the current feature-flagged model with face-only edits to eyes, orbital transitions, cheeks, nose and mouth. The Blender master and reproducible source live under `assets/3d/source/asterion/sculpt-v006/`. Separate body/armor meshes share one 22-bone skin and nine unchanged clips. Equipment is identified by explicit node extras, not colors or material names. Head hair remains omitted; body, crown, ears, outfit and static native tail groom are unchanged from v005. Use the v006 manifest and validation report for exact counts and provenance. All historical masters/exports, including v005 and the complete approximately five-million-triangle v002, remain unchanged.

`NEXT_PUBLIC_ASTERION_3D_ENABLED` remains off by default. The existing animation and portrait assets remain the loading, failure, unsupported-WebGL, and reduced-motion fallback. Representative mobile-performance acceptance is outstanding, and no exact 1:1 likeness is claimed.

The seven other selectable pets now use `3d/<kind>/<kind>-sculpt-v005.glb`:
`rabbit`, `cat`, `orc`, `pony`, `fairy`, `dog`, and `elf`. Each is a real
volumetric figure with nine unchanged presentation clips and separate body/outfit
meshes on the original shared skeleton. Sources and provenance are described in
`assets/3d/source/companions/sculpt-v005/README.md`. This round modifies only
faces; nonfacial geometry/materials and original animation data remain exact.
Every earlier v001/v002/v003/v004 file
is retained. Natural markings, wings and opaque base clothing stay on the body.
The opt-in `/3d-preview` includes all eight names. Unshown reference views are
interpreted; mobile performance and human likeness acceptance remain pending.

`asterion-canonical-highpoly-v001.glb` is the historical, user-rejected reconstruction of the old portrait as a relief shell. It is not the current 3D design authority. `asterion-highpoly-v001.glb` and `asterion.glb` are also retained only as superseded comparison checkpoints.
