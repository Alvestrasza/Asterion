# Asterion Operations

## Deployment contract

The repository contains generic templates only. Real hostnames, certificate paths, credentials, database endpoints, and identity topology remain in the protected operations environment.

The target platform requires:

- Node.js 22 or newer
- two stateless web nodes behind the existing reverse proxy or load balancer
- one dedicated PostgreSQL database per environment
- a runtime database role with DML privileges only
- a migration database role that owns the application schema
- one Keycloak OIDC client and one required access assignment per environment

## Initial provisioning

1. Have the PostgreSQL administrator create the environment-specific database and roles using `deploy/postgresql/bootstrap.sql` as a reviewed template.
2. Have the identity administrator create the OIDC client, callback URI, logout URI, and required group or role.
3. Create the protected environment file on each node. Start from `deploy/systemd/asterion.env.example`; set mode `0640` and owner/group appropriate for the service account.
4. Install the application under a dedicated path and install an environment-specific systemd unit derived from `deploy/systemd/asterion.service`.
5. Install an environment-specific reverse-proxy site derived from `deploy/nginx/asterion.conf` and validate the proxy configuration before reload.

## Release procedure

Use the same immutable build on both nodes.

1. Run `pnpm install --frozen-lockfile`, `pnpm test`, `pnpm check`, and `pnpm build` in a clean Linux release workspace. The build script copies `public/` and `.next/static/` into the standalone artifact.
2. Back up the target database and record the application artifact hash.
3. Run `prisma migrate deploy` once with the migration role. Do not run migrations concurrently on both nodes.
4. Remove node A from load-balancer rotation.
5. Install the immutable release on node A, restart its service, and verify `/api/health` plus an authenticated pet read/action.
6. Return node A to rotation and repeat for node B.
7. Verify that the same user sees the same pet version through both nodes and that replaying one request id changes the pet only once.

## Rollback

Application rollback is an atomic switch to the previous immutable release followed by a service restart. Database rollback requires a migration-specific plan; never reverse a schema migration by restoring an old application alone. Prefer backward-compatible expand-and-contract migrations.

## Health and acceptance levels

- Process: systemd reports the unit active.
- Listener: the configured loopback port accepts connections.
- Readiness: `/api/health` returns HTTP 200 and reports the database reachable.
- Authentication: Keycloak login creates an Auth.js database session.
- Functional: a care action persists and appears from a second device.
- Multi-node: an idempotency replay and simultaneous actions remain consistent across both nodes.

Only the last two levels establish that the Tamagotchi service itself works.

## Observability

Log authentication denials, transaction exhaustion, database reachability failures, and unexpected API errors without tokens, cookies, personal pet exports, or connection strings. Alert on repeated HTTP 5xx responses and health-check failures.
