import type { CompanionKind } from "./companions";

// Keep the approved originals addressable; next/image serves responsive derivatives.
export const COMPANION_BACKGROUNDS: Record<CompanionKind, string> = {
  asterion: "/assets/backgrounds/asterion-background-v1.png",
  rabbit: "/assets/backgrounds/rabbit-background-v1.png",
  cat: "/assets/backgrounds/cat-background-v1.png",
  orc: "/assets/backgrounds/orc-background-v1.png",
  pony: "/assets/backgrounds/pony-background-v1.png",
  fairy: "/assets/backgrounds/fairy-background-v1.png",
  dog: "/assets/backgrounds/dog-background-v1.png",
  elf: "/assets/backgrounds/elf-background-v1.png"
};
