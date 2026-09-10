-- Additive only. Existing users receive no public entitlement automatically.
CREATE TYPE "AccessRole" AS ENUM ('none', 'member', 'admin');
CREATE TYPE "AccessSyncStatus" AS ENUM ('pending', 'applied', 'failed', 'blocked');

CREATE TABLE "UserAccess" (
    "userId" TEXT NOT NULL,
    "issuer" VARCHAR(512) NOT NULL,
    "subject" VARCHAR(255) NOT NULL,
    "desiredRole" "AccessRole" NOT NULL DEFAULT 'none',
    "effectiveRole" "AccessRole" NOT NULL DEFAULT 'none',
    "revision" INTEGER NOT NULL DEFAULT 1,
    "syncedRevision" INTEGER NOT NULL DEFAULT 0,
    "syncStatus" "AccessSyncStatus" NOT NULL DEFAULT 'pending',
    "attempts" INTEGER NOT NULL DEFAULT 0,
    "retryAt" TIMESTAMP(3),
    "checkedAt" TIMESTAMP(3),
    "errorCode" VARCHAR(64),
    "careWindowStartedAt" TIMESTAMP(3),
    "careWindowCount" INTEGER NOT NULL DEFAULT 0,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "UserAccess_pkey" PRIMARY KEY ("userId"),
    CONSTRAINT "UserAccess_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE
);
CREATE UNIQUE INDEX "UserAccess_issuer_subject_key" ON "UserAccess"("issuer", "subject");
CREATE INDEX "UserAccess_syncStatus_retryAt_idx" ON "UserAccess"("syncStatus", "retryAt");
CREATE INDEX "UserAccess_syncStatus_checkedAt_idx" ON "UserAccess"("syncStatus", "checkedAt");

CREATE TABLE "AccessBootstrap" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "consumedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "AccessBootstrap_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "AccessAudit" (
    "id" TEXT NOT NULL,
    "actorId" TEXT,
    "targetId" TEXT NOT NULL,
    "action" VARCHAR(40) NOT NULL,
    "desiredRole" "AccessRole" NOT NULL,
    "effectiveRole" "AccessRole" NOT NULL,
    "revision" INTEGER NOT NULL,
    "outcome" VARCHAR(64) NOT NULL,
    "occurredAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "AccessAudit_pkey" PRIMARY KEY ("id")
);
CREATE INDEX "AccessAudit_targetId_occurredAt_idx" ON "AccessAudit"("targetId", "occurredAt" DESC);
