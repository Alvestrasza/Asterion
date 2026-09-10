# Chat recovery phases

Phase 1 provides optional chat activation and account-based restoration in a
new browser. This is an implementation candidate requiring real-user acceptance,
not a claim of operator-blind recovery or independent security certification.

Phase 2 is planned to add an independent user-held recovery code of at most
32 characters. It is not implemented by the 0.8.0 source release.

The private diary has a separate confidentiality requirement and must not
silently inherit the phase 1 chat recovery model. Issue #13 remains deferred.

Deployment-specific preparation, credentials and validation evidence are not
published here. See [release notes](RELEASE-0.8.0.md) for current boundaries.
