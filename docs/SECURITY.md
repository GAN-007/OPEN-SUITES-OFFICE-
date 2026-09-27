# Security model

Nexus separates source ownership, execution authority, and externally observable
side effects.

The control plane requires explicit approval for requests marked
`external_side_effect`. Vendoring an engine does not bypass that engine's own
authorization, sandboxing, RBAC, browser-profile, or credential controls; the
stricter control wins.

## Secrets

Secrets are not stored in `sources.lock.json`, `engines.runtime.json`,
`engines/VENDOR_MANIFEST.json`, or provenance payloads by design. Provider
keys, OAuth tokens, cookies, browser profiles, database credentials, and model
credentials stay in environment variables, secret managers, or the native
engine's credential store.

Vendored `.env.example` files are templates only. The vendoring workflow
checks out public upstream commits and does not import private developer
worktrees or local secret files.

## Source integrity

- Every engine is pinned to a full commit SHA.
- Vendoring records per-tree SHA-256 fingerprints and file counts.
- CI recomputes the fingerprints.
- CI rejects legacy gitlinks under `upstream/`.
- CI rejects accidental inclusion of GenOffice's separately licensed `ee/`.
- Original license/notice files remain inside each vendored tree.

## Runtime isolation

Production deployments should use per-engine process/container identities,
network policy, TLS, managed secrets, sandboxed browser/terminal workers,
resource limits, audit logging, SSO/RBAC, immutable image digests, backups,
and explicit outbound-network policy.

The root development compose file is not a hardened production deployment.
