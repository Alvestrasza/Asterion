import type { CareAction } from "@/lib/care-engine";

export const DAILY_XP_LIMIT = 160;
export const REWARD_COOLDOWN_MS = 3 * 60 * 60 * 1000;

export type RewardLedger = {
  rewardDay: string | null;
  earnedToday: number;
  lastFeedRewardAt: number | null;
  lastPlayRewardAt: number | null;
  lastPetRewardAt: number | null;
};

const rewardField = {
  feed: "lastFeedRewardAt",
  play: "lastPlayRewardAt",
  pet: "lastPetRewardAt"
} as const;

export function utcRewardDay(now: number) {
  if (!Number.isFinite(now)) throw new RangeError("Invalid reward time.");
  return new Date(now).toISOString().slice(0, 10);
}

export function grantCareReward(
  ledger: RewardLedger,
  action: CareAction,
  candidate: number,
  now: number
): { xp: number; ledger: RewardLedger } {
  const day = utcRewardDay(now);
  // A clock rollback must not reopen an older daily budget for another action.
  if (ledger.rewardDay && day < ledger.rewardDay) return { xp: 0, ledger };
  const today = ledger.rewardDay === day ? Math.max(0, Math.min(DAILY_XP_LIMIT, ledger.earnedToday)) : 0;
  const next = { ...ledger, rewardDay: day, earnedToday: today };
  if (!(action in rewardField) || !Number.isSafeInteger(candidate) || candidate <= 0) return { xp: 0, ledger: next };

  const field = rewardField[action as keyof typeof rewardField];
  const previous = next[field];
  if (previous !== null && (now < previous || now - previous < REWARD_COOLDOWN_MS)) {
    return { xp: 0, ledger: next };
  }

  const xp = Math.max(0, Math.min(candidate, DAILY_XP_LIMIT - today));
  if (xp === 0) return { xp, ledger: next };
  next.earnedToday += xp;
  next[field] = now;
  return { xp, ledger: next };
}
