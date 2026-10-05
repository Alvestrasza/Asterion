# Starfriends 0.10.0

Version: 1.2.0 | Updated: 2026-10-05 | Status: production active; functional acceptance open

## Changes

Eight private account and companion achievements recognize adoption, levels,
rewarded care variety and seven qualifying UTC care days. The four-language
collection retains progress and earned timestamps across sessions and devices.
The first catalog awards recognition with no extra XP. See the stable
[achievement contract](ACHIEVEMENTS.md).

Feeding, playing and petting are disabled while the companion sleeps. Zero
energy starts sleep automatically; elapsed time switches from awake decay to
sleep recovery at exhaustion. Sleep continues until an explicit wake command.
An open, visible care page refreshes authoritative state every 30 seconds and on
focus, preserving queued actions and rejecting obsolete responses.

This version also retains the accepted permanent companion collection,
individual care profiles and authored companion voices from issues #7 and #8.
The existing approved artwork, ownership checks and XP budget are preserved.

## Deployment

The additive achievement migration must run after a fresh verified backup with
old care/adoption writers stopped. Keep both old web nodes quiescent until the
backfill is verified and the new version is activated on both nodes. Verify
application DML privileges on both new tables. The previous application cannot
maintain the recognition ledger even though the expanded schema is compatible.

Application rollback retains additive tables and earned records. A later forward
activation after old-app writes requires a reviewed catch-up using provable
events; historical healthy days cannot be reconstructed. No automated schema
drop or backup restoration is part of application rollback.

## Verification and acceptance

Required gates are frozen dependency installation, tests, Prisma/TypeScript
checks, production build, exact-head Linux CI and a verified artifact built on
the target Linux architecture. The isolated SQL tests use PGlite and a transport
adapter; actual Prisma transport and cross-node behavior require runtime checks.

After migration and activation, verify both-node readiness, action persistence,
cross-node continuity, replay without duplicate awards and two-account isolation.
Confirm sleep controls, automatic rest, earned/locked presentation and language
changes in a real authenticated session. Availability and functional acceptance
remain separate. Current dated evidence is recorded in
[project status](PROJECT-STATUS.md).

## Verified staging — 2026-10-01

PR #19 is merged. Exact-head Linux CI and the target Linux x86_64 build each
passed all 408 tests, Prisma/TypeScript and production build. The identical
verified artifact is installed inactive with preflight passed on both public
nodes. Existing production remains on the accepted issue #8 application.
Fresh owner backup, SQL migration, activation and authenticated acceptance are
pending; no later evidence level is implied by source or artifact verification.

## Production activation — 2026-10-05

The operator reports a successful fresh backup and single reviewed migration,
with all twelve migration checksums, preserved legacy rows, evidence backfill,
constraints and application privileges verified. The immutable artifact was
then activated sequentially on both nodes and passed separate database-backed
readiness and public availability checks. Authenticated functional acceptance
remains open. The owner requested a dedicated achievements page and dark-mode
correction, tracked in the [0.10.1 follow-up](RELEASE-0.10.1.md).
