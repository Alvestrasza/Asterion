# Achievements and automatic rest — catalog v1

Version: 1.3.0 | Updated: 2026-10-05 | Status: 0.10.1 active; authenticated functional acceptance open

Issue [#9](https://github.com/Alvestrasza/Asterion/issues/9) introduces permanent,
private account and companion recognition. The initial authored catalog is a
first implementation draft. `ACHIEVEMENT_VERSION = 1` fixes its identifiers,
scopes and thresholds. Names, explanations and restrained feedback are
available in German, English, French and Spanish, with English fallback.

## Catalog

| Stable identifier | Scope | Evidence and target |
| --- | --- | --- |
| `v1.first-adoption` | Account | One adopted companion |
| `v1.companion-family` | Account | Two distinct adopted kinds |
| `v1.constellation` | Account | Five distinct adopted kinds |
| `v1.player-level-five` | Account | Player level 5 |
| `v1.first-care` | Companion | One accepted, XP-rewarded care action |
| `v1.varied-care` | Companion | Accepted, XP-rewarded feed, play and pet actions |
| `v1.pet-level-five` | Companion | Companion level 5 |
| `v1.healthy-bond` | Companion | Seven distinct qualifying UTC days |

A qualifying bond day contains accepted, XP-rewarded care whose resulting
awake state has at least 50 satiety, energy and joy, and 45 bond. Multiple
actions on the same day count once. The days need not be consecutive; breaks
never erase progress. No diary content or writing metric contributes.

`ACHIEVEMENT_XP_REWARD = 0`: v1 awards recognition only. Existing care XP,
cooldowns and the account-wide daily budget keep their current semantics.
Future XP bonuses require a separately versioned, transaction-bound ledger
and reward budget decision; they must not feed back into their own triggers.

## Persistence, ownership and replay

`AchievementProgress` is unique by owner, scope key and catalog ID. Account
scope has no pet; companion scope uses the stable pet ID. Composite foreign
keys bind every pet record to its actual owner. Progress is monotonic and
earned timestamps are retained. `AchievementCareDay` has one row per pet and
UTC date, with a care-type bitmask and a qualifying-health flag.

Adoption and new care events update these records within the existing
serializable pet transaction. Care requires `accepted=true` and positive
authoritative `xpAwarded`; no-op care, sleep, wake and client predictions do
not count. A replay returns the original feedback, a fresh current pet
snapshot and no new unlock notifications. Transaction aborts roll back both
care and recognition; normal unique/serialization retries remain bounded.

The authenticated pet snapshot carries account and selected-companion
achievements. The existing actor/ownership/access checks and private,
no-store response remain in force. There is no public achievement feed or
friend-profile disclosure. The 0.10.1 correction moves the collection to its
own authenticated localized achievements page with a shared navigation entry.
Account and named active-companion sections show earned/locked text and labelled
progress on dark theme surfaces. Icons are decorative and status does not depend
on color. New care unlocks retain a polite, temporary status
announcement. Offline care waits for server confirmation to earn recognition.

## Existing data, resets and imports

The atomic additive migration recognizes existing distinct adoptions and
stored account/pet levels. Retained accepted care events with positive XP
prove first care, varied care and care dates. Rejected, zero-XP and mismatched
owner events are excluded. Historical healthy state is not known, so no
healthy days are fabricated. Legacy recognition uses the migration timestamp,
not an invented historical unlock time. No old care event or XP is rewritten.

Public restore, reset and kind replacement remain forbidden. Internal test
reset/restore/select commands do not themselves trigger or clear achievements;
later real, accepted care can advance permanent recognition. Test imports are
not a way to import achievement records, bonus XP or qualifying days into
PROD. Account deletion cascades recognition records with the account; hiding
or switching a companion does not reset them.

## Automatic rest and controls

The shared care engine starts sleep at zero energy, including an already
exhausted stored state. Elapsed time is split at that exact threshold: awake
decay first, then sleep recovery and gentler sleep decay for the remainder.
Sleep persists until an explicit wake action; waking at exactly zero energy
is refused until some energy has recovered. Automatic rest grants no XP and
adds no artificial user interaction. All eight kind-specific rates apply.

This is the existing lazy server-time model: reads and commands materialize
elapsed time, rather than a background task modifying every pet. Inactive
collection summaries project the same sleeping state without writing it.
An open, visible care page refreshes the server snapshot every 30 seconds and
on focus, while preserving pending actions. Feed, play and pet buttons use
native `disabled` while sleeping; the handler also blocks accidental calls,
and direct API commands retain authoritative rejection. Wake remains available.

## Verification and rollout boundary

Tests execute the migration and achievement persistence against isolated
PGlite PostgreSQL with synthetic data. They cover proven legacy backfill,
atomic failure, owner foreign keys, repeated calls, rollback, locale continuity
and nonconsecutive healthy days. Actual React markup verifies the controls
and accessible collection. Existing pet-service tests exercise real award
hooks and suppression during command replay. A controlled effect/network test
also verifies that an older refresh cannot overwrite a newer sleeping/waking
presentation, and that a cancelled refresh cannot update the care view.

The final local Windows set passed frozen-lockfile installation, 408 tests
(396 passed, 12 platform-dependent skips), Prisma/TypeScript checking and the
production build using Node 24.19.0 and the pinned pnpm 11.19.0.

PGlite uses one connection and a transport adapter; this is not proof of
Prisma wire transport, multi-node PostgreSQL serialization or PROD acceptance.
Windows tests/check/build, Linux CI, target Linux build, owner migration,
both-node readiness and authenticated gameplay are separate evidence gates.

Before migration, take/read a fresh exact-target backup and stop old care and
adoption writers. Keep writes quiescent through the evidence backfill and
activation on both nodes: the predecessor app can run on the expanded schema,
but it cannot maintain the new recognition ledger. Verify new-table DML
privileges for the application role. Retain the previous immutable artifact
and test guarded activation/replay on both nodes with two accounts.

Application rollback retains the additive tables and earned records; it does
not undo committed data. Before later forward activation after old-app writes,
review a care-event catch-up using only provable facts, with no fabricated
healthy days. Do not drop recognition tables or restore a backup automatically.

Current release evidence: exact-head Linux CI and the target Linux x86_64
artifact both passed all 408 tests, Prisma/TypeScript and production build.
The operator reported successful migration and the artifact was activated on
both public nodes on 2026-10-05, with database readiness and public availability
verified. The 0.10.1 separate-page/theme correction then passed Windows
validation, all 410 Linux CI/target tests and both production-node readiness
checks. The schema and award rules are unchanged. Authenticated functional
acceptance remains open. See [project status](PROJECT-STATUS.md).
