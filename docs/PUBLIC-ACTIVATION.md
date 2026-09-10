# Public activation boundary

The files in `deploy/public/` are generic templates and guarded helpers, not a
copy of a running environment. Never use placeholder configuration as a live
configuration or treat source publication as permission to activate a service.

`prepare-public.sh` and `activate-public.sh` target first provisioning. They are
not an upgrade procedure for an existing active service. A release upgrade needs
its own reviewed plan, backup, migration acceptance and rollback path.

Build and verify the artifact on the target Linux architecture. Complete the
deployment-specific environment review, identity and database acceptance before
activation. Keep internal and public environments separate. Verify real sign-in,
per-user isolation and the intended user flows before opening general access.

Operational runbooks and private evidence are maintained separately. See
[release notes](RELEASE-0.8.0.md) for the current pilot boundary.
