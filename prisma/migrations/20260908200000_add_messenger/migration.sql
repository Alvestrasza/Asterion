-- Additive migration: old releases do not read or write these tables.
-- No private keys, recovery codes, or message plaintext belong in these columns.
CREATE TABLE "ChatIdentity" (
  "userId" TEXT PRIMARY KEY REFERENCES "User"("id") ON DELETE CASCADE,
  "fingerprint" VARCHAR(64) NOT NULL,
  "registration" JSONB NOT NULL,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX "ChatIdentity_fingerprint_key" ON "ChatIdentity"("fingerprint");

CREATE TABLE "ChatBudget" (
  "userId" TEXT PRIMARY KEY REFERENCES "User"("id") ON DELETE CASCADE,
  "windowStartedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "windowCount" INTEGER NOT NULL DEFAULT 0,
  "sendCount" INTEGER NOT NULL DEFAULT 0,
  "registrationCount" INTEGER NOT NULL DEFAULT 0,
  "dayStartedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "daySendCount" INTEGER NOT NULL DEFAULT 0,
  CONSTRAINT "ChatBudget_nonnegative" CHECK ("windowCount" >= 0 AND "sendCount" >= 0 AND "registrationCount" >= 0 AND "daySendCount" >= 0)
);

CREATE TABLE "ChatMessage" (
  "sequence" BIGSERIAL PRIMARY KEY,
  "id" VARCHAR(36) NOT NULL,
  "friendshipId" TEXT NOT NULL REFERENCES "Friendship"("id") ON DELETE CASCADE,
  "senderId" TEXT NOT NULL,
  "recipientId" TEXT NOT NULL,
  "envelope" JSONB NOT NULL,
  "digest" VARCHAR(128) NOT NULL,
  "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "ChatMessage_distinct_participants" CHECK ("senderId" <> "recipientId")
);
CREATE UNIQUE INDEX "ChatMessage_id_key" ON "ChatMessage"("id");
CREATE INDEX "ChatMessage_friendshipId_sequence_idx" ON "ChatMessage"("friendshipId", "sequence");
CREATE INDEX "ChatMessage_recipientId_friendshipId_sequence_idx" ON "ChatMessage"("recipientId", "friendshipId", "sequence");

CREATE TABLE "ChatRead" (
  "userId" TEXT NOT NULL REFERENCES "User"("id") ON DELETE CASCADE,
  "friendshipId" TEXT NOT NULL REFERENCES "Friendship"("id") ON DELETE CASCADE,
  "sequence" BIGINT NOT NULL DEFAULT 0,
  PRIMARY KEY ("userId", "friendshipId"),
  CONSTRAINT "ChatRead_nonnegative" CHECK ("sequence" >= 0)
);
