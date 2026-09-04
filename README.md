# Asterion

Asterion is a gentle, multi-user Tamagotchi service built as an installable web application. Each authenticated user has one active server-authoritative companion whose state follows them across devices.

## Features

- Keycloak OpenID Connect authentication through Auth.js
- PostgreSQL persistence with one isolated pet per user
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

See [Architecture](docs/ARCHITECTURE.md) and [Operations](docs/OPERATIONS.md) for the full design and rollout procedure.

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
```

## License

No public license has been granted. All rights are reserved.
