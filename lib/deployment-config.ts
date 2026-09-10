type Environment = Record<string, string | undefined>;

export function isPublicDeployment(environment: Environment = process.env) {
  return environment.ASTERION_DEPLOYMENT_MODE === "public";
}

export function canonicalOrigin(environment: Environment = process.env): string | null {
  try {
    const value = environment.AUTH_URL?.trim();
    if (!value) return null;
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash || url.pathname !== "/") return null;
    return url.origin;
  } catch {
    return null;
  }
}

export function publicRuntimeErrors(environment: Environment = process.env): string[] {
  if (!isPublicDeployment(environment)) return [];
  const errors: string[] = [];
  if (environment.ASTERION_INTERNAL_TEST_MODE !== "false") errors.push("internal_mode_must_be_false");
  if (!canonicalOrigin(environment)) errors.push("canonical_https_origin_required");
  for (const key of ["AUTH_SECRET", "AUTH_KEYCLOAK_ID", "AUTH_KEYCLOAK_SECRET", "AUTH_KEYCLOAK_ISSUER",
    "ASTERION_KEYCLOAK_ADMIN_ORIGIN", "ASTERION_KEYCLOAK_ADMIN_CLIENT_ID", "ASTERION_KEYCLOAK_ADMIN_CLIENT_SECRET", "ASTERION_KEYCLOAK_CLIENT_UUID",
    "ASTERION_MEMBER_ROLE", "ASTERION_ADMIN_ROLE", "ASTERION_ACCESS_SYNC_SECRET"]) {
    if (!environment[key]?.trim()) errors.push(`${key}_required`);
  }
  if ((environment.AUTH_SECRET?.length ?? 0) < 32) errors.push("auth_secret_too_short");
  if (environment.ASTERION_MEMBER_ROLE === environment.ASTERION_ADMIN_ROLE) errors.push("roles_must_be_distinct");
  try {
    const issuer = new URL(environment.AUTH_KEYCLOAK_ISSUER ?? "");
    if (issuer.protocol !== "https:" || issuer.username || issuer.password || issuer.search || issuer.hash || !/\/realms\/[^/]+$/.test(issuer.pathname)) errors.push("invalid_oidc_issuer");
  } catch { errors.push("invalid_oidc_issuer"); }
  try {
    const admin = new URL(environment.ASTERION_KEYCLOAK_ADMIN_ORIGIN ?? "");
    if (admin.protocol !== "https:" || admin.username || admin.password || admin.port ||
        environment.ASTERION_KEYCLOAK_ADMIN_ORIGIN !== admin.origin ||
        !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(admin.hostname) ||
        /^\d+\.\d+\.\d+\.\d+$/.test(admin.hostname)) errors.push("invalid_keycloak_admin_origin");
  } catch { errors.push("invalid_keycloak_admin_origin"); }
  return errors;
}

export function assertDeploymentConfiguration() {
  const errors = publicRuntimeErrors();
  if (errors.length) throw new Error(`Public deployment configuration rejected: ${errors.join(", ")}`);
}
