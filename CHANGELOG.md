# Changelog

All notable changes to Asterion are documented in this file.

## 0.4.1 - 2026-09-04

### Fixed

- Preserve the client-visible port through the internal Nginx proxy so same-origin companion actions work on the temporary test listener
- Remove chroma-key fringe from Asterion's transparent companion artwork without changing its silhouette
- Retry the internal Nginx health check during first activation and stop an orphaned service during rollback

## 0.4.0 - 2026-09-04

### Added

- Selectable celestial pony, light fairy, celestial dog, and woodland-elf companions
- Transparent companion artwork with distinct silhouettes and color palettes in the established painterly storybook style

### Changed

- The settings dialog now scrolls safely as the companion roster grows
- The offline cache now includes all eight selectable companions

## 0.3.0 - 2026-09-04

### Added

- Selectable rabbit, cat, and young-orc companions alongside Asterion
- Companion-aware care messages and persistent companion selection
- Explicit internal shared-user test mode for the pre-Keycloak evaluation
- Reversible systemd and private-network Nginx installation scripts
- A restricted staged-release dispatcher compatible with the web-node sudo policy
- Interactive database provisioning and migration helpers

### Changed

- The interface now presents the active companion's identity and artwork
- Static companions receive accessible CSS-based reactions while Asterion retains his validated animation set

## 0.2.0 - 2026-09-03

### Added

- Multi-user Next.js application with Keycloak authentication and database sessions
- Dedicated PostgreSQL schema for Auth.js, per-user pets, and event journals
- Serializable server-side mutations with optimistic version checks and idempotency keys
- Same-origin mutation protection and a database-backed health endpoint
- Safe offline action queue and static-only service worker cache
- Sanitized two-node deployment, database bootstrap, and operations templates

### Changed

- Pet progression is now server-authoritative and synchronized across devices
- Save export, restore, and reset now operate against the authenticated user's pet
- Runtime baseline raised from Node.js 20 to Node.js 22

## 0.1.0 - 2026-09-03

### Added

- Installable local-first Tamagotchi-style web application
- Persistent satiety, energy, joy, and bond values
- Feed, play, pet, sleep, and wake interactions
- Real-time and offline progression
- Mood-driven use of Asterion's existing animation set
- Bond levels, experience, companion age, and local journal
- Save export, restore, and confirmed reset
- Responsive and accessible interface
- Offline cache and dependency-free development server
- Deterministic care-engine test suite
