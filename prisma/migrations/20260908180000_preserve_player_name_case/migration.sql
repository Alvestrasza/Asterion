-- Keep the normalized unique/search key unchanged. Earlier casing cannot be recovered.
-- Nullable display data allows older releases to read/write the same profiles.
ALTER TABLE "SocialProfile" ADD COLUMN "usernameDisplay" VARCHAR(32);
