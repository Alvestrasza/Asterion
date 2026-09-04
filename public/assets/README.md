# Asterion visual assets

The animation files and sprite atlas in this directory are the approved Asterion v2 companion artwork. The application reuses the existing identity and state animations rather than generating a second visual interpretation.

Runtime state mapping:

| App behavior | Animation asset |
| --- | --- |
| Calm or sleeping | `idle.gif` |
| Feeding and focused attention | `review.gif` |
| Playing | `jumping.gif` |
| Greeting and high wellbeing | `waving.gif` |
| Hungry or requesting attention | `waiting.gif` |
| Very tired | `failed.gif` |

`spritesheet.webp` is also used to provide a non-animated frame when the operating system requests reduced motion.

The `companions/` directory contains the selectable full-body portraits used by the web Tamagotchi. Asterion uses the validated animation set above; the additional companions use their transparent portrait together with the interface's state-specific reaction motion.
