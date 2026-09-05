export function isKeycloakConfigured(environment: Record<string, string | undefined> = process.env): boolean {
  return ["AUTH_KEYCLOAK_ID", "AUTH_KEYCLOAK_SECRET", "AUTH_KEYCLOAK_ISSUER"]
    .every((key) => Boolean(environment[key]?.trim()));
}
