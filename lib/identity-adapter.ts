import { PrismaAdapter } from "@auth/prisma-adapter";
import type { Adapter } from "next-auth/adapters";
import { prisma } from "@/lib/db";
import { registerIdentity } from "@/lib/access-service";
import { isPublicDeployment } from "@/lib/deployment-config";

const base = PrismaAdapter(prisma);

// Email is display data, never an account-linking or bootstrap mechanism.
export const identityAdapter: Adapter = {
  ...base,
  async linkAccount(account) {
    if (isPublicDeployment()) {
      if (account.provider !== "keycloak") throw new Error("identity_provider_rejected");
      await registerIdentity(account.userId, process.env.AUTH_KEYCLOAK_ISSUER!, account.providerAccountId);
    }
    // The application does not refresh tokens or call APIs with user tokens.
    const { access_token: _access, refresh_token: _refresh, id_token: _id, ...minimal } = account;
    await base.linkAccount!(minimal);
  },
  async getUserByAccount(account) {
    const user = await base.getUserByAccount!(account);
    if (!user || !isPublicDeployment()) return user;
    const identity = await prisma.userAccess.findUnique({ where: { userId: user.id } });
    if (!identity || identity.issuer !== process.env.AUTH_KEYCLOAK_ISSUER || identity.subject !== account.providerAccountId) throw new Error("identity_binding_rejected");
    return user;
  },
  async getSessionAndUser(token) {
    const result = await base.getSessionAndUser!(token);
    if (!result || !isPublicDeployment()) return result;
    const identity = await prisma.userAccess.findUnique({ where: { userId: result.user.id } });
    if (!identity || identity.issuer !== process.env.AUTH_KEYCLOAK_ISSUER) return null;
    return result;
  }
};
