-- One-to-many companion collection. Apply only after a verified backup with old writers stopped.
BEGIN;

ALTER TABLE "Pet" ADD COLUMN "adoptionRequestId" VARCHAR(36);
ALTER TABLE "PlayerProgress"
  ADD COLUMN "activePetId" TEXT,
  ADD COLUMN "unlockedSlots" INTEGER NOT NULL DEFAULT 1;

UPDATE "PlayerProgress" AS progress
SET "activePetId" = pet."id",
    "unlockedSlots" = LEAST(5, 1 + GREATEST(0, progress."level") / 15)
FROM "Pet" AS pet
WHERE pet."ownerId" = progress."userId";

ALTER TABLE "PetEvent" ADD COLUMN "ownerId" TEXT;
UPDATE "PetEvent" AS event
SET "ownerId" = pet."ownerId"
FROM "Pet" AS pet
WHERE event."petId" = pet."id";
ALTER TABLE "PetEvent" ALTER COLUMN "ownerId" SET NOT NULL;

DROP INDEX "Pet_ownerId_key";
CREATE UNIQUE INDEX "Pet_ownerId_kind_key" ON "Pet"("ownerId", "kind");
CREATE UNIQUE INDEX "Pet_ownerId_adoptionRequestId_key" ON "Pet"("ownerId", "adoptionRequestId");
CREATE INDEX "Pet_ownerId_createdAt_id_idx" ON "Pet"("ownerId", "createdAt", "id");
CREATE UNIQUE INDEX "PetEvent_ownerId_requestId_key" ON "PetEvent"("ownerId", "requestId");
ALTER TABLE "PlayerProgress" ADD CONSTRAINT "PlayerProgress_unlocked_slots" CHECK ("unlockedSlots" BETWEEN 1 AND 5);

COMMIT;
