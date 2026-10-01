-- Asterion achievement catalog v1. Atomic additive schema and evidence-based backfill.
-- Version: 1.0.0 | License: UNLICENSED | Updated: 2026-10-01
BEGIN;
CREATE UNIQUE INDEX "Pet_id_ownerId_key" ON "Pet"("id", "ownerId");
CREATE TABLE "AchievementProgress" (
  "ownerId" TEXT NOT NULL,
  "scopeKey" VARCHAR(64) NOT NULL,
  "achievementId" VARCHAR(64) NOT NULL,
  "petId" TEXT,
  "catalogVersion" INTEGER NOT NULL DEFAULT 1,
  "progress" INTEGER NOT NULL DEFAULT 0,
  "earnedAt" TIMESTAMP(3),
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "AchievementProgress_pkey" PRIMARY KEY ("ownerId", "scopeKey", "achievementId"),
  CONSTRAINT "AchievementProgress_ownerId_fkey" FOREIGN KEY ("ownerId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT "AchievementProgress_petId_ownerId_fkey" FOREIGN KEY ("petId", "ownerId") REFERENCES "Pet"("id", "ownerId") ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT "AchievementProgress_scope_check" CHECK (("petId" IS NULL AND "scopeKey" = 'account') OR ("petId" IS NOT NULL AND "scopeKey" = "petId")),
  CONSTRAINT "AchievementProgress_progress_check" CHECK ("progress" >= 0 AND "catalogVersion" >= 1)
);
CREATE INDEX "AchievementProgress_ownerId_petId_idx" ON "AchievementProgress"("ownerId", "petId");
CREATE TABLE "AchievementCareDay" (
  "ownerId" TEXT NOT NULL,
  "petId" TEXT NOT NULL,
  "day" VARCHAR(10) NOT NULL,
  "careMask" INTEGER NOT NULL,
  "healthy" BOOLEAN NOT NULL DEFAULT false,
  CONSTRAINT "AchievementCareDay_pkey" PRIMARY KEY ("petId", "day"),
  CONSTRAINT "AchievementCareDay_ownerId_fkey" FOREIGN KEY ("ownerId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT "AchievementCareDay_petId_ownerId_fkey" FOREIGN KEY ("petId", "ownerId") REFERENCES "Pet"("id", "ownerId") ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT "AchievementCareDay_mask_check" CHECK ("careMask" BETWEEN 1 AND 7),
  CONSTRAINT "AchievementCareDay_day_check" CHECK ("day" ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$')
);
CREATE INDEX "AchievementCareDay_ownerId_petId_idx" ON "AchievementCareDay"("ownerId", "petId");

-- Retained positive-XP care events prove care type/date, but cannot prove historical health.
INSERT INTO "AchievementCareDay" ("ownerId", "petId", "day", "careMask")
SELECT e."ownerId", e."petId", to_char(e."occurredAt", 'YYYY-MM-DD'),
  bit_or(CASE e."action" WHEN 'feed' THEN 1 WHEN 'play' THEN 2 WHEN 'pet' THEN 4 END)
FROM "PetEvent" e JOIN "Pet" p ON p."id" = e."petId" AND p."ownerId" = e."ownerId"
WHERE e."accepted" AND e."xpAwarded" > 0 AND e."action" IN ('feed', 'play', 'pet')
GROUP BY e."ownerId", e."petId", to_char(e."occurredAt", 'YYYY-MM-DD');

WITH roster AS (
  SELECT "ownerId", count(DISTINCT "kind")::int AS amount FROM "Pet" GROUP BY "ownerId"
), care AS (
  SELECT "ownerId", "petId", bit_or("careMask") AS mask FROM "AchievementCareDay" GROUP BY "ownerId", "petId"
), candidates AS (
  SELECT "ownerId", NULL::text AS "petId", 'v1.first-adoption' AS id, least(amount, 1) AS value, 1 AS target FROM roster
  UNION ALL SELECT "ownerId", NULL, 'v1.companion-family', least(amount, 2), 2 FROM roster
  UNION ALL SELECT "ownerId", NULL, 'v1.constellation', least(amount, 5), 5 FROM roster
  UNION ALL SELECT "userId", NULL, 'v1.player-level-five', least("level", 5), 5 FROM "PlayerProgress"
  UNION ALL SELECT "ownerId", "id", 'v1.pet-level-five', least("level", 5), 5 FROM "Pet"
  UNION ALL SELECT "ownerId", "petId", 'v1.first-care', 1, 1 FROM care
  UNION ALL SELECT "ownerId", "petId", 'v1.varied-care',
    ((mask & 1) > 0)::int + ((mask & 2) > 0)::int + ((mask & 4) > 0)::int, 3 FROM care
)
INSERT INTO "AchievementProgress" ("ownerId", "scopeKey", "achievementId", "petId", "progress", "earnedAt")
SELECT "ownerId", coalesce("petId", 'account'), id, "petId", value,
  CASE WHEN value >= target THEN CURRENT_TIMESTAMP ELSE NULL END FROM candidates;
-- No health-day fabrication, XP changes, gameplay-event edits or deletions.
COMMIT;
