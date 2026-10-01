/**
 * Asterion: transaction-bound, owner-scoped achievement persistence.
 * Version: 1.0.0 | License: UNLICENSED | Updated: 2026-10-01
 */
import type { Prisma, Pet } from "@prisma/client";
import { ACHIEVEMENTS, ACHIEVEMENT_VERSION, achievementViews, careBit, healthyCare, variedCareCount, type AchievementId } from "./achievements.ts";
import type { Locale } from "./i18n.ts";
import { utcRewardDay } from "./progression.ts";

async function record(tx: Prisma.TransactionClient, ownerId: string, petId: string | null, id: AchievementId, value: number, now: Date) {
  const definition = ACHIEVEMENTS.find(entry => entry.id === id)!;
  if ((definition.scope === "account") !== (petId === null)) throw new Error("Invalid achievement scope.");
  const scopeKey = petId ?? "account";
  const where = { ownerId_scopeKey_achievementId: { ownerId, scopeKey, achievementId: id } };
  const prior = await tx.achievementProgress.findUnique({ where });
  const progress = Math.min(definition.target, Math.max(prior?.progress ?? 0, value));
  const earnedAt = prior?.earnedAt ?? (progress >= definition.target ? now : null);
  await tx.achievementProgress.upsert({ where,
    create: { ownerId, petId, scopeKey, achievementId: id, catalogVersion: ACHIEVEMENT_VERSION, progress, earnedAt },
    update: { progress, earnedAt }
  });
  return !prior?.earnedAt && earnedAt !== null ? id : null;
}

export async function recordAdoptionAchievements(tx: Prisma.TransactionClient, ownerId: string, now: Date) {
  const pets = await tx.pet.findMany({ where: { ownerId }, select: { kind: true } });
  const count = new Set(pets.map(pet => pet.kind)).size;
  const unlocked: AchievementId[] = [];
  for (const id of ["v1.first-adoption", "v1.companion-family", "v1.constellation"] as const) {
    const award = await record(tx, ownerId, null, id, count, now);
    if (award) unlocked.push(award);
  }
  return unlocked;
}

/** Call only after persisting a new accepted, XP-rewarded care event in the same serializable transaction. */
export async function recordCareAchievements(tx: Prisma.TransactionClient, ownerId: string, pet: Pet,
  event: { action: string; accepted: boolean; xpAwarded: number }, now: Date, playerLevel: number) {
  const bit = careBit(event.action);
  if (!event.accepted || event.xpAwarded <= 0 || bit === 0) return [] as AchievementId[];
  if (pet.ownerId !== ownerId) throw new Error("Achievement companion ownership mismatch.");
  const day = utcRewardDay(now.getTime());
  const where = { petId_day: { petId: pet.id, day } };
  const prior = await tx.achievementCareDay.findUnique({ where });
  await tx.achievementCareDay.upsert({ where,
    create: { ownerId, petId: pet.id, day, careMask: bit, healthy: healthyCare(pet, pet.sleeping) },
    update: { careMask: (prior?.careMask ?? 0) | bit, healthy: Boolean(prior?.healthy) || healthyCare(pet, pet.sleeping) }
  });
  const days = await tx.achievementCareDay.findMany({ where: { petId: pet.id, ownerId }, select: { careMask: true, healthy: true } });
  const mask = days.reduce((sum, entry) => sum | entry.careMask, 0);
  const values: Array<[AchievementId, string | null, number]> = [
    ["v1.first-care", pet.id, 1], ["v1.varied-care", pet.id, variedCareCount(mask)],
    ["v1.healthy-bond", pet.id, days.filter(entry => entry.healthy).length],
    ["v1.pet-level-five", pet.id, pet.level], ["v1.player-level-five", null, playerLevel]
  ];
  const unlocked: AchievementId[] = [];
  for (const [id, petId, value] of values) {
    const award = await record(tx, ownerId, petId, id, value, now);
    if (award) unlocked.push(award);
  }
  return unlocked;
}

export async function readAchievements(tx: Prisma.TransactionClient, ownerId: string, petId: string, locale: Locale) {
  const rows = await tx.achievementProgress.findMany({ where: { ownerId, OR: [{ scopeKey: "account" }, { petId }] } });
  return achievementViews(locale, rows);
}
