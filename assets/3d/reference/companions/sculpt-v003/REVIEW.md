# Modular companion collection review

This pass refines all seven additional companions and adds independently
removable outer outfits. Asterion v004, original portraits and every v001/v002
master/export remain unchanged. The figures are local high-poly desktop review
assets; neither exact likeness nor representative mobile performance is accepted.

## Asset-level evidence

Every current source folder has `manifest.json`; every current reference folder
has `validation.json`. These bind the actual Blender master, GLB, original
portrait, builder dependencies and review images by SHA-256.

| Figure | Authored triangles | Main change |
| --- | ---: | --- |
| Caelo | 1,203,008 | Scored sky-blue locks, shaded roots, rounded lower muzzle |
| Liora | 1,325,486 | Shorter/plumper cheek fans and directional cream relief |
| Nyra | 1,367,850 | Shortened cheek blades and less projecting lower face |
| Fenn | 1,325,472 | Plush ear/bib channels and surface-seated shorter smile |
| Brumo | 1,320,470 | Plum hair relief, separate outfit, opaque base clothing |
| Selya | 1,427,002 | Copper lock relief and curled outer-petal family |
| Aelira | 1,519,338 | Green hair/braid relief and coherent cape/edging folds |

The original ocular surfaces and blink covers are preserved. The shape edits
are recorded per source object, with measured displacement where applicable;
counts are not increased through indiscriminate subdivision.

Each figure has six source views (hero/front/side/rear and outfit-off hero/side)
and four independently imported views (hero/rear/outfit-off hero/blink).
Comparisons use the approved portrait, not newly generated reference artwork.

## Outfit boundary review

The exported body and outfit are two mesh nodes on one unchanged shared rig.
Every source mesh belongs to one component. The original nine animation actions
are compared exactly, including keys/handles, rest data, constraints and drivers.
Both old and new GLBs are freshly imported for nine normalized time samples per
clip, checked at a `2e-4` world skin-matrix tolerance.

- Natural fur, eyes, nose and markings remain on the body. Fenn's cream moons
  are not inferred to be equipment merely because they resemble ornaments.
- Brumo retains an opaque plum under-tunic and shorts. His plain collar rim is
  base-clothing trim; his forged/leather outer equipment is removable.
- Selya retains wings, mint/ivory dress layers and sandals. Coral outer petals,
  jewelry and their bezels are equipment. Visual review caught initially
  unclassified gemstone roots; both roots and bezels now share the outfit.
- Aelira retains her tunic, trousers and closed boots when the cape, belt,
  bracers, clasps and outer straps are hidden.

The preview toggle is local page state, independent per pet. It does not imply
an inventory, individually swappable slots, reward logic, new outfits or stored
user choices. Replacement outfits must match the species-specific rig contract.

## Local integration verification

Verified on 2026-09-05 after the final asset handoff:

- `pnpm install --frozen-lockfile`: exit 0, dependencies already current. The
  optional pnpm update-metadata request could not reach the registry; no package
  upgrade was attempted or required.
- `pnpm test`: 67 passed, 0 failed. This includes real Meshopt/Three.js decoding,
  outfit toggles on running animations, evidence hashes, historical asset
  preservation and the Selya gemstone-root regression.
- `python .../sculpt-v003/test_delivery.py --review <private-review>`: four
  read-only delivery-gate tests passed; no destination bytes changed.
- `pnpm check` and `pnpm build`: exit 0. The Windows local build is not Linux
  deployment acceptance.
- Browser `/3d-preview`: all eight models reached `ready`; all outfits switched
  between their full primitive count and zero visible equipment primitives.
  Counts were Caelo 7, Liora 11, Nyra 6, Fenn 3, Brumo 10, Selya 8, Aelira 8 and
  unchanged Asterion 9. No browser warnings/errors were recorded in this check.
- Selya's hidden outfit persisted while switching to visible Caelo and back.
  Reduced Motion used the loaded original `fairy.png`; returning the model to
  the viewport restored the hidden-outfit 3D view through existing lazy loading.
- Caelo's four fixed camera states were checked; sleep visibly closed the eyes,
  and idle restored the normal presentation. No animation code was changed.
- An additional visit to `/` reached the login page but reported Auth.js
  `MissingSecret`. The local authentication secret is not configured in this
  development launch. This is separate from `/3d-preview`; no credentials,
  authentication behavior or ownership checks were changed.

Blender emitted non-blocking thumbnail/extension-cache write warnings in the
restricted host environment. The actual masters were saved and reopened, all
ten required renders per pet were verified, and fresh GLB imports passed.
These checks do not exercise authentication, persistent care actions, databases,
multi-node behavior, production readiness or mobile performance.

## Remaining visual limits

This is an incremental sculpt refinement, not a new reconstruction of every
feature. The eyes and main anatomy retain the stylization of the accepted local
v002 baseline. Painterly strand highlights, coat transitions and some silhouette
proportions still differ from the illustrations. Higher triangle counts alone
would not resolve those differences. Unshown views are inferred.

Source/render validation does not establish collision-free cloth, accurate
foot contact, natural gait or mobile frame rates. Meshopt uses the existing
precision-reducing encoder; compression is not claimed to be lossless.

The [gallery](companions-gallery.jpg) assembles actual imported outfit/body
renders with independent framing. It is not a shared physical-scale chart.
Its inputs and hashes are recorded in `gallery-manifest.json`.

See the [production guide](../../../source/companions/sculpt-v003/README.md)
for reproduction, safe pre-handoff corrections and validation boundaries.
