# Website foundation

Status: version `0.5.2` website foundation and internal-browser corrections, 2026-09-05.

This work begins issues [#2: public website](https://github.com/Alvestrasza/Asterion/issues/2) and [#5: localization](https://github.com/Alvestrasza/Asterion/issues/5). Neither issue is complete merely because the introduction is available. The foundation was introduced in `0.5.0`; application version `0.5.2` and its matching static-cache generation include the subsequent internal-browser fixes. Deployment evidence is recorded separately in [Project status](PROJECT-STATUS.md).

## Route and access contract

| Route | Behavior | Boundary |
| --- | --- | --- |
| `/` | Public project introduction, eight-companion gallery, and roadmap | Does not call authentication or query PostgreSQL; planned features are labeled as planned |
| `/login` | Localized Keycloak entry point or unavailable-configuration message | Requires nonblank client ID, secret, and issuer before offering sign-in; configuration presence does not prove a working provider |
| `/care` | Existing care prototype moved from the root route | Resolves the current actor before loading that actor's companion; unauthenticated visitors are redirected to login |
| Existing `/api/*` routes | Unchanged API contract | No owner-selection parameter, authorization bypass, or device API is introduced |

The existing internal test flag and persistent shared-state warning are preserved. In that profile, login redirects to the shared care prototype. Normal authenticated login redirects to `/care`. The public introduction must not be treated as permission to expose the existing temporary internal listener to the Internet.

The root page does not create an account, hatch a companion, or load a pet snapshot. Its links into protected routes do not prefetch those routes.

## Localization contract

- Supported languages: German (`de`), English (`en`), French (`fr`), and Spanish (`es`).
- A valid saved manual preference takes precedence over browser language negotiation. English is the fallback when no supported preference can be selected.
- Browser language ranges support regional tags and quality weights. Unsupported or malformed values are ignored.
- The language form validates its input on the server and allows redirects only to `/`, `/login`, or `/care`.
- The preference is a host-scoped, HTTP-only, SameSite-Lax cookie, valid for one year. Normal production uses `Secure`; the explicitly isolated internal HTTP test profile is the exception. Authentication-cookie policy is unchanged.
- Public page metadata, the document language, login text, and loading/error presentation use the selected locale.
- Manual choice is currently browser-local, not a database-backed account setting. Cross-device language preference synchronization is not implemented.
- Existing care controls and historical event messages remain German. The care page marks that region with `lang="de"` and shows a localized notice when another interface language is selected.

No private content is passed to a translation service. Future event localization needs stable message identifiers and structured parameters; stored historical prose must not be overwritten indiscriminately.

## Public presentation

The landing page introduces the project's gentle Tamagotchi-style premise and the eight existing characters. Roadmap cards distinguish future progression, multiple companions, the diary, and social features from the present care prototype. It does not promise that an unfinished safety or privacy feature is already available.

The public interface includes a skip link, labeled language selection, visible keyboard focus, descriptive image text, static character art, reduced-motion support, and responsive layouts. These are implementation measures, not a claim of completed accessibility certification.

### Existing artwork constraint

Asterion's static portrait remains a 192-by-208-pixel image with a binary-alpha silhouette. The historical `0.4.1` repair removed its strong chroma-key fringe without adding resolution or smoothing that silhouette. Large presentations can therefore still look jagged. This slice does not generate replacement artwork, edit image bytes, or certify every GIF/atlas frame. The approved character identity and the existing 2D fallback remain authoritative.

## Verification and evidence limits

Local browser checks have exercised:

- public presentation in all four languages
- manual language selection and persistence across navigation/reload
- login without a configured Keycloak provider
- anonymous care-route redirection to login
- responsive presentation at a 375-pixel viewport, including the corrected overflow condition
- no browser-console errors during these exercised flows

A frozen-lockfile installation, all 33 automated tests, `pnpm check`, and `pnpm build` passed for `0.5.2` on both Windows and Linux. The focused tests cover language negotiation, redirect allowlisting, cookie policy, provider-configuration presence, catalog completeness, secure request IDs, and timezone-stable initial timestamps. The Linux standalone server also passed eight isolated HTTP smoke cases: four supported language headers, unsupported-language fallback, saved preference priority, unavailable-provider login, and anonymous care redirection. Earlier foundation browser checks confirmed persisted language, matching metadata, all eight gallery cards, and no console errors on the isolated standalone server.

The read-only `scripts/check-public-pages.mjs` smoke check targets an isolated local production server with Keycloak and internal shared-user mode disabled and an unreachable placeholder database. It checks language negotiation, metadata/cache boundaries, unavailable login, and anonymous `/care` redirection. Its result must be recorded separately from browser interaction tests and real database-backed acceptance.

Run the smoke check against an isolated production server with `node scripts/check-public-pages.mjs http://127.0.0.1:3000`, replacing only the loopback port as needed. It intentionally checks production cache headers and is not a development-server check. Windows build success is not a Linux deployment artifact or target-runtime acceptance.

The `0.5.2` Linux artifact is deployed on both existing internal nodes. Fresh browser checks confirmed a saved care action, shared state observed through the second node, a working settings dialog, and no console errors on either final care page. No database migration, public cutover, or real Keycloak sign-in was performed. Current and historical evidence remain separate in [Project status](PROJECT-STATUS.md). Shared-user acceptance does not establish session revocation or per-user isolation.

### Corrections discovered on internal HTTP

The actual internal-browser check exposed a request-ID failure that loopback-only checks did not reproduce: `crypto.randomUUID` was absent. The helper now retains the native method where available and otherwise constructs a version-four UUID using `crypto.getRandomValues`; it fails closed if secure randomness is unavailable. Request IDs and existing idempotency checks remain intact. See the browser contracts for [randomUUID](https://developer.mozilla.org/en-US/docs/Web/API/Crypto/randomUUID) and [getRandomValues](https://developer.mozilla.org/en-US/docs/Web/API/Crypto/getRandomValues).

The Linux server and browser also formatted journal timestamps in different timezones during initial rendering. The first label is now deterministic UTC text, followed by the browser's local timezone after hydration; the displayed companion age uses the snapshot timestamp. Stored event times and game rules are unchanged. This addresses the observed [React hydration mismatch](https://react.dev/errors/418) without suppressing warnings or forcing a server timezone on the user.

## Next slices and excluded work

1. Continue #5 with care controls, client feedback, date/number formatting, and event-message presentation.
2. Continue #3 with user admission, session authorization/revocation, account-switch and offline-queue boundaries, and real two-account isolation tests. Provider availability must be validated independently from configuration presence.
3. Build #4 administrative grants, audit, and retryable Keycloak synchronization on the shared authorization foundation. Do not bootstrap an administrator from whichever user happens to register first.
4. Continue progression, multiple companions, achievements, diary, device API, and friendship/chat work in dependency order.

Issue [#13: child-safety support](https://github.com/Alvestrasza/Asterion/issues/13) remains explicitly deferred with no delivery date or selected implementation. This slice adds no diary scanner, alarm recipient, reporting pipeline, content-access hook, or operator plaintext access. Keeping that future topic in mind does not authorize surveillance or weaken the planned client-encrypted diary. Any later proposal must state its data flow, limitations, and consent boundaries explicitly.

The private diary, its key recovery, end-to-end chat, and device pairing are not implemented here. Their privacy properties must be designed and verified before release; the landing-page roadmap is not a security guarantee.
