import NextAuth from "next-auth";
import Keycloak from "next-auth/providers/keycloak";
import { PrismaAdapter } from "@auth/prisma-adapter";
import { prisma } from "@/lib/db";

type KeycloakProfile = {
  groups?: unknown;
  realm_access?: { roles?: unknown };
  resource_access?: Record<string, { roles?: unknown }>;
};

function strings(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string") : [];
}

function profileAssignments(profile: unknown) {
  const source = (profile ?? {}) as KeycloakProfile;
  const clientId = process.env.AUTH_KEYCLOAK_ID;
  const assignments = new Set([
    ...strings(source.groups),
    ...strings(source.realm_access?.roles),
    ...(clientId ? strings(source.resource_access?.[clientId]?.roles) : [])
  ]);

  return assignments;
}

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
  adapter: PrismaAdapter(prisma),
  session: { strategy: "database" },
  providers: [
    Keycloak({
      clientId: process.env.AUTH_KEYCLOAK_ID!,
      clientSecret: process.env.AUTH_KEYCLOAK_SECRET!,
      issuer: process.env.AUTH_KEYCLOAK_ISSUER!
    })
  ],
  callbacks: {
    async signIn({ account, profile }) {
      if (account?.provider !== "keycloak") return false;

      const required = process.env.ASTERION_REQUIRED_ROLE?.trim();
      if (!required) {
        if (process.env.NODE_ENV === "production") {
          console.error("Asterion sign-in denied: ASTERION_REQUIRED_ROLE is not configured.");
          return false;
        }
        return true;
      }

      const assignments = profileAssignments(profile);
      return assignments.has(required) || assignments.has(`/${required}`);
    },
    session({ session, user }) {
      if (session.user) session.user.id = user.id;
      return session;
    }
  },
  pages: {
    signIn: "/login"
  }
});
