# Asterion Agent Guide

## Purpose

Asterion is a multi-user, server-authoritative Tamagotchi-style web service. Preserve its gentle storybook identity, accessible interaction model, and device-independent state.

## Repository rules

- Keep source code, tracked documentation, commit messages, and public GitHub content in English.
- Never commit real hostnames, IP addresses, usernames, passwords, tokens, certificates, fingerprints, connection strings, or raw infrastructure logs.
- Keep machine-specific and operationally sensitive material under `.private/`. It is intentionally excluded from Git.
- Treat `.env.example` and deployment templates as placeholders only.
- Preserve DEV and PROD separation across databases, credentials, OIDC clients, environment files, ports, and release paths.
- Do not weaken authentication, ownership checks, same-origin checks, or the shared-user test warning.

## Technical baseline

- Node.js 22 or newer
- pnpm 11.19.0, pinned by `packageManager`
- Next.js App Router
- React and TypeScript
- Prisma with PostgreSQL
- Auth.js with Keycloak OIDC
- Linux standalone production artifacts

Run the full local validation set before committing functional changes:

```powershell
pnpm install --frozen-lockfile
pnpm test
pnpm check
pnpm build
```

Production artifacts must additionally be built and verified on the target Linux architecture. A successful local build is not deployment acceptance.

## Authoritative project references

- `README.md`: product overview and entry points
- `docs/PROJECT-STATUS.md`: last verified public-safe status and next milestones
- `docs/ARCHITECTURE.md`: application and persistence design
- `docs/OPERATIONS.md`: release, rollback, and acceptance model
- `docs/SECOND-WORKSTATION.md`: reproducible handoff to another computer
- `docs/3D-ASSET-PIPELINE.md`: Blender and web-asset production contract
- `deploy/internal/README.md`: temporary pre-Keycloak evaluation profile

## Companion artwork and 3D assets

- Maintain the established painterly, cute, storybook character language while preserving each companion's distinct silhouette and palette.
- Do not replace approved character art merely because a generated alternative looks polished. Identity preservation is an acceptance requirement.
- Keep transparent boundaries clean and verify alpha independently from color edits.
- Use Blender source files as the editable authority and glTF Binary (`.glb`) as the browser delivery format.
- Keep the current 2D companion presentation as a fallback until the corresponding 3D asset passes mobile performance, animation, accessibility, and identity checks.
- Follow `docs/3D-ASSET-PIPELINE.md` before adding the first binary 3D asset.

## Deployment evidence

Keep these proof levels separate:

1. Tests and static checks pass.
2. A production artifact builds.
3. The service process and listener are healthy.
4. The database-backed readiness endpoint is healthy.
5. A real companion action persists.
6. The same state is observed through both web nodes.
7. Keycloak authentication and per-user isolation are accepted.

Do not claim a later level from an earlier one. The internal shared-user profile cannot prove authentication or per-user isolation.
