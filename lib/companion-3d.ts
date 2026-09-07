import type { CareAction } from "@/lib/care-engine";
import type { CompanionKind } from "@/lib/companions";

export const ASTERION_MODEL_ASSET = "/assets/3d/asterion/asterion-sculpt-v006.glb";

export const ASTERION_REQUIRED_CLIPS = [
  "blink",
  "eat",
  "happy",
  "idle",
  "pet_reaction",
  "play",
  "sleep",
  "wake",
  "walk"
] as const;

export type AsterionClip = (typeof ASTERION_REQUIRED_CLIPS)[number];

export function companion3DModelAsset(kind: CompanionKind) {
  return kind === "asterion" ? ASTERION_MODEL_ASSET : `/assets/3d/${kind}/${kind}-sculpt-v005.glb`;
}

export function asterionClipForCareAction(action: CareAction): AsterionClip {
  const clips: Record<CareAction, AsterionClip> = {
    feed: "eat",
    play: "play",
    pet: "pet_reaction",
    sleep: "sleep",
    wake: "wake"
  };
  return clips[action];
}

export function asterionClipForPresentation(animation: string, sleeping: boolean): AsterionClip {
  if (sleeping) return "sleep";

  const clips: Record<string, AsterionClip> = {
    failed: "sleep",
    idle: "idle",
    jumping: "play",
    review: "idle",
    waiting: "walk",
    waving: "happy"
  };
  return clips[animation] ?? "idle";
}
