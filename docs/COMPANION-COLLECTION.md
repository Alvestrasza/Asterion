# Companion collection (issue #7)

## Product rules

- Every account begins with one companion slot. Account levels 15, 30, 45, and 60 unlock one additional slot each; the limit remains five through level 99.
- A companion kind may be adopted once per account. Adoption is permanent in this release; there is no public replacement, deletion, reset, or import path.
- Each companion has its own level, XP, needs, sleep state, and journal. The account has its own level and a single daily/cooldown reward budget shared across companions.
- Selection changes only the active companion pointer. Pending and retried care actions retain the original companion ID and request ID.

## Data migration and release gate

The additive `20260924170000_add_companion_collection` migration preserves existing pets and events, backfills the active companion pointer and unlocked slots, and adds database constraints for distinct kinds and account-wide request idempotency. Do not apply it while an older application version can write pet or event rows: old code does not supply the new non-null event owner field.

Before activation, verify the exact writable target and migration history, take and read back a fresh backup, stop all old writers on both nodes, and apply the reviewed migration once using the schema-owner role. Confirm existing pet/event counts and ownership, backfilled active pointers, new indexes/constraints, application privileges, and no failed migration. Build a Linux artifact from the same source and activate one node at a time. Keep the predecessor release and restore plan available. A successful local build is not database or production acceptance.

## Functional acceptance

Use two authorized accounts and both web nodes. Confirm first adoption remains idempotent; a second slot is denied below level 15 and available at 15; further slots unlock at 30/45/60 and never exceed five. Verify duplicate kinds and a sixth pet are rejected, each pet's state and journal remain independent, selection survives a new browser, and a queued/retried care command applies only to its original pet and earns account XP at most once. Confirm cross-account reads/actions are denied, public reset/replacement are rejected, and existing pets/history survive the migration.
