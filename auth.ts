import NextAuth from "next-auth";
import Keycloak from "next-auth/providers/keycloak";
import { isKeycloakConfigured } from "@/lib/auth-config";
import { identityAdapter } from "@/lib/identity-adapter";
import { isPublicDeployment, publicRuntimeErrors } from "@/lib/deployment-config";
import { identitySubject, mayBootstrapAdmin } from "@/lib/identity-policy";
import { registerIdentity } from "@/lib/access-service";
import { prisma } from "@/lib/db";
import { ensureFriendCode } from "@/lib/friend-code-service";
import { keycloakStorageConfigured } from "@/lib/keycloak-storage";

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }
}

export const { handlers, signIn, signOut, auth } = NextAuth({
  adapter: identityAdapter,
  session: { strategy: "database", maxAge: 8 * 60 * 60, updateAge: 60 * 60 },
  logger: { error(error) {
    const category = "type" in error && typeof error.type === "string" ? error.type : error.name;
    const code = /^[A-Za-z]{1,64}$/.test(category) ? category : "AuthenticationError";
    console.error(`Authentication operation failed (${code}); inspect provider and deployment configuration.`);
  } },
  providers:
    isKeycloakConfigured()
      ? [
          Keycloak({
            clientId: process.env.AUTH_KEYCLOAK_ID,
            clientSecret: process.env.AUTH_KEYCLOAK_SECRET,
            issuer: process.env.AUTH_KEYCLOAK_ISSUER,
            checks: ["pkce", "state", "nonce"],
            authorization: { params: { scope: "openid profile email", prompt: "login" } }
          })
        ]
      : [],
  callbacks: {
    async signIn({ account, profile }) {
      if (account?.provider !== "keycloak") return false;
      if (isPublicDeployment()) {
        // Verified identities receive basic membership; admin roles remain separately controlled.
        return publicRuntimeErrors().length === 0 && identitySubject(profile) === account.providerAccountId;
      }

      return false;
    },
    session({ session, user }) {
      if (session.user) session.user.id = user.id;
      return session;
    }
  },
  events: {
    async signIn({ user, account, profile }) {
      if (!isPublicDeployment() || !user.id || account?.provider !== "keycloak") return;
      await registerIdentity(user.id, process.env.AUTH_KEYCLOAK_ISSUER!, account.providerAccountId, mayBootstrapAdmin(profile));
      // First successful StarFriends admission creates the immutable code in a
      // standard Keycloak attribute. Existing accounts use the same guarded path.
      if (keycloakStorageConfigured()) await ensureFriendCode(user.id);
      // Retain fresh provider verification as identity metadata, not social lookup.
      // Never link accounts or grant membership through this display attribute.
      await prisma.user.update({ where: { id: user.id }, data: {
        emailVerified: typeof profile?.email === "string" && profile.email === user.email && profile.email_verified === true ? new Date() : null
      } });
    }
  },
  pages: {
    signIn: "/login"
  }
});
