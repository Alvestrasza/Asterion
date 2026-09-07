# Metadata-only publication tooling

These tools implement the explicitly authorized 2026-09-07 publication of the
existing collection. They do not generate models, reauthor animations, re-render
previews, deploy the website, or invoke a paid service. This is not a Game-Dev-CLI
canonical package or a new licensing decision.

## Dependency order

1. `snapshot.mjs` copies the pre-publication prospective Git files to a new
   ignored mirror, verifies exact bytes, and records the original hashes.
2. `sanitize_media.mjs` produces new PNG/legacy GLB copies. It removes only
   audited PNG `File` text and explicitly allowed legacy scene-extra values.
   Pixel-bearing chunks and GLB binary data remain unchanged. Additional
   independent decoded-pixel and privacy checks are required.
3. `sanitize_blender.py`, run by Blender with automatic scripts disabled,
   produces separate editable copies. It compares stored asset semantics before
   cleanup, after cleanup and after reopening. Unchanged external image
   dependencies may be mirrored solely for this reopen check.
4. `clean_blend_tails.mjs` removes residual bytes after the first NUL in the
   specifically allowlisted file-browser and render-output C-string buffers,
   using each file's embedded SDNA layout. All other decompressed bytes must
   remain identical. `verify_final_blender.py` then reopens the final copies
   read-only and checks the complete stored-data fingerprint again. Audit the
   whole decompressed file, not only the path strings exposed by Blender.
5. `rebind.mjs` creates a separate receipt candidate mirror in dependency order.
   It preserves original safe receipts byte-for-byte, discloses omitted unsafe
   originals, and records every new file hash or metadata redaction. Measured
   geometry, materials, rig, action and acceptance evidence remains historical.
6. `promote.mjs` defaults to a read-only preflight. An explicit `--apply` promotes
   reviewed asset copies only when the private snapshot, live sources and
   candidates still match. Originals remain in the private mirror. It refuses
   unbacked replacement files, changed candidates, links and unrelated paths.
7. Run the full repository validation, independently audit the exact prospective
   Git/LFS bytes, then commit and push only with publication authorization.

The sanitizer allowlists and dated publication identifier are intentionally
specific to this migration. Do not silently widen them for another collection
or publication. Never upload private candidate mirrors, raw logs, personal
memory, or the original unsafe metadata.

Promotion is atomic per file, not across the whole batch. If an I/O failure
interrupts it, retain the private originals and inspect the partial overlay
before recovery; the ordinary preflight deliberately rejects a blind retry
against already changed working files.

## Verification

The Node publication tests are part of `pnpm test`. The synthetic Blender guards
do not open production inputs. Their serialization check saves and reopens a
fresh ignored fixture under the private publication review directory:

```powershell
$blender = '<path-to-blender-executable>'
& $blender --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/asset-publication/test_sanitize_blender.py
```

The final-receipt/path guards are ordinary Python tests and do not load Blender
or production inputs:

```powershell
$python = '<path-to-python-3-executable>'
& $python scripts/asset-publication/test_verify_final_blender.py
```

The guards deliberately alter representative mesh, attribute, material, rig,
binding, animation, curve, shape-key and image data to demonstrate detection.
UI caches and explicitly listed path-only metadata are not asset semantics.
Keep hash-bound tools and asset JSON/Python files byte-preserved according to
`.gitattributes`; historical authoring archives are not live distribution manifests.

See the [publication amendment](../../assets/3d/publication/2026-09-07/README.md)
for the actual migration scope, measured proofs and remaining acceptance limits.
