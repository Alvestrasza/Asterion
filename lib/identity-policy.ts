type Environment = Record<string, string | undefined>;

export function identitySubject(profile: unknown): string | null {
  if (!profile || typeof profile !== "object") return null;
  const sub = (profile as { sub?: unknown }).sub;
  return typeof sub === "string" && sub.length > 0 && sub.length <= 255 ? sub : null;
}

export function mayBootstrapAdmin(profile: unknown, environment: Environment = process.env): boolean {
  const subject = identitySubject(profile);
  if (!environment.AUTH_KEYCLOAK_ID?.trim() || !environment.ASTERION_ADMIN_ROLE?.trim()) return false;
  if (!subject || !environment.ASTERION_BOOTSTRAP_ADMIN_SUB || subject !== environment.ASTERION_BOOTSTRAP_ADMIN_SUB) return false;
  const source = profile as { resource_access?: Record<string, { roles?: unknown }> };
  const roles = source.resource_access?.[environment.AUTH_KEYCLOAK_ID ?? ""]?.roles;
  return Boolean(environment.ASTERION_ADMIN_ROLE) && Array.isArray(roles) && roles.includes(environment.ASTERION_ADMIN_ROLE);
}

export function keycloakLogoutUrl(environment: Environment = process.env): string | null {
  if (environment.ASTERION_DEPLOYMENT_MODE !== "public" || !environment.AUTH_KEYCLOAK_ISSUER || !environment.AUTH_KEYCLOAK_ID || !environment.AUTH_URL) return null;
  const issuer = new URL(environment.AUTH_KEYCLOAK_ISSUER);
  const origin = new URL(environment.AUTH_URL);
  if (issuer.protocol !== "https:" || origin.protocol !== "https:") return null;
  const url = new URL(`${issuer.href}/protocol/openid-connect/logout`);
  url.searchParams.set("client_id", environment.AUTH_KEYCLOAK_ID);
  url.searchParams.set("post_logout_redirect_uri", `${origin.origin}/login`);
  return url.href;
}
