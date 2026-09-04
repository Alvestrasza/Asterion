# Internal test deployment

This profile deliberately runs without Keycloak and maps every visitor to one shared test user. It is suitable only for a private network test before the real OIDC client and external reverse-proxy route exist.

Security boundaries:

- Next.js listens on loopback port `3011`.
- Nginx exposes port `8088` only to loopback, RFC1918, and unique-local IPv6 source addresses.
- The shared-user bypass is enabled only by `ASTERION_INTERNAL_TEST_MODE=true` in the protected service environment.
- Do not attach the temporary port to an Internet-facing load balancer.
- Remove this profile when Keycloak is enabled; do not convert it into the external deployment in place.

After staging the release, use `deploy/internal/provision-database.sh` with a PostgreSQL cluster-administrator URL, or have a database administrator apply `deploy/postgresql/bootstrap.sql` with equivalent reviewed names and passwords.

1. Build the release on Linux with `pnpm install --frozen-lockfile`, `pnpm test`, `pnpm check`, and `pnpm build`.
2. Provision the database once, if it does not already exist.
3. On the first web node, run `deploy/internal/finish-internal-test.sh`. It applies migrations and dispatches the root installation through the approved staged-release sudo rule. On the second node, run `sudo /bin/bash "$(pwd -P)/install-staged-release.sh" internal-test` from the release root so the sudo rule receives the required absolute path and migrations are not applied twice.
4. If UFW is active, allow only the trusted test-client CIDR by running `sudo deploy/internal/configure-internal-test-firewall.sh allow <trusted-private-cidr>` on each node. Use the `remove` action with the same CIDR to revoke the temporary rule.
5. Verify `/api/health`, the shared-test banner, a care action, and a companion change through each web node on port `8088`.

The installer uses immutable releases and restores the previous application symlink when service or health verification fails.
