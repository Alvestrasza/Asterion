-- Durable metadata reservations only. No recovery secrets, encrypted bundles, or user FK.
CREATE TABLE "IdentityStorageWrite" (
    "userId" VARCHAR(128) NOT NULL,
    "issuer" VARCHAR(512) NOT NULL,
    "subject" VARCHAR(255) NOT NULL,
    "attribute" VARCHAR(40) NOT NULL,
    "digest" VARCHAR(64) NOT NULL,
    "confirmed" BOOLEAN NOT NULL DEFAULT false,
    "friendCodeHash" VARCHAR(64),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,
    CONSTRAINT "IdentityStorageWrite_pkey" PRIMARY KEY ("issuer", "subject", "attribute"),
    CONSTRAINT "IdentityStorageWrite_attribute_check" CHECK ("attribute" IN ('starfriends_friend_code', 'starfriends_chat_recovery')),
    CONSTRAINT "IdentityStorageWrite_digest_check" CHECK ("digest" ~ '^[a-f0-9]{64}$'),
    CONSTRAINT "IdentityStorageWrite_friend_hash_check" CHECK (
        ("attribute" = 'starfriends_friend_code' AND "friendCodeHash" IS NOT NULL AND "friendCodeHash" ~ '^[a-f0-9]{64}$') OR
        ("attribute" = 'starfriends_chat_recovery' AND "friendCodeHash" IS NULL)
    )
);

CREATE UNIQUE INDEX "IdentityStorageWrite_friendCodeHash_key" ON "IdentityStorageWrite"("friendCodeHash");
