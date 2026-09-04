# Asterion Architecture

## Purpose

Asterion is an account-backed Tamagotchi-style web service. A user owns exactly one companion, and that companion must remain consistent when the user changes devices or when requests reach different web nodes.

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

Keycloak remains the identity source. Auth.js stores provider accounts and database sessions locally. Every pet row has a unique foreign key to the Auth.js user row. API handlers derive that user id exclusively from the authenticated server session; no owner identifier is accepted from a request body.

Production authentication fails closed unless `ASTERION_REQUIRED_ROLE` is configured. The configured assignment may be delivered as a Keycloak group, realm role, or client role.

## State model

`Pet` stores the current materialized state:

- birth and last-advance timestamps
- satiety, energy, joy, and bond
- sleeping state
- level, experience, and interaction count
- the currently selected companion kind
- an optimistic concurrency version

`PetEvent` stores the journal and the idempotency key for every command. The `(petId, requestId)` unique constraint guarantees that a retried browser request cannot apply an action twice.

## Time progression and consistency

Needs advance lazily whenever the pet is read or changed. The server calculates elapsed time, not the browser. Writes run in PostgreSQL `SERIALIZABLE` transactions and additionally require the expected pet version. Serialization failures, creation races, and version conflicts are retried within a small fixed bound.

This design prevents lost updates when two devices or two web nodes act at nearly the same time.

## Offline behavior

An already-open client can queue care actions while disconnected. Each queued action receives its final UUID before it is stored. Reconnection retries the same UUID, making an uncertain response safe even if the first request reached the server.

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
