-- Apply only in a maintenance window after a verified backup and before the new app starts.
-- Preserve any out-of-range legacy progress before enforcing the level-99 cap.
ALTER TABLE "Pet"
  ADD COLUMN "preCapLevel" INTEGER,
  ADD COLUMN "preCapXp" INTEGER;

UPDATE "Pet"
SET "preCapLevel" = "level", "preCapXp" = "xp"
WHERE "level" > 99 OR ("level" = 99 AND "xp" <> 0);

UPDATE "Pet"
SET "level" = LEAST(99, GREATEST(1, "level")),
    "xp" = CASE WHEN "level" >= 99 THEN 0 ELSE GREATEST(0, "xp") END
WHERE "level" > 99 OR "level" < 1 OR "xp" < 0 OR ("level" = 99 AND "xp" <> 0);

CREATE TABLE "PlayerProgress" (
  "userId" TEXT NOT NULL PRIMARY KEY REFERENCES "User"("id") ON DELETE CASCADE,
  "level" INTEGER NOT NULL DEFAULT 1,
  "xp" INTEGER NOT NULL DEFAULT 0,
  "rewardDay" VARCHAR(10),
  "earnedToday" INTEGER NOT NULL DEFAULT 0,
  "lastFeedRewardAt" TIMESTAMP(3),
  "lastPlayRewardAt" TIMESTAMP(3),
  "lastPetRewardAt" TIMESTAMP(3),
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updatedAt" TIMESTAMP(3) NOT NULL
);

-- Existing users keep their current pet progress as their initial account progress.
INSERT INTO "PlayerProgress" ("userId", "level", "xp", "createdAt", "updatedAt")
SELECT "ownerId", "level", "xp", CURRENT_TIMESTAMP, CURRENT_TIMESTAMP FROM "Pet";

ALTER TABLE "PetEvent" ADD COLUMN "xpAwarded" INTEGER NOT NULL DEFAULT 0;

ALTER TABLE "Pet" ADD CONSTRAINT "Pet_level_range" CHECK ("level" BETWEEN 1 AND 99 AND "xp" >= 0);
ALTER TABLE "PlayerProgress" ADD CONSTRAINT "PlayerProgress_range" CHECK (
  "level" BETWEEN 1 AND 99 AND "xp" >= 0 AND "earnedToday" BETWEEN 0 AND 160
);
ALTER TABLE "PetEvent" ADD CONSTRAINT "PetEvent_xp_nonnegative" CHECK ("xpAwarded" >= 0);
