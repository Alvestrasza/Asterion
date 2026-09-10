# StarFriends 0.8.0

Source publication: 2026-09-10. Status: pilot; final functional acceptance pending.

## Included

- Localized introduction, login navigation and first-companion selection.
- Application account administration and case-preserving player names.
- A collapsible friends panel, friend-code invitations, explicit confirmation,
  and presence and level visibility between confirmed friends.
- Optional one-to-one encrypted text messages and account-based restoration.
- Companion-specific backgrounds and the approved Asterion animation atlas.
- Database migrations, generic deployment templates and automated checks.

The previously published 3D sources, browser models, provenance and regression
checks are preserved. The 3D care view remains opt-in and disabled by default.
Mobile performance and final visual acceptance remain separate work.

## Acceptance boundary

Publishing source does not activate a deployment. Real sign-in, first-companion
selection, two-user friendship, messaging and new-browser continuity must still
be accepted together. Account-based chat recovery is not operator-blind
encryption, and this release is not an independent security certification.

The private diary, device API and later recovery phase are not delivered here.
Issue #13 remains deferred. Operational evidence and private configuration are
maintained outside the published repository.

## Reproduce the source checks

Use Node.js 22 or newer and the pinned pnpm version. Fetch Git LFS assets before
running the checks. Do not copy production environment files into the checkout.

```sh
pnpm install --frozen-lockfile
pnpm test
pnpm check
pnpm build
```

Platform-dependent tests may be skipped on Windows. A Linux build and runtime
acceptance are separate from the local source checks.
