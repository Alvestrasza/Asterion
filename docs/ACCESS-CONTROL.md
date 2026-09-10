# Application access

The pilot supports sign-in, first-companion selection and account administration.
Authentication does not replace per-user authorization. The internal shared-user
test profile is separate from normal accounts and cannot exercise social features.

The source includes server-side access checks and automated regression tests.
Actual identity-provider configuration and real multi-user acceptance must be
verified separately. This document publishes no deployment-specific identities,
permissions or configuration. See [release notes](RELEASE-0.8.0.md).
