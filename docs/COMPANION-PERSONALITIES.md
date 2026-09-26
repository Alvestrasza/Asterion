# Companion personalities and speech

Version: 1.0.0-draft | Scope: issue #8 | Status: draft source

## Editorial direction

The owner approved the issue's suggested character directions and accepted the first four-language editorial draft on 2026-09-26. Wording may still change during review.

| Companion | Voice | Care tendency |
| --- | --- | --- |
| Asterion | Calm, protective | Existing v0.9.0 baseline retained |
| Liora | Gentle, curious | Enjoys touch; a little more hungry while awake |
| Nyra | Independent, observant | Enjoys play more than touch |
| Brumo | Kind, enthusiastic | Strong appetite and a generous response to food |
| Caelo | Adventurous | Spends more energy and responds well to play |
| Selya | Playful | Enjoys play; benefits from light, frequent contact |
| Fenn | Loyal, sociable | Responds warmly to touch and play |
| Aelira | Patient, nature-loving | Needs change more slowly; enjoys gentle contact |

The numerical source of truth is `COMPANIONS[*].care` at `CARE_PROFILE_VERSION = 1`. Awake satiety decay ranges from 1.15 to 1.60 points/hour, energy decay from 0.38 to 0.60, and joy decay from 0.28 to 0.60. Sleep restores 8.5–10 energy points/hour. Feed restores 20–25 satiety points, play 10–18 joy points, and petting adds 2.2–3.5 bond points. Asterion retains the previously shipped values. XP candidates, levels, slot unlocks and reward budgets do not depend on species.

There is no random per-instance personality modifier in v1. Public accounts can adopt a given kind only once. Stable kind-level behavior keeps saved state, offline replay and cross-device observations predictable. Any later variation needs its own persisted version and migration policy.

## Versioned text contract

`SPEECH_VERSION = 1` uses keys of the form `v1.<kind>.<context>.<variant>`. The content matrix covers greeting, hunger, tiredness, joy, loneliness, feeding, play, petting, rest/no-op, satisfaction, sleep, wake, return after absence, companion level-up, achievements, adoption and already-awake feedback for all eight kinds in German, English, French and Spanish. Each cell has two alternatives. The primary line expresses the companion voice where appropriate; the alternate is a calm, localized context line. A stable seed selects an alternative, and consecutive identical keys alternate in the durable event stream. Retries return the original event and text for the requested locale.

New `PetEvent` rows keep the v1 key and typed level parameters alongside a German compatibility fallback. The additive migration leaves previous rows untouched. Rows without a valid key display their stored German text, marked as German for assistive technology. Locale changes rerender keyed history; they never change timestamps, XP, or stored event identity. Personal diary content is neither read nor used to choose speech. No AI text provider is involved.

The UI announces speech politely, uses translated companion species/image descriptions and mood labels, and retains the existing 2D fallback. Presentation animation IDs continue through the separate 3D contract. A tired but awake Asterion uses the idle clip; only a sleeping state uses the sleep clip. Reduced-motion presentation follows the existing CSS and still-art behavior.

## Care and release boundaries

Need changes use elapsed server time, capped at the established 14-day offline window. A long absence can make a companion hungry or tired; it cannot kill, retire or irreversibly harm one. A return greeting appears after at least six hours since the active pet's last advancement. Unselected companions are projected on collection reads without writing their state; selection or care persists their catch-up through the existing owner-bound transaction.

The broader care screen still contains German controls while localization issue #5 remains open. This slice localizes companion speech, history, species/image descriptions and mood labels, and marks legacy German content accurately. Achievement text is prepared for issue #9; achievements are not emitted here.

The schema change is additive. Deploy it before the new app code after a reviewed backup and migration gate. The currently deployed application can continue reading the expanded table; do not drop the new columns as an application rollback. No production migration or activation follows from this source candidate. Real two-account, both-node and cross-device acceptance remain separate checks.
