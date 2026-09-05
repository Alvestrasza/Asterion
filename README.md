# Asterion

Asterion is a gentle, multi-user Tamagotchi service built as an installable web application. Each authenticated user has one active server-authoritative companion whose state follows them across devices.

Version `0.5.2` delivers the website foundation and internal-browser fixes for internal testing, not a public-service launch. The public introduction is at `/`; the existing care prototype has moved to `/care`. Its Keycloak integration and ownership model still require real multi-user acceptance. The internal test profile intentionally shares one test account. Consult the project status for separately verified deployment evidence.

## Features

- Public introduction and login interface in German, English, French, and Spanish, with a saved language preference, browser detection, and English fallback
- Keycloak OpenID Connect integration through Auth.js; the login button is unavailable until the three provider settings are present
- PostgreSQL persistence with one owner-linked pet per user; live authentication and per-user isolation acceptance remain pending
- Eight selectable companions: Asterion, Liora the rabbit, Nyra the cat, Brumo the young orc, Caelo the pony, Selya the fairy, Fenn the dog, and Aelira the elf
- Server-authoritative satiety, energy, joy, bond, age, and experience
- Feed, play, pet, sleep, wake, restore, and confirmed reset interactions
- Serializable transactions and idempotency keys for safe multi-node operation
- Responsive, keyboard-accessible interface using the approved Asterion artwork
- Installable Progressive Web App with a safe static-only offline cache
- Offline action queue that retries with the original idempotency key
- Local JSON export and legacy-save restore
- Database-backed health endpoint at `/api/health`
- Explicit private-network test mode with a visible shared-state warning

## Architecture

The browser communicates only with the Next.js application. Auth.js uses Keycloak for identity and database sessions. Prisma stores pets and their event journal in a dedicated PostgreSQL database. The same build can run on multiple stateless web nodes because all mutable state is in PostgreSQL.

See [Project status](docs/PROJECT-STATUS.md), [Architecture](docs/ARCHITECTURE.md), and [Operations](docs/OPERATIONS.md) for the verified baseline, full design, and rollout procedure.

See [Website foundation](docs/WEBSITE-FOUNDATION.md) for the new route contract and the partial delivery of issues [#2](https://github.com/Alvestrasza/Asterion/issues/2) and [#5](https://github.com/Alvestrasza/Asterion/issues/5). The care interface and stored care-event messages remain German in this slice. Multi-companion progression, the private diary, friendship/chat, and the device API are roadmap work, not available features. Issue [#13](https://github.com/Alvestrasza/Asterion/issues/13) remains explicitly deferred.

## Continue on another workstation

Use the reviewed [second-workstation guide](docs/SECOND-WORKSTATION.md) instead of copying a working directory. It covers the Codex local-project boundary, clean Git handoff, dependency reconstruction, private-file handling, Blender preparation, and acceptance checks.

Durable agent instructions live in [AGENTS.md](AGENTS.md). They are intentionally tracked so a fresh Codex chat can recover the project's technical, security, documentation, and artwork rules from the repository.

## 3D companion roadmap

The planned Blender-to-GLB workflow is defined in [3D asset pipeline](docs/3D-ASSET-PIPELINE.md). The existing 2D presentation remains the default until each model passes identity, animation, mobile-performance, accessibility, fallback, and release checks.

## Local development

Requirements:

- Node.js 22 or newer
- pnpm 11
- PostgreSQL 16 or newer
- A Keycloak OIDC client

Prepare a local environment file from the sanitized template:

```powershell
Copy-Item .env.example .env.local
```

Set local-only values, then install, migrate, and start:

```powershell
pnpm install
pnpm db:migrate
pnpm dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000).

For a temporary internal deployment before Keycloak is available, use the reviewed profile in [Internal test deployment](deploy/internal/README.md). It intentionally shares one test user and must never be exposed through an Internet-facing load balancer.

## Quality checks

```powershell
pnpm test
pnpm check
pnpm build
```

`pnpm build` generates the Prisma client, compiles the production application, and completes the standalone artifact with public and static assets. Build deployment artifacts on the Linux target architecture.

## Security boundaries

- Production sign-in fails closed when `ASTERION_REQUIRED_ROLE` is unset.
- `ASTERION_INTERNAL_TEST_MODE` defaults off and is permitted only on the isolated temporary listener.
- Pet APIs derive the owner from the authenticated server session; callers cannot select another user.
- State-changing requests require a same-origin browser request.
- The service worker never caches authenticated pages, API responses, or session material.
- Runtime and migration database roles are separate.
- DEV and PROD require separate databases, credentials, OIDC clients, and environment files.
- No real hostnames, credentials, certificates, or topology details belong in this repository.

## Project structure

```text
app/                    Next.js routes, UI, API, and global styles
auth.ts                 Auth.js and Keycloak configuration
lib/                    Care engine, database client, and transaction service
prisma/                 Schema and reviewed SQL migrations
public/                 PWA shell and approved Asterion artwork
tests/                  Deterministic domain tests
deploy/                 Sanitized deployment templates
docs/                   Architecture and operations guidance
AGENTS.md               Durable project rules for Codex and contributors
```

## License

No public license has been granted. All rights are reserved.
