-- Keycloak owns immutable friend codes. Store only the exact-match SHA-256 lookup.
ALTER TABLE "SocialProfile" ADD COLUMN "friendCodeHash" VARCHAR(64);
CREATE UNIQUE INDEX "SocialProfile_friendCodeHash_key" ON "SocialProfile"("friendCodeHash");
