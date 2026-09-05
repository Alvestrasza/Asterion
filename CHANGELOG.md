# Changelog

All notable changes to Asterion are documented in this file.

## 0.5.0 - 2026-09-05

### Added

- Reproducible second-workstation setup and Git handoff guide
- Durable public-safe agent guidance for fresh Codex project sessions
- Blender-to-GLB companion production and acceptance pipeline
- Public-safe project status snapshot with verified and explicitly pending proof levels
- Public Starfriends introduction with all eight companions and clearly separated available and planned features
- German, English, French, and Spanish public/login message catalogs, browser-language negotiation, and a persistent manual language choice
- Localized loading and error messages, labeled language controls, keyboard navigation, and responsive public-page layout
- Website-foundation scope, route, verification, and deferred-work documentation for the first slice of issues #2 and #5

### Changed

- Move the existing authenticated care prototype to `/care` while keeping `/` independent of authentication and database queries
- Preserve the internal shared-user warning and existing care authorization boundaries at the new route
- Hide the Keycloak sign-in action when any required provider setting is missing or blank
- Keep secure language-preference cookies in normal production while supporting the explicitly isolated internal HTTP test profile
- Advance the public static cache generation and display the application version on the landing page

The care interface and existing event messages are not yet localized. This is an internal-test release, not a public launch or live Keycloak acceptance. It does not implement the diary, social features, device API, or deferred issue #13. The existing low-resolution Asterion silhouette is unchanged. Deployment evidence is recorded separately in the project status.

## 0.4.1 - 2026-09-04

### Fixed

- Preserve the client-visible port through the internal Nginx proxy so same-origin companion actions work on the temporary test listener
- Remove the strong chroma-key fringe from Asterion's static companion PNG without changing its silhouette; this repair did not increase the image resolution or soften its binary-alpha edge
- Refresh the offline asset cache so repaired companion artwork reaches existing installations
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
