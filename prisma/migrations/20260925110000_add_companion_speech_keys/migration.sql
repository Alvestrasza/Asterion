-- Additive event localization metadata. Existing German-only history remains readable.
ALTER TABLE "PetEvent"
  ADD COLUMN "messageKey" VARCHAR(80),
  ADD COLUMN "messageParams" JSONB;
