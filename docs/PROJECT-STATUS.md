# Asterion project status

Local website-foundation status: 2026-09-05

Deployment preflight: both internal nodes were rechecked on 2026-09-05 and still served the healthy `0.4.1` artifact. Installation of the new `0.5.0` website foundation is pending at this publication checkpoint.

## Version 0.5.0 website foundation

The first implementation slice for issues [#2](https://github.com/Alvestrasza/Asterion/issues/2) and [#5](https://github.com/Alvestrasza/Asterion/issues/5) adds:

- a public introduction at `/` that does not query authentication or the database
- the existing protected care prototype at `/care`, with its ownership checks and shared-test warning preserved
- German, English, French, and Spanish public/login text, saved language selection, browser detection, and English fallback
- a disabled login entry point when the complete Keycloak provider configuration is absent
- localized loading/error messages and accessible, responsive public navigation

Local browser checks covered all four public-page languages, persistence of a manual selection across reload and navigation, the unavailable-provider login state, anonymous care-route redirection, and the corrected 375-pixel mobile layout, with no browser-console errors. A frozen-lockfile installation, all 27 automated tests, `pnpm check`, and the Windows production build passed. The built standalone server passed eight isolated HTTP smoke cases with an unreachable placeholder database; a browser check also confirmed persisted language and matching metadata on that artifact. Linux artifact and deployment verification remain outstanding.

This slice has not been deployed and establishes no new PostgreSQL, Keycloak, multi-node, or per-user isolation acceptance. The care interface and persisted event messages remain German. See [Website foundation](WEBSITE-FOUNDATION.md) for the implementation boundary and remaining checks.

Issue [#13](https://github.com/Alvestrasza/Asterion/issues/13) is deliberately deferred. No diary inspection, alerting, content-access hooks, or new operator visibility have been introduced. Future private-diary work retains the requirement for client-side encryption and must not silently introduce server-side plaintext access.

## Historical deployed application baseline

- Application version: `0.4.1`
- Eight selectable companions are implemented.
- PostgreSQL is authoritative for companion state, action history, and Auth.js sessions.
- Web nodes are stateless and use serializable, idempotent mutations.
- The installable PWA caches public static assets only.
- The temporary internal profile uses one visibly identified shared test user.

## Historical internal-test evidence

The immutable `0.4.1` application artifact was installed on two private-network web nodes and verified on 2026-09-04 at these levels:

- service active and enabled on both nodes
- loopback application listener healthy on both nodes
- private reverse-proxy listener healthy on both nodes
- PostgreSQL reported reachable through the application health endpoint
- browser-origin mutation requests returned HTTP 200 through both nodes
- companion selection persisted and returned the requested companion kind
- the same repaired Asterion asset and PWA cache generation were served by both nodes

The release passed 16 deterministic tests, TypeScript checking, Prisma client generation, and a Linux production build.

This evidence did not prove Keycloak login or per-user isolation: the temporary shared-user bypass was active during those checks.

## Resolved issues in 0.4.1

- The internal reverse proxy now preserves the browser-visible port for same-origin mutation checks.
- Asterion's static companion PNG had its strong chroma-key fringe repaired; canvas dimensions and alpha silhouette were preserved. This is a historical, asset-specific repair, not a claim that every animation or enlarged rendering has clean edges.
- The service-worker cache generation was advanced so existing installations can receive the repaired asset.
- First-start health verification and rollback behavior were hardened.

### Remaining artwork limitation

The current Asterion portrait is still only 192 by 208 pixels and uses binary alpha. Enlarging it reveals a jagged silhouette; this website slice does not repair that limitation or replace the approved identity. Animation and atlas assets require their own visual checks and must not be assumed equivalent to the repaired static PNG.

## Pending infrastructure work

- Create and configure the intended Keycloak OIDC client and access assignment.
- Disable the shared-user test mode.
- Configure the external URL and load-balancer route.
- Validate authentication, authorization, per-user isolation, logout, and cross-device continuity.
- Perform production readiness review before any public exposure.

Real endpoints, addresses, credentials, keys, certificates, and host inventories remain outside this public repository.

## Pending product work

- Complete localization of the care interface and event presentation without rewriting historical event content indiscriminately.
- Continue issue #3 with admission, authenticated-session enforcement, account-switch handling, and real ownership-isolation tests; then build issue #4 administration and Keycloak permission synchronization on that foundation.
- Continue the remaining product issues in dependency order, retaining issue #13 as an explicitly deferred design consideration rather than an implemented monitoring feature.
- Establish the Blender-based 3D pipeline described in `docs/3D-ASSET-PIPELINE.md`.
- Build and approve the Asterion 3D vertical slice.
- Add a lazy-loaded WebGL presentation with a resilient 2D fallback.
- Extend the accepted pipeline to the remaining companions.

## Workstation handoff

Use `docs/SECOND-WORKSTATION.md`. A clean Git clone plus tracked instructions is authoritative; copied dependency trees, local build output, chat transcripts, and ignored private files are not.
