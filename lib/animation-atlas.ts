export const ASTERION_ATLAS = {
  asset: "/assets/spritesheet.webp", width: 1536, height: 2288, cellWidth: 192, cellHeight: 208
} as const;

// Zero-based atlas rows and original GIF frame delays in milliseconds.
// The extra idle cell at column 6 is not part of the approved six-frame loop.
export const ASTERION_ANIMATIONS = {
  idle: { row: 0, delays: [280, 110, 110, 140, 140, 320] },
  "running-right": { row: 1, delays: [120, 120, 120, 120, 120, 120, 120, 220] },
  "running-left": { row: 2, delays: [120, 120, 120, 120, 120, 120, 120, 220] },
  waving: { row: 3, delays: [140, 140, 140, 280] },
  jumping: { row: 4, delays: [140, 140, 140, 140, 280] },
  failed: { row: 5, delays: [140, 140, 140, 140, 140, 140, 140, 240] },
  waiting: { row: 6, delays: [150, 150, 150, 150, 150, 260] },
  running: { row: 7, delays: [120, 120, 120, 120, 120, 220] },
  review: { row: 8, delays: [150, 150, 150, 150, 150, 280] }
} as const;

export type AsterionAnimation = keyof typeof ASTERION_ANIMATIONS;

export function atlasAnimation(value: string | undefined): AsterionAnimation {
  return value && Object.hasOwn(ASTERION_ANIMATIONS, value) ? value as AsterionAnimation : "idle";
}

export function atlasTimeline(value: string | undefined) {
  const name = atlasAnimation(value);
  const { row, delays } = ASTERION_ANIMATIONS[name];
  const duration = delays.reduce<number>((total, delay) => total + delay, 0);
  let elapsed = 0;
  const frames = delays.map((delay, column) => {
    const frame = { column, offset: elapsed / duration };
    elapsed += delay;
    return frame;
  });
  return { name, row, duration, frames };
}
