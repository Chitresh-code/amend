# 0003: Account authentication for the web app

Status: Accepted
Date: 2026-08-07

## Context

The web app's login screen (see the UI mockups referenced in [docs/internal](../internal)) is a human email/password login, not the Amend API key bearer-token auth already specified in [PRD §70.1](../PRD.md#701-configuration-model). The PRD never specified a human account layer: it only specifies Amend's own API keys, admin-issued out-of-band for the MVP. A password-based login is a genuinely new requirement, not a rewording of an existing one, so it gets its own decision record rather than silently expanding §70.

Two things needed deciding: how accounts come into existence, and how a logged-in browser stays authenticated across requests.

## Decision

**Account provisioning: admin-provisioned for MVP, matching the existing API key precedent.** PRD §2260 (§70.1) already decided that self-service Amend API key issuance is a post-MVP concern; a self-service signup flow (email verification, password reset, etc.) for accounts is the same category of work and gets deferred for the same reason: it is a real subsystem (email delivery, verification tokens, abuse handling) that is not required to prove the product's core value. Amend operators create accounts for their users for the MVP.

**Session mechanism: server-side sessions in PostgreSQL, referenced by an opaque token in an httpOnly cookie.** Alternatives considered:

- *JWT, no server-side state*: rejected. Revoking a session (logout, account compromise) requires either short-lived tokens with a refresh dance or a server-side denylist, which reintroduces server-side state anyway, with more moving parts than just storing the session.
- *Redis-backed sessions*: rejected for the primary store. Redis is already used for rate limiting (PRD §45.1), which is fine to lose on restart; losing every logged-in user's session on a Redis restart is a worse user experience for no real benefit, and Postgres is already the system of record for everything else caller-scoped (API keys, credentials, conversations).

A session is a random opaque token; only its hash is stored (same pattern as `api_keys.key_hash`, PRD §70.1). The cookie is httpOnly, Secure, `SameSite=Lax`, with a sliding expiration refreshed on use. See [docs/DATA_MODEL.md §1.4a](../DATA_MODEL.md) for `users`/`user_sessions`.

**Identity model: a session resolves to the same `user_id` scope an Amend API key resolves to, not a separate one.** Before this decision, `api_keys` was the caller-identity root that `model_credentials`, `conversations`, and `query_telemetry` all hung off of. That stops being accurate once a human can authenticate without an API key at all (via the web session). `users` becomes the identity root; `api_keys` becomes a secondary, revocable access mechanism issued *to* a user, for programmatic access. Both a browser session and a bearer API key now authenticate to a `user_id`, and everything caller-scoped (BYOK credentials, conversations, rate limits, telemetry) scopes to that `user_id`. See [PRD §72](../PRD.md#72-account-authentication) and the updated `docs/DATA_MODEL.md` §1.4.

**Password hashing: Argon2id.** Current OWASP-recommended default, memory-hard, no dependency the project doesn't already need to add.

**CSRF: required on session-cookie-authenticated endpoints.** Bearer-token auth (`Authorization: Bearer <key>`) is inherently CSRF-safe, since a malicious page cannot set that header on a cross-site request. Cookie auth is not: `SameSite=Lax` covers top-level navigation but not all cross-site state-changing requests, so state-changing endpoints reachable via a session cookie also require a CSRF check when the request did not carry a bearer token.

## Consequences

- New tables: `users`, `user_sessions` (DATA_MODEL.md §1.4).
- `api_keys` gains `user_id`; `model_credentials`, `conversations`, `query_telemetry` are rescoped from `api_key_id` to `user_id` (nullable `api_key_id` retained on `query_telemetry` only, to record which access mechanism made a given request).
- New endpoints: `POST /v1/auth/login`, `POST /v1/auth/logout` (PRD §72).
- `api/app/` gains an auth module distinguishing "session cookie" and "bearer API key" as two ways to resolve the same `user_id`, both feeding the same downstream authorization/rate-limiting/telemetry code, per [ARCHITECTURE.md §4](../ARCHITECTURE.md#4-caller-identity-credentials-and-rate-limiting).
- Self-service signup, password reset via email, and self-service API key issuance all stay explicitly post-MVP; not decided here because the precedent (§70.1) already decided it.
