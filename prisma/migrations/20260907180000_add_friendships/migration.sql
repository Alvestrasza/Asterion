CREATE TABLE "SocialProfile" (
  "userId" TEXT PRIMARY KEY REFERENCES "User"("id") ON DELETE CASCADE,
  "username" VARCHAR(32), "discoverable" BOOLEAN NOT NULL DEFAULT false,
  "lastSeenAt" TIMESTAMP(3), "windowStartedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "windowCount" INTEGER NOT NULL DEFAULT 0, "requestDay" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "requestCount" INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX "SocialProfile_username_key" ON "SocialProfile"("username");
CREATE TABLE "Friendship" (
  "id" TEXT PRIMARY KEY,
  "leftId" TEXT NOT NULL REFERENCES "User"("id") ON DELETE CASCADE,
  "rightId" TEXT NOT NULL REFERENCES "User"("id") ON DELETE CASCADE,
  "requestedBy" TEXT NOT NULL, "status" VARCHAR(16) NOT NULL DEFAULT 'pending',
  "leftBlocked" BOOLEAN NOT NULL DEFAULT false, "rightBlocked" BOOLEAN NOT NULL DEFAULT false,
  "updatedAt" TIMESTAMP(3) NOT NULL, "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "Friendship_ordered_pair" CHECK ("leftId" < "rightId"),
  CONSTRAINT "Friendship_requester_member" CHECK ("requestedBy" IN ("leftId", "rightId")),
  CONSTRAINT "Friendship_valid_status" CHECK ("status" IN ('pending', 'accepted', 'closed'))
);
CREATE UNIQUE INDEX "Friendship_leftId_rightId_key" ON "Friendship"("leftId", "rightId");
CREATE INDEX "Friendship_rightId_status_idx" ON "Friendship"("rightId", "status");
