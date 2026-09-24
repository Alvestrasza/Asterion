# Progression and companion needs — candidate v1

This is source behavior for issue #6, not a deployed release or a claim of
real-user acceptance. Player and pet levels are separate, each starting at 1
and capped at 99. A player caring for multiple companions will accumulate
account XP across them; each companion receives XP only when cared for.
Companion slots are **not** unlocked by this change; that remains issue #7.

## XP curve

`PROGRESSION_VERSION = 1` freezes the 98-entry `XP_REQUIRED_V1` table in
`lib/care-engine.ts`. For transition from level `L` to `L+1`, where `1 ≤ L < 99`:

`40 + 18 × (L − 1) + floor(max(0, L − 10)² / 3)` XP.

| Level reached | Total XP from level 1 | Minimum days at 160 XP/day |
| ---: | ---: | ---: |
| 5 | 268 | 1.68 |
| 10 | 1,008 | 6.30 |
| 15 | 2,207 | 13.79 |
| 30 | 9,287 | 58.04 |
| 45 | 23,342 | 145.89 |
| 60 | 46,622 | 291.39 |
| 99 | 166,469 | 1,040.43 |

The minimum is a ceiling on reward throughput, not a promise that a player
must log in every day. A deterministic three-session varied-care simulation
tests level 5 within two days and level 10 after roughly a week. Additional
casual, intensive, and absent-player simulations cover slower care, saturation,
and return after a break. Absence and sleep produce no passive XP. Future balancing must version the table and
provide an explicit progress migration; never silently re-interpret saved XP.

## Care and anti-farming

- Feeding, playing and petting while asleep are refused with no state or XP gain.
- Sleep/wake transitions and duplicate transitions grant no XP.
- Feeding an already full pet is refused. A pet can still enjoy a play session
  or affection at high joy, but receives no XP when neither joy nor bond can
  improve. Otherwise, each action type is rewardable at most once every three
  hours.
- Eligible rewards are feed 15, play 25 and pet 16 XP. One account can receive
  at most 160 XP per UTC calendar day, across pets and web nodes. A partial
  final reward may fill the remaining daily budget.
- The server awards XP only inside the pet mutation transaction. The browser
  may display an offline action optimistically but does not predict its XP.
  Replayed request IDs return the original result without a second award.
- Existing per-minute command limits remain in force. These limits complement
  but do not replace the progression budget.

Needs now decay while awake by 1.35 satiety, 0.45 energy and 0.4 joy per hour.
Sleep restores 9 energy per hour while satiety and joy decay by 0.75 and 0.1.
Play costs 4 energy and 2 satiety. Time advancement remains server-authoritative
and bounded by the existing maximum offline interval.

## Data and rollout boundary

Migration `20260924060000_add_dual_progression` adds an account-progress row,
daily reward bookkeeping, and an audited XP amount on pet events. Existing
users' account level/XP is initialized from their current pet. Existing pet
levels beyond 99 are archived in `preCapLevel` and `preCapXp` before capping;
those columns are not used for gameplay but must be retained for recovery.

Do not apply this migration to an active public release. Before any rollout,
verify the exact database and writable primary, take and read back a fresh
backup, quiesce old pet writes, review the additive SQL and backfill, run the
owner migration once, verify role privileges, build a Linux artifact and
perform a guarded application activation. Then accept with two accounts on
both web nodes: existing progress, varied care, sleep/no-XP, retry idempotency,
day boundary, friend-visible account level, and rollback. None of those
production steps is established by a local build.
