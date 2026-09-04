# Asterion 3D asset pipeline

## Goal

Create lightweight, expressive, rigged 3D companions for the web application without losing the approved storybook identity of the 2D artwork. Blender source files are the editable authority; optimized glTF Binary files are delivery artifacts.

The first prototype should be Asterion. The existing 2D implementation remains the production fallback until the prototype passes every acceptance check in this document.

## Asset layout

Create the directories only when the first asset is ready:

```text
assets/3d/reference/<companion>/   approved turnarounds and color references
assets/3d/source/<companion>/      Blender source and linked source textures
public/assets/3d/<companion>/      optimized browser-ready GLB and textures
```

Large `.blend`, `.glb`, and `.fbx` files should use Git LFS. Do not commit Blender autosaves, render caches, simulation caches, or redundant exports.

## Production stages

### 1. Identity reference

Build an approved character sheet containing front, side, rear, and three-quarter views. Record the non-negotiable silhouette, proportions, palette, face, horns or ears, clothing or armor, and characteristic markings.

Generated reference art is exploratory until visually approved. Do not silently replace the canonical companion design.

### 2. Blockout

Model primary volumes at neutral pose and real scene scale. Validate the silhouette from the intended web-camera distance before adding surface detail.

For Asterion, validate these features first:

- compact quadruped proportions
- large expressive head and blue eyes
- layered gold horns and crest
- dark blue body with gold armor language
- pale mane and tail tuft
- readable paws and silhouette at small display sizes

### 3. Retopology and UVs

Use animation-friendly edge flow around shoulders, hips, mouth, eyelids, tail, and horn bases. Prefer a compact mobile-ready mesh over sculpt-level density.

Initial performance targets:

- 10,000 to 30,000 rendered triangles per companion
- one primary 1K or 2K texture set
- as few materials and draw calls as the design permits
- no hidden geometry that cannot affect the final presentation

These are starting budgets, not excuses to damage the silhouette. Measure on representative mobile hardware before raising them.

### 4. Materials and textures

Use a stylized physically based material with painted color variation. Bake reusable detail instead of shipping heavy procedural node graphs. Keep transparent materials exceptional because they increase sorting and overdraw costs in browsers.

### 5. Rigging

Use one deforming armature per companion, clean normalized weights, and stable bone names. Apply transforms before export and keep non-deforming control bones out of the exported deformation set when possible.

Minimum animation clips:

- `idle`
- `blink`
- `happy`
- `eat`
- `play`
- `pet_reaction`
- `sleep`
- `wake`
- `walk`

Loops must be seamless where appropriate. The first and last frame should not produce a visible pause or root jump.

### 6. GLB export

Export one self-contained `.glb` per companion prototype with:

- only required meshes, armature, materials, and animation clips
- applied coordinate and scale conventions
- embedded or deliberately colocated optimized textures
- no cameras, lights, helpers, or editor-only collections
- deterministic, lowercase asset names

Record the Blender version and export settings in the asset's review note. Re-export from the `.blend` source rather than editing generated GLB files manually.

### 7. Web integration

Load 3D only in the client and only when needed. Preserve:

- the current 2D fallback
- useful alternative text and non-visual status feedback
- `prefers-reduced-motion` behavior
- lazy loading and a visible loading state
- cleanup of WebGL resources when changing companions
- graceful fallback when WebGL or the asset fails

The server-authoritative care model does not need to change. Existing mood and action results should select animation clips without moving companion state into the browser.

## Acceptance checks

### Visual identity

- The companion is immediately recognizable beside the approved 2D reference.
- Silhouette, palette, eyes, face, and signature features remain consistent.
- No chroma fringe, texture seams, inverted normals, or unintended transparency is visible.

### Animation

- All required clips exist under stable names.
- Limbs, face, mane, tail, armor, and clothing deform without obvious collapse.
- Loops do not jump and one-shot actions return cleanly to idle.
- Reduced-motion mode can present a still or substantially calmer alternative.

### Technical

- The asset loads as GLB without console errors.
- Materials and animation clips survive a clean export and fresh browser load.
- File size, triangle count, texture memory, draw calls, and load time are recorded.
- Desktop and representative mobile browsers retain an acceptable frame rate.
- A missing or corrupt model falls back to the 2D companion.

### Repository and release

- Source and export are traceable to one reviewed commit.
- Binary assets use the agreed LFS policy.
- Tests, type checks, and production build still pass.
- Deployment uses the same immutable application artifact on both web nodes.

## Recommended first milestone

Build an Asterion vertical slice containing the approved neutral model, textures, rig, `idle`, `blink`, `happy`, and `sleep`. Integrate it behind a local development flag while retaining the 2D default. Expand to the full animation set only after identity and mobile performance are accepted.
