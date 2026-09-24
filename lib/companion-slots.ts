export const MAX_COMPANIONS = 5;

/** Slots stay unlocked after reaching a milestone, even if progress is repaired later. */
export function slotsForLevel(level: number): number {
  if (!Number.isFinite(level)) return 1;
  return Math.min(MAX_COMPANIONS, 1 + Math.floor(Math.max(0, level) / 15));
}

export function availableSlots(level: number, persistedSlots: number): number {
  return Math.min(MAX_COMPANIONS, Math.max(slotsForLevel(level), Math.max(1, persistedSlots)));
}
