# 15. Security

Baseline: OWASP ASVS level 2 for the web app, OWASP Top 10 for LLM applications for the AI parts. Every item below maps to a ticket in `18`.

## 1. Identity and access

| Control | Implementation |
|---|---|
| Passwords | argon2id (`argon2-cffi` defaults, time_cost 3, memory 64 MB), minimum 12 characters, checked against a bundled list of the 100k most common passwords |
| Login throttling | nginx 5/min per IP plus app-level 10 failures per account per 15 min, then 15 min lock with audit entry |
| Tokens | Access JWT 15 min (HS256, `DF_JWT_SECRET` at least 32 random bytes). Refresh token 7 days, rotating, stored as sha256, reuse detection revokes the family |
| SSO | OIDC authorisation code flow with PKCE (authlib). Org admins map IdP groups to roles (optional) |
| API keys | 32 random bytes, prefix `df_live_`, stored as sha256, shown once, scoped, revocable, last-used tracked |
| Authorisation | Every repository method takes `org_id` and filters by it. Every route declares its role or scope through a dependency. Unit tests assert that each router function has a permission dependency (introspection test) |
| Tenant isolation tests | Integration suite creates two orgs and tries every endpoint with the other org's ids: all must return 404 |
| Lite mode | Binds to 127.0.0.1. Binding to another interface requires `DF_JWT_SECRET` set explicitly and prints a warning |

## 2. Secrets

- Server: Docker secrets mounted as files, read through `*_FILE` settings. Never in images, never in logs.
- Provider credentials in the database: AES-256-GCM with `DF_SECRETS_KEY`, a random 12-byte nonce per value, associated data = `org_id|provider`. Key rotation: `deckforge secrets rotate` re-encrypts all rows with a new key (old key kept in `DF_SECRETS_KEY_OLD` during rotation).
- Structlog processor redacts keys named `password`, `token`, `api_key`, `secret`, `authorization`, and values matching `df_live_`, `sk-`, `Bearer ` patterns.

## 3. Transport

- TLS 1.2+ at nginx with HSTS. Internal service traffic on a private Docker network. Optional mTLS between hosts in multi-host installs (customer PKI).
- Laya, renderer, LiteLLM, vLLM, SearXNG, PostgreSQL and Valkey never publish ports outside the internal network. Laya and LiteLLM additionally require bearer keys.

## 4. Uploads

`deckforge/security/uploads.py`, applied before any parsing:

1. Size limit (`DF_MAX_UPLOAD_MB`).
2. Magic-byte type detection with `filetype` and must match the allowed list for the declared kind. Extension alone is never trusted.
3. Office files are ZIP containers: open with `zipfile`, reject if any member name contains `..` or is absolute, if member count exceeds 5,000, if total uncompressed size exceeds 20x the compressed size or 500 MB (zip bomb), if `vbaProject.bin` or other macro parts exist, or if the file is encrypted.
4. XML parts parsed with `defusedxml` or `lxml` with `resolve_entities=False, no_network=True` (python-pptx's parser is configured this way in our wrapper).
5. CSV: max 1,000,000 rows, max 500 columns, decoded as UTF-8 with BOM handling, fallback cp1252 with a warning. Cells starting with `=`, `+`, `-`, `@` are treated as text (no formula evaluation anywhere).
6. SVG: sanitised to a safe subset (no scripts, no external references, no `foreignObject`) or rasterised.
7. PDFs are only read for text. No rendering of untrusted PDFs in the API process.
8. Rejected files: status `rejected` with a reason. Stored blob deleted.

## 5. Outbound requests (SSRF)

`deckforge/security/egress.py` wraps every outbound HTTP call made because of user or model input (`fetch_url`, image download, webhooks, customer MCP servers):

- Allowed schemes: `https` (and `http` only if `allow_http` is set for the org).
- DNS is resolved by us, and every resolved address is checked: block loopback, private (RFC 1918), link-local, CGNAT, multicast, IPv6 unique-local and mapped addresses, and cloud metadata addresses (169.254.169.254 and the IPv6 equivalent). The connection is made to the checked IP with the original Host header (prevents DNS rebinding between check and connect).
- Redirects followed manually, at most 5, each hop re-checked.
- Response size cap 10 MB, timeout 20 s, content types limited per use (`text/html`, `application/pdf`, images).
- Optional domain allow-list per org (`DF_FETCH_ALLOWED_DOMAINS` and org setting).
- All requests go through `DF_EGRESS_PROXY` when set.

## 6. LLM-specific risks

| Risk (OWASP LLM Top 10) | Control |
|---|---|
| Prompt injection (direct and indirect) | Untrusted content handling (`10`, section 6), Laya guard, delimiters, no write tools for agents that read external content, tool selection state excludes raw external text |
| Insecure output handling | Every model output validated by Pydantic. Text placed into PPTX through python-pptx APIs (no raw XML from models). Markdown from models rendered in the UI with a sanitising renderer (no raw HTML) |
| Training data poisoning | Laya training uses only system-generated, corpus and install-local data. Customer-derived data never leaves the install. Teacher labels require unanimous self-consistency |
| Model denial of service | Per-role semaphores, run budgets, max slides, max tokens per call, rate limits and quotas |
| Supply chain | Pinned versions with hashes in `uv.lock` and `package-lock.json`, `pip-audit` and `npm audit` in CI, images built from pinned digests, SBOM (syft) published per release, model weights pinned by revision SHA (`LAYA_REVISION`, HF revisions) |
| Sensitive information disclosure | Org-scoped caches and memory, decision log state redaction option, no customer data in shared caches, prompts not logged at INFO |
| Excessive agency | Agents have no write tools, call and tool limits, human approval for storyline by default |
| Overreliance | Every number traced to data, research or a flagged dummy. QA report and reasoning trace shipped with the deck |
| Model theft | Model volumes read-only, internal network only |

## 7. Data protection

- Encryption at rest: customer-managed disk encryption (LUKS, BitLocker, cloud volume encryption). S3 server-side encryption when S3 is used.
- Retention and purge jobs (`04`, section 5). Purge is verifiable (row counts and blob listing in the audit entry).
- PII: optional Presidio-based redaction of names and emails in `decision_log.state_text` and `llm_calls` previews (P12, org setting).
- Data processing record: the admin UI shows which external services an org's data can reach (cloud LLM, search, stock images) given current settings.

## 8. Application hardening

- Containers run as non-root with read-only root filesystems where possible (`tmpfs` for `/tmp`), `no-new-privileges`, dropped capabilities.
- Dependency and image scanning in CI (pip-audit, npm audit, Trivy on images).
- Security headers and CSP at nginx (`14`, section 3).
- Error responses never include stack traces in server mode.
- Audit log for logins, role changes, key creation and revocation, credential changes, settings changes, deletions and exports.

## 9. Security tests (must pass before a release)

| Test | Where |
|---|---|
| Tenant isolation over every endpoint | `tests/integration/test_tenancy.py` |
| Permission dependency present on every route | `tests/unit/api/test_route_permissions.py` |
| Zip bomb, macro file, path traversal, polyglot uploads rejected | `tests/unit/security/test_uploads.py` with fixture files |
| SSRF blocks private, metadata, rebinding and redirect-to-private cases | `tests/unit/security/test_egress.py` (respx + fake resolver) |
| Injection strings in uploaded references do not change tool availability or plan structure | `tests/integration/test_prompt_injection.py` with FakeLLM that would obey injections, asserting the guard path quarantined them |
| JWT tampering, expired tokens, refresh reuse | `tests/unit/api/test_auth.py` |
| Rate limits return 429 with headers | `tests/integration/test_ratelimit.py` |
