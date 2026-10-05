# Starfriends 0.10.1

Version: 1.0.0 | Updated: 2026-10-05 | Status: source verified; Linux and deployment gates pending

## Changes

Achievements have a dedicated authenticated `/{locale}/achievements` page in
German, English, French and Spanish. The shared navigation and language selector
preserve this route. Account recognition and the active companion's progress are
always visible in separate sections; the companion is named and a care link
allows returning to care or choosing another companion.

Cards use the existing dark surfaces, readable text and azure/gold progress
colors. Earned and pending states retain explicit text and labelled progress
bars. The care screen retains its polite unlock notices.

## Data and rollout

This patch changes no schema, migration, award rule, owner check or care behavior.
It requires the already-applied 0.10.0 achievement schema. Use the same verified
Linux artifact on both nodes and activate sequentially from 0.10.0, checking
readiness after each switch. Keep the immutable 0.10.0 artifact for application
rollback; no database restoration or migration replay belongs to this patch.

## Verification

Windows frozen installation, 410 tests (398 passed, 12 platform skips),
Prisma/TypeScript and production build passed with pnpm 11.19.0. Focused tests
cover anonymous access, onboarding without implicit adoption,
actor-scoped active-companion reads, internal shared-user warnings, four-language
navigation and accessible expanded collections. A synthetic browser preview
of the actual React components passed desktop and 390px/320px layouts in all
four languages, with card text contrast 17.42:1 and description contrast 9.12:1.
Linux checks and production activation are tracked in
[project status](PROJECT-STATUS.md). Authenticated user acceptance remains open.
