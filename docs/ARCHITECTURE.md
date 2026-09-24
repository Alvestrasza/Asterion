# Asterion Architecture

## Purpose

Asterion is an account-backed Tamagotchi-style web service. A user starts with one companion and can unlock up to five independent companions. Their state must remain consistent across devices and web nodes.

## Components

```text
Browser / installed PWA
        |
        | HTTPS + Auth.js session cookie
        v
Reverse proxy / load balancer
        |
        +-------------------+
        |                   |
        v                   v
Next.js node A         Next.js node B
        |                   |
        +---------+---------+
                  |
                  v
          Dedicated PostgreSQL database

Identity: Keycloak OIDC -> Auth.js database session
```

The web nodes are stateless. PostgreSQL is the only authoritative store for pet state, action history, and Auth.js sessions.

## Identity and ownership

Keycloak remains the identity source. Auth.js stores provider accounts and database sessions locally. Every pet row belongs to an Auth.js user; `(ownerId, kind)` is unique, so an account cannot adopt the same kind twice. API handlers derive the owner exclusively from the authenticated server session; no owner identifier is accepted from a request body.

Production authentication fails closed unless `ASTERION_REQUIRED_ROLE` is configured. The configured assignment may be delivered as a Keycloak group, realm role, or client role.

## State model

`Pet` stores the current materialized state:

- birth and last-advance timestamps
- satiety, energy, joy, and bond
- sleeping state
- level, experience, and interaction count
- an immutable companion kind in the public profile
- an optimistic concurrency version

`PlayerProgress` stores a separate account level and XP, the active companion ID,
and the highest unlocked slot count. Slots unlock at account levels 1, 15, 30,
45, and 60, with an absolute maximum of five. Each `Pet` retains its own level,
XP and needs. The same care reward currently advances the account and the cared-for
pet, but the counters are independent. Friend cards show the account level.

The account row also holds the UTC-day XP budget and last rewarded time for each
care action. These fields are committed in the same serializable transaction as
the pet change and `PetEvent.xpAwarded`; a retried request ID cannot award again.
See [progression and needs](PROGRESSION.md) for the versioned curve and pacing.

`PetEvent` stores each pet's journal. A unique `(ownerId, requestId)` constraint prevents a retried browser request from applying to a different pet or awarding account XP twice. Additional adoption has its own durable request ID. Selection changes only `PlayerProgress.activePetId`; it never copies or resets pet state. Public companion deletion, replacement and reset are unavailable.

## Time progression and consistency

Needs advance lazily whenever the pet is read or changed. The server calculates elapsed time, not the browser. Writes run in PostgreSQL `SERIALIZABLE` transactions and additionally require the expected pet version. Serialization failures, creation races, and version conflicts are retried within a small fixed bound.

This design prevents lost updates when two devices or two web nodes act at nearly the same time.

## Offline behavior

An already-open client can queue care actions while disconnected. Each queued action receives its final UUID and pet ID before storage. Reconnection retries the same pair even if another pet is now selected. Legacy one-pet queued actions are assigned to the original pet during migration.

The service worker caches only public artwork, the manifest, immutable Next.js assets, and a generic offline page. It never caches authenticated HTML, API responses, session cookies, or personal pet state. The latest state is kept in a user-keyed browser cache only for continuity in the open application.

## Environment isolation

DEV and PROD must use separate:

- PostgreSQL databases and login roles
- Keycloak clients and required access assignments
- Auth.js secrets
- environment files
- application directories and loopback ports
- systemd units and reverse-proxy upstreams

Database or identity fallback between environments is prohibited.

## Temporary internal test mode

Before the OIDC client exists, an explicit `ASTERION_INTERNAL_TEST_MODE=true` setting may map private-network visitors to one synthetic shared user. The application displays a persistent warning in this mode. The provided temporary Nginx profile is restricted to private source ranges and must not be connected to an Internet-facing load balancer.

This is a deployment bridge, not an alternative identity model. Enabling Keycloak requires disabling the flag and replacing the temporary listener rather than extending it in place.
