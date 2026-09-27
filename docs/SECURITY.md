# Security model

Nexus separates read-only reasoning from externally observable side effects. The control plane requires explicit approval for requests marked `external_side_effect`; upstream applications may implement additional approval controls and their stricter controls remain authoritative.

Secrets are never stored in `sources.lock.json`, `.gitmodules`, provenance payloads by design, or committed configuration. Provider/API credentials stay in environment variables, secret managers, or the native upstream product's credential store. Browser profile data and cookies remain under the browser integration's configured local/runtime storage.

The default infrastructure compose file is for local development. Its development credentials must not be used on a public network. Production deployments should use managed secrets, TLS, network policies, isolated browser/sandbox workers, SSO/RBAC and immutable image digests.
