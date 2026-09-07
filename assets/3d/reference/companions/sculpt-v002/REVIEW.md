# Remaining companions — v002 handoff review

All five remaining reference refinements are locally delivered and selected by
the opt-in runtime mapping. Caelo and Liora retain their delivered v002 files;
Asterion retains its accepted sculpt-v001. Every original portrait and historical
v001 master/export is preserved. No commit, push or deployment was performed.

## Figure evidence

| Figure | Imported triangles | GLB bytes | Materials | Review |
| --- | ---: | ---: | ---: | --- |
| Nyra | 1,367,847 | 16,469,864 | 13 | [Cat](../../cat/sculpt-v002/REVIEW.md) |
| Brumo | 1,289,652 | 13,669,416 | 21 | [Orc](../../orc/sculpt-v002/REVIEW.md) |
| Selya | 1,426,998 | 15,148,892 | 19 | [Fairy](../../fairy/sculpt-v002/REVIEW.md) |
| Fenn | 1,325,462 | 15,841,868 | 11 | [Dog](../../dog/sculpt-v002/REVIEW.md) |
| Aelira | 1,519,337 | 15,901,816 | 24 | [Elf](../../elf/sculpt-v002/REVIEW.md) |

Each has one self-contained Meshopt mesh/skin, nine clips and separately editable
Blender source parts. Portrait authority, sculpt changes, remaining artistic
differences, master/export/builder hashes, four source views, three independent
import views and six motion frames are documented per figure. All 19 import
checks passed for each delivery. All sampled vertices were finite, and idle,
sleep and walk endpoint displacement was 0.0 within 0.0001 scene units.

The [gallery](companions-gallery.png) imports the actual five final GLBs into
one neutral studio scene. It was rendered with Blender 5.2.1 LTS at 3200×1000,
64 samples and visually inspected. Model display heights are normalized; labels
and the studio floor are scene objects, not composited reference pictures.
The [aggregate manifest](collection-manifest.json) points to the exact deliveries.

## Fresh software and browser checks

- `pnpm test`: 35 tests passed, including all seven v002 GLB contracts,
  manifest/builder hashes, import/motion bindings and preservation of earlier
  source/export/reference files.
- `pnpm check`: Prisma client generation and TypeScript checks passed.
- `pnpm build`: the Windows standalone production artifact built successfully.
  Each of the five GLBs in its public tree matches its delivery SHA-256.
- `python assets/3d/source/companions/sculpt-v002/test_delivery.py`: 11 tests
  passed, including preflight conflicts, changed master/build hashes, protected
  generated metadata, concurrent changes and late-write rollback. These fixture
  tests exercise delivery safety, not Blender geometry validity.
- The restarted local `/3d-preview` loaded all five new models. Each pet's four
  fixed views and nine clip buttons retained `ready` with one canvas. All five
  hero views were visually inspected in the app browser; figures fit the narrow
  viewport without cutting off the silhouette.
- Reduced Motion was enabled and disabled for each pet. Every fallback had zero
  canvases and its complete original 1254-pixel-wide portrait. Bringing the model
  panel back into view restored `ready` and one canvas.
- The inspected preview browser warning/error log was empty after the checks.
  This verifies selection/control handling, not exhaustive animation playback.

The game-dev and agent-browser CLIs were unavailable. Blender CLI scripts and
the app's browser automation supplied the recorded evidence; no canonical CLI
receipt, external generation service or new dependency is claimed.

## Acceptance boundaries

These are reference-led stylized reconstructions, not exact 1:1 copies or final
human likeness approval. Single-view hidden surfaces remain inferred. The
high-poly budget is intentional: roughly 1.3–1.5 million triangles per figure,
with an explicit 1.6-million ceiling for Aelira's folded embroidered costume.
It does not establish acceptable mobile frame rate or memory use.

Motion checks do not prove every frame/transition, collision-free cloth, ground
contact or biomechanical gait. The narrow desktop app viewport is not a test on
representative mobile hardware. The 2D default and fallback remain enabled;
3D stays opt-in. The existing local authentication-secret configuration gap is
outside this asset change; authenticated gameplay, database-backed readiness,
Linux artifacts and production deployment were not accepted by these checks.
