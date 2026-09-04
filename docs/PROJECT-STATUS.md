# Asterion project status

Last public-safe verification: 2026-09-04

## Current application baseline

- Application version: `0.4.1`
- Eight selectable companions are implemented.
- PostgreSQL is authoritative for companion state, action history, and Auth.js sessions.
- Web nodes are stateless and use serializable, idempotent mutations.
- The installable PWA caches public static assets only.
- The temporary internal profile uses one visibly identified shared test user.

## Verified internal-test evidence

The current immutable `0.4.1` application artifact was installed on two private-network web nodes and verified at these levels:

- service active and enabled on both nodes
- loopback application listener healthy on both nodes
- private reverse-proxy listener healthy on both nodes
- PostgreSQL reported reachable through the application health endpoint
- browser-origin mutation requests returned HTTP 200 through both nodes
- companion selection persisted and returned the requested companion kind
- the same repaired Asterion asset and PWA cache generation were served by both nodes

The release passed 16 deterministic tests, TypeScript checking, Prisma client generation, and a Linux production build.

This evidence does not prove Keycloak login or per-user isolation because the temporary shared-user bypass is still active.

## Resolved issues in 0.4.1

- The internal reverse proxy now preserves the browser-visible port for same-origin mutation checks.
- Asterion's transparent artwork no longer contains the bright chroma-key edge fringe; canvas dimensions and alpha silhouette were preserved.
- The service-worker cache generation was advanced so existing installations can receive the repaired asset.
- First-start health verification and rollback behavior were hardened.

## Pending infrastructure work

- Create and configure the intended Keycloak OIDC client and access assignment.
- Disable the shared-user test mode.
- Configure the external URL and load-balancer route.
- Validate authentication, authorization, per-user isolation, logout, and cross-device continuity.
- Perform production readiness review before any public exposure.

Real endpoints, addresses, credentials, keys, certificates, and host inventories remain outside this public repository.

## Pending product work

- Establish the Blender-based 3D pipeline described in `docs/3D-ASSET-PIPELINE.md`.
- Build and approve the Asterion 3D vertical slice.
- Add a lazy-loaded WebGL presentation with a resilient 2D fallback.
- Extend the accepted pipeline to the remaining companions.

## Workstation handoff

Use `docs/SECOND-WORKSTATION.md`. A clean Git clone plus tracked instructions is authoritative; copied dependency trees, local build output, chat transcripts, and ignored private files are not.
