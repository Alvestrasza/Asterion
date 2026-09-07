# Metadata-only publication amendment: 2026-09-07

This directory records publication copies, not a new sculpting, rendering or animation round. The change map binds 293 binary files (45 Blender sources, 246 PNG images and 2 historical GLBs), 82 amended JSON documents and 79 exact public-safe authoring archives.

## Authoring evidence and publication bindings

The original authoring documents describe the bytes actually used and measured during the historical builds. Their original file digests are preserved in byte-identical archives, including their original line endings. They must not be interpreted as manifests for the newly cleaned distribution files.

The canonical amended documents explicitly identify themselves as publication derivatives. File SHA-256 and file-size fields, including input_sha256 entries, now bind the publication copies; they do not claim that the old builder opened those cleaned bytes. Each document links its original authoring hash and archive status to [amendment.json](amendment.json). The amendment lists every changed JSON pointer with its original and current binding. Geometry, material, rig, action, motion, acceptance flags and measured counts are preserved. Original numeric tokens, including signed zero, exponent notation and large integers, are retained exactly. A separate conservation digest checks all remaining evidence.

## Omitted private originals

3 legacy canonical-highpoly authoring receipts contained workstation paths. Their exact originals remain privately retained and are authenticated by the original document digests; they are deliberately not included in the public authoring archive. The amendment records each path-redaction pointer and the original value digest without exposing the removed value. Existing repository files use relative paths; unpublished authoring outputs are explicitly null, not invented public artifacts.

## Verification and limits

The eight current runtime GLBs remain byte-identical. PNG proofs bind unchanged rendering chunks and independently decoded RGBA pixels. Legacy GLB proofs cover unchanged non-JSON chunks and unchanged semantic JSON outside the approved metadata fields. Blender proofs bind original, in-memory and reopened data equivalence. A separate byte-only step zeroes only unused bytes after the first NUL in the two exact SDNA metadata buffers, FileSelectParams.dir[1282] and RenderData.pic[1024]. Live strings and all other decompressed bytes remain identical. That byte-only step truthfully records no Blender reopen; a subsequent read-only Blender reopen, independent byte-delta check and full raw privacy scan each bind the final file hash. Raw RNA-only intermediate copies are not publication artifacts. Source sanitizer receipts and frozen verification tools are digest-bound separately.

The dependency order is binary copies, reports and validations, asset manifests, gallery manifests, then the amendment index. Documents refer to the stable amendment identifier/path rather than its final digest, avoiding a hash cycle. The clean-clone verifier checks published file bytes, exact original archives, allowed pointer changes, conserved evidence and runtime GLBs. No private files are required for that verifier.

This record does not assert a commit, push, deployment, fresh historical Blender test run, game-dev canonical package, mobile performance acceptance or 100-percent visual likeness. The current 2D fallback and existing acceptance limits remain unchanged.
