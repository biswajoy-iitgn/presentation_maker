# 18. Work breakdown

## 1. How to read a ticket

```text
### T-<phase>.<n> <title>                         Size: S (under half a day) | M (1 to 2 days) | L (3 to 5 days)
Depends on: tickets that must be merged first
Files: files to create (+) or change (~)
Steps: numbered, do them in order
Tests: test files and the cases they must contain
Done when: checklist, each item verifiable by a command or a test
```

Sizes are effort estimates for one implementing agent. They are planning numbers, not commitments.

## 2. Phases

| Phase | Goal | Exit demo | Can run in parallel with |
|---|---|---|---|
| P0 Foundation | Cross-platform base: env, settings, fonts, ports, fakes, CI on three OSes | `uv run poe check` green on macOS, Windows, Linux CI | none (first) |
| P1 Persistence and auth | Database, blobs, API skeleton, auth, projects, files, briefs | Create a user, log in, create a project, upload the example xlsx, create a brief through the API | P3 after T-1.1 |
| P2 Jobs, events, runs | Queue, worker, events, runs API, SSE, rate limits, file profiling, lite single process | Create a run that executes a dummy graph, watch SSE events, cancel and resume | P3 |
| P3 LLM layer | Model registry, local backends, ModelPool router, prompts, structured output, caches, credentials | `deckforge llm try planning.frame_problem --brief examples/...` returns a validated `ProblemOut` from Ollama or vLLM (base open model until DeckForge-LM exists) | P2 |
| P4 Deck graph v1 | LLM planner and composer, deterministic render, QA Tier 0, decisions on fallbacks | Example brief to PPTX end to end through the API with a local model, plan review interrupt in between | P5 from T-4.3 |
| P5 Laya integration | Decision engine, policies, shadow mode, question catalogue, state builders, Laya service | Same run with Laya in shadow mode: decision_log shows paired Laya and fallback answers | P6 |
| P6 Evaluators and repair | Tier 0 to 3 cascade, renderer service, repair loop, slide regeneration | Deck with an injected bad title is repaired automatically, QA report shows before and after | P7, P8 |
| P7 Tools and research | Tool executor, tool catalogue, SSRF-safe fetch, search, Laya tool selection, research agent | A brief needing external data produces cited findings in the deck | P8, P9 |
| P8 Templates | Customer template to DesignSystem, decks built on the template | Upload a corporate template, decks use its masters, colours and fonts | P9 |
| P9 Frontend | Full SPA | Non-technical user completes the whole flow in the browser | P10 |
| P10 Packaging and deployment | Images, compose, nginx, observability, lite installers, CI | Fresh Linux server up with one command, three-OS lite smoke green | P11 |
| P11 Learning loop | Laya fine-tuning, calibration, promotion, eval harness | First `df-laya-v1` promoted for at least three decisions on measured gates | P12 |
| P12 Hardening and scale | Security suite, load tests, backups, Helm, air-gapped bundle, installers, index and partition work | Release candidate checklist complete | P13 to P18 |
| P13 DeckForge-LM | Base model bake-off, data engine, SFT, DPO, GRPO, distillation, exports, CLM heads, `df-vlm`, counterfactual replay (`19`, `24`) | `df-lm-v1` passes the gates in `19` section 6 and replaces the base model on the reference server | P14, P15 |
| P14 Memory and performance | Memory calculator, admission control, degradation ladder, benchmarks, GPU scheduler (`22`) | 4 x 80 GB reference holds 64 concurrent sequences with no OOM and no vLLM preemption at the target load | P13 |
| P15 Agents and protocol | Agent cards, DAP envelope, blackboard, dependency graph, `qa_router`, supervisor and W2, transports, A2A (`20`, `27`) | The P6 demo runs through agents: a bad title goes to copywriter, a label collision to repair_specialist, a wrong number to data_analyst, each fixed and traced | P16, P17 |
| P16 Visual inspector | L2 geometry, L3 pixels, L4 Laya-Vision, L5 regions, L6 clicks, L7 flows (`25`) | A deck with injected overlap, low contrast, off-grid and broken-link defects gets each one found with a bounding box and fixed by its owner | P15 |
| P17 Knowledge base | Card schema, import, build, retrieval modes, DS cards as standards registry, evals, org cards (`28`) | Plan report cites framework, exhibit and standard card ids for every choice, and the KB retrieval eval passes | P15 |
| P18 Product stories and data | Later tables, revisions, variants, diff, comments, review links, notifications, exports (`23`, `26`) | A reviewer comments on a shared link, the comment becomes a revision, the editor approves the new version | P16, P17 |

Critical path: P0, P1, P2, P4, P6, P10. P3 feeds P4. P5 and P11 are the Laya track. P9 can start once P2's API contracts are stable (after T-2.5) using the generated OpenAPI types. P13 (model training) starts as soon as P4 produces traces and runs on vendor GPUs in parallel with P6 to P10. Until `df-lm-v1` passes its gates, every role runs on the base open model with the same prompts, so nothing in P4 to P10 waits for training. P15 re-wraps the P4 to P6 nodes as agents without changing their contracts.

---

## P0 Foundation

### T-0.1 Project tooling with uv and poe          Size: S
Depends on: none
Files: ~`pyproject.toml`, +`uv.lock`, +`.gitattributes`, +`.env.example`, ~`.gitignore`
Steps:
1. Set `requires-python = ">=3.12"`. Keep the existing base dependencies and add the base set from `02` section 2 that both modes need (fastapi, uvicorn[standard], sse-starlette, python-multipart, pydantic-settings, sqlalchemy[asyncio], alembic, langgraph, langchain, langchain-core, langchain-openai, fastembed, httpx, tenacity, jinja2, pyyaml, pandas, openpyxl, pyarrow, pypdfium2, pdfplumber, python-docx, trafilatura, filetype, defusedxml, pyjwt, argon2-cffi, authlib, cryptography, structlog, opentelemetry-sdk, opentelemetry-exporter-otlp, the three instrumentation packages, prometheus-client, platformdirs, orjson, xxhash, fonttools). Pin with `==X.Y.*`.
2. Add extras exactly as in `03` section 6. Add `[project.scripts] deckforge = "deckforge.cli:main"`.
3. Add `[tool.poe.tasks]` for every command in `03` section 5 (use `poe` sequences and `cmd` entries, no shell-specific syntax).
4. Add ruff config (line length 120, rules from `03` section 3) and mypy config (strict for the listed packages).
5. `.gitattributes`: `* text=auto eol=lf`, `*.png binary`, `*.pptx binary`, `*.xlsx binary`, `*.ttf binary`.
6. `.env.example` with every variable from `03` section 4 and a comment line each.
7. Run `uv lock` and commit `uv.lock`.
Tests: none new. Existing tests must still pass with `uv run pytest`.
Done when:
- [ ] `uv sync --extra lite --extra dev` succeeds on a clean checkout.
- [ ] `uv run poe check` runs (it may fail only on mypy for packages that do not exist yet, which are excluded until created).
- [ ] `deckforge --help` prints (CLI stub from T-0.5 may be a placeholder printing "not implemented").

### T-0.2 Test layout and three-OS unit CI          Size: S
Depends on: T-0.1
Files: move `tests/*.py` to `tests/unit/` keeping names, +`tests/conftest.py`, +`tests/unit/conftest.py`, ~`.github/workflows/ci.yml`
Steps:
1. Move existing tests to `tests/unit/` (git mv). Fix relative paths to `examples/` using a `REPO_ROOT` fixture in `tests/conftest.py`.
2. Register markers in `pyproject.toml`: `network`, `integration`, `golden`, `slow`.
3. Default pytest run excludes `network`, `integration`, `golden` (`addopts = "-m 'not network and not integration and not golden'"`).
4. Replace CI with two jobs: `lint-type` (ubuntu) and `unit` (matrix ubuntu, macos, windows) using `astral-sh/setup-uv`, running `uv sync --extra lite --extra dev` and `uv run pytest tests/unit -n auto`.
Tests: existing suite.
Done when:
- [ ] CI is green on all three OSes for the unit job (tests needing network are marked and skipped).

### T-0.3 Bundled fonts and OS-independent text metrics          Size: M
Depends on: T-0.1
Files: +`deckforge/fonts/` (font files and licences), +`deckforge/fonts/fonts.json`, ~`deckforge/render/metrics.py`, +`tests/unit/render/test_metrics_portable.py`, ~`pyproject.toml` (package data)
Steps:
1. Add the fonts from `12` section 4 (download from their official GitHub releases, include each OFL or Apache licence file). Total size under 6 MB.
2. Write `fonts.json`: `{"files": {"Liberation Sans|regular": "LiberationSans-Regular.ttf", ...}, "aliases": {"Arial": "Liberation Sans", "Georgia": "Gelasio", "Calibri": "Carlito", "Cambria": "Caladea", "Times New Roman": "Liberation Serif"}}`.
3. Rewrite `metrics.font_file(name, bold)` to resolve through `fonts.json` only (alias first, then exact family, then fallback to Liberation Sans with a logged warning). Remove the `fc-match` subprocess.
4. Keep the public functions (`text_width_pt`, `wrap`, `text_height`, `fit_size`) with the same signatures.
5. Include fonts as package data (`[tool.setuptools.package-data] deckforge = ["fonts/*"]` or the uv build equivalent).
Tests:
- Known string widths for Arial and Georgia at 12 pt equal fixed expected values (computed once on Linux, asserted on all OSes within 0.01 pt).
- Unknown font falls back to Liberation Sans.
- Existing render tests still pass.
Done when:
- [ ] No reference to `fc-match` remains (`rg fc-match` empty).
- [ ] Unit tests pass on Windows and macOS CI.
- [ ] Example brief renders lint-clean (`python examples/auto_components_margin/build.py out/x`).

### T-0.4 Import boundary test          Size: S
Depends on: T-0.2
Files: +`tests/unit/test_import_rules.py`
Steps:
1. Parse every module under `deckforge/` with `ast`, collect `import` and `from` targets inside `deckforge`.
2. Encode the layer table from `03` section 2 as a dict and assert no module imports a higher layer. Allow-list for `wiring.py`.
Tests: the test itself, plus a fixture-based self-test that a synthetic violation is detected.
Done when:
- [ ] Test passes on the current tree.

### T-0.5 Settings and CLI skeleton          Size: M
Depends on: T-0.1
Files: +`deckforge/settings.py`, +`deckforge/cli.py`, +`tests/unit/test_settings.py`
Steps:
1. Implement `Settings(BaseSettings)` with every variable in `03` section 4, defaults per mode (a `model_validator(mode="after")` fills mode-dependent defaults such as `DF_DATABASE_URL`, `DF_HOST`, `DF_PORT`).
2. `_FILE` support: for each secret field `x`, if env `DF_X_FILE` is set, read the file (strip trailing newline). Implement generically with a validator over a list of secret field names.
3. `get_settings()` cached with `functools.lru_cache`.
4. `deckforge.cli:main` with `argparse` subcommands: `init`, `serve`, `worker`, `migrate`, `doctor`, `secrets`, `eval`, `laya`, `render`, `llm`. Each calls a function in its package (placeholders raise `SystemExit("not implemented yet: T-x.y")`).
Tests: defaults for lite and server, `_FILE` loading from a temp file, invalid mode rejected, data dir resolves via platformdirs.
Done when:
- [ ] `deckforge doctor` prints the resolved settings with secrets masked.

### T-0.6 Core utilities: ids, errors, logging          Size: S
Depends on: T-0.5
Files: +`deckforge/core/ids.py`, +`deckforge/core/errors.py`, +`deckforge/observability/logging.py`, tests
Steps:
1. `new_id()` returns a UUIDv7 string (implement per RFC 9562: 48-bit ms timestamp, version 7, random bits from `secrets`).
2. Error classes from `03` section 3 with `code` and `http_status` class attributes.
3. `configure_logging(settings)`: structlog with contextvars, JSON or console renderer, redaction processor (`15` section 2).
Tests: UUIDv7 ordering and version bits, redaction of each sensitive key and pattern.
Done when:
- [ ] Tests pass, `deckforge doctor` uses the logger.

### T-0.7 Ports, wiring skeleton and fakes          Size: M
Depends on: T-0.5, T-0.6
Files: +`deckforge/ports.py`, +`deckforge/wiring.py`, +`deckforge/testing/__init__.py` and fakes from `17` section 2 (except FakeLLM and FakeLaya bodies, filled in T-3.7 and T-5.1), tests
Steps:
1. Write the `Protocol` classes exactly as in `01` section 5 with full type hints and docstrings.
2. `wiring.build_ports(settings) -> Ports` (a frozen dataclass holding every port). For now, return fakes when `DF_TEST_PROFILE=fake`, raise `NotImplementedError` for real adapters until their tickets land.
3. Implement `FakeBlobStore`, `MemoryCache`, `MemoryEventBus`, `FakeJobQueue`, `NumpyVectorStore`, `FakeRenderer`, `FakeSearch`.
Tests: each fake satisfies its protocol (`isinstance` with `runtime_checkable`), basic behaviour.
Done when:
- [ ] mypy strict passes on `ports.py`, `wiring.py`, `testing/`.

---

## P1 Persistence and auth

### T-1.1 Database models, session and repositories          Size: L
Depends on: T-0.7
Files: +`deckforge/db/models.py`, +`deckforge/db/session.py`, +`deckforge/db/repositories/*.py`, tests
Steps:
1. SQLAlchemy 2 declarative models for every table in `04` section 3, using `Uuid`, `JSON().with_variant(JSONB(), "postgresql")`, `DateTime(timezone=True)`, `ARRAY` only on PostgreSQL with a JSON variant on SQLite (`api_keys.scopes`, `webhooks.events`), `INET` with a `String` variant, `citext` with a `String` variant plus lower-casing in the repository.
2. `session.py`: `create_engine(settings)` (async), `async_sessionmaker`, SQLite pragmas on connect (`journal_mode=WAL`, `foreign_keys=ON`, `busy_timeout=5000`).
3. Repository classes per aggregate (`OrgRepo`, `UserRepo`, `ProjectRepo`, `FileRepo`, `BriefRepo`, `RunRepo`, `RunEventRepo`, `DeckRepo`, `DecisionLogRepo`, `LlmCallRepo`, `ToolCallRepo`, `UsageRepo`, `AuditRepo`, `ModelRegistryRepo`, `DecisionPolicyRepo`). Every method on a tenant table requires `org_id` and filters by it. `Repositories` dataclass groups them for a session.
Tests: CRUD round trip on SQLite for each repo, cross-org access returns `None`.
Done when:
- [ ] All repos tested on SQLite. PostgreSQL tests added in T-1.2 integration.

### T-1.2 Alembic migrations          Size: M
Depends on: T-1.1
Files: +`deckforge/db/alembic.ini`, +`deckforge/db/alembic/env.py`, +`deckforge/db/alembic/versions/0001_initial.py`, +`tests/integration/test_migrations.py`
Steps:
1. Async Alembic env using `DF_DATABASE_URL`. `deckforge migrate` runs `upgrade head`.
2. Migration 0001: on PostgreSQL create schemas `app` and `lg`, extensions `citext` and `vector`, all tables and indexes (including the partial indexes and the HNSW index). On SQLite, create the same tables without schemas, extensions or vector columns (`kb_items.embedding` becomes `vector_json TEXT`).
3. Guard dialect-specific DDL with `if op.get_bind().dialect.name == "postgresql":`.
Tests (integration, testcontainers `pgvector/pgvector:pg17`): upgrade, downgrade, upgrade again. Repository CRUD on PostgreSQL.
Done when:
- [ ] `deckforge migrate` works on SQLite (lite) and PostgreSQL (integration test).

### T-1.3 Blob store adapters          Size: S
Depends on: T-0.7
Files: +`deckforge/storage/fs.py`, +`deckforge/storage/s3.py`, tests
Steps:
1. `FsBlobStore(root)`: key to path via `PurePosixPath(key).parts` joined onto `root`, reject keys with `..`, absolute keys or backslashes. Atomic writes (temp file then `os.replace`). `url()` returns an API download path (signed token added by the API).
2. `S3BlobStore`: boto3 client in `asyncio.to_thread`, presigned GET URLs for `url()`.
3. Wire into `wiring.py` by `DF_BLOB_BACKEND`.
Tests: fs round trip, traversal rejected, atomic overwrite. S3 against a moto-free fake (stub client) for presign shape.
Done when:
- [ ] Ports wired. Windows CI passes the fs tests.

### T-1.4 API skeleton          Size: M
Depends on: T-1.1
Files: +`deckforge/api/app.py`, `deps.py`, `errors.py`, `middleware.py`, `routers/system.py`, tests
Steps:
1. `create_app(settings, ports)`: FastAPI with `/api/v1` prefix routers, OpenAPI at `/api/v1/openapi.json`, lifespan opening DB engine and ports.
2. Middleware: request id (read `X-Request-ID` or generate), structlog context, timing, security of error output.
3. Exception handlers mapping `DeckForgeError` subclasses and validation errors to problem+json (`05` section 5).
4. `/healthz`, `/readyz` (checks DB `SELECT 1`, cache ping, blob write-read of a probe key, and lists optional services status), `/api/v1/system/info`.
Tests: problem+json shape for each error class, readyz degraded output with a failing fake.
Done when:
- [ ] `deckforge serve` (stub using uvicorn) answers `/readyz` in lite mode.

### T-1.5 Authentication and lite init          Size: L
Depends on: T-1.4
Files: +`deckforge/security/passwords.py`, `tokens.py`, +`deckforge/api/routers/auth.py`, ~`deps.py`, +`deckforge/cli_init.py`, tests
Steps:
1. Password hashing (argon2id) and common-password check (bundled list file).
2. JWT encode and decode (claims from `05` section 2), refresh tokens with rotation and family revocation (`refresh_tokens` table).
3. Routes: login, refresh, logout, me, switch-org.
4. Dependencies: `get_principal` (Bearer JWT or API key, T-1.6 adds keys), `require_role(min_role)`.
5. `deckforge init`: create data dir, generate `DF_JWT_SECRET` and `DF_SECRETS_KEY` into `{DF_DATA_DIR}/secrets.env` (permissions 600 where supported), run migrations, create org "Personal" and an owner user, print a one-time login URL with a 10-minute token.
6. Login throttling (account lock after 10 failures in 15 min).
Tests: login success and failure, refresh rotation, reuse detection revokes family, expired token, role checks, lock after failures.
Done when:
- [ ] A user can log in through the API in lite mode and call `/me`.

### T-1.6 API keys and scopes          Size: S
Depends on: T-1.5
Files: +`deckforge/api/routers/org.py` (keys part), ~`deps.py`, tests
Steps: create (returns full key once), list, revoke. `get_principal` accepts `df_live_` keys (sha256 lookup, not revoked, not expired), updates `last_used_at` at most once per minute. `require_scope(scope)` dependency.
Tests: key auth works, revoked key fails, scope missing returns 403 `SCOPE_MISSING`.
Done when:
- [ ] Tests pass. Audit entries written for create and revoke.

### T-1.7 Organisation, members, audit          Size: M
Depends on: T-1.5
Files: ~`routers/org.py`, +`deckforge/api/audit.py`, tests
Steps: org get and patch (settings schema validated), members list, invite (creates user with set-password token), role change, remove, audit listing with cursor pagination. `audit.record(...)` helper used by all admin actions.
Tests: role matrix from `05` section 2.1, last owner cannot be removed, audit rows created.
Done when:
- [ ] Route permission introspection test (T-12.2 extends it) passes for these routes.

### T-1.8 Projects, files, briefs          Size: L
Depends on: T-1.3, T-1.6
Files: +`deckforge/security/uploads.py`, +`routers/projects.py`, `files.py`, `briefs.py`, +`deckforge/api/schemas/*.py`, tests and upload fixtures
Steps:
1. Upload validation pipeline exactly as `15` section 4 (fixture files: valid xlsx, xlsm, zip bomb, traversal zip, encrypted docx, polyglot).
2. Projects CRUD with cursor pagination.
3. File upload: validate, compute sha256 while streaming to the blob store, create `files` row with status `uploaded`, enqueue `file.profile` (data), `template.ingest` (template), `reference.extract` (reference) in the same transaction (the job table exists from T-1.2, queue logic lands in T-2.1: insert rows directly here through `JobRepo.insert`).
4. Briefs create, get, patch with `Brief` validation (T-4.1 will move `Brief` into `core`, create it here first in `core/brief.py`).
Tests: each upload rejection case, tenancy on files and briefs, pagination.
Done when:
- [ ] The P1 exit demo works with `curl` (script in `docs/build/demos/p1.sh` and `p1.ps1`).

---

## P2 Jobs, events, runs

### T-2.1 Job queue (PostgreSQL and SQLite)          Size: L
Depends on: T-1.2
Files: +`deckforge/jobs/queue.py` (`SqlJobQueue`), +`deckforge/jobs/models.py` (`Job`), tests (unit for SQLite, integration for PostgreSQL)
Steps:
1. Implement `enqueue`, `lease`, `heartbeat`, `complete`, `fail(retry: bool)` with the SQL in `06` section 8 for PostgreSQL. `fail(retry=True)` sets `queued` with backoff `run_after = now() + 10 s * 2^attempts` or `dead` when attempts reach max.
2. Reaper task (`reap_expired()`), guarded by `pg_try_advisory_lock(4242)` on PostgreSQL.
3. `listener()` async context manager: PostgreSQL uses a dedicated psycopg connection with `LISTEN jobs_ready` and an `asyncio.Event`. SQLite returns a ticker that fires every second.
4. SQLite lease: same logic in a transaction guarded by a process-wide `asyncio.Lock`.
5. `enqueue` inserts and issues `NOTIFY jobs_ready` in the same transaction (PostgreSQL).
Tests: lease order by priority then time, SKIP LOCKED with two concurrent leasers (integration), org cap respected, heartbeat extends, reaper requeues and dead-letters, SQLite path.
Done when:
- [ ] Two workers never lease the same job in a 1,000-job stress test (integration).

### T-2.2 Worker process          Size: M
Depends on: T-2.1
Files: +`deckforge/jobs/worker.py`, +`deckforge/jobs/handlers.py`, ~`cli.py`, tests
Steps:
1. Worker loop exactly as `06` section 7 with `DF_WORKER_SLOTS`, `DF_WORKER_KINDS`.
2. `HANDLERS` registry `dict[str, Callable[[Job, Ports], Awaitable[None]]]` with a `@handler("kind")` decorator. Register a `noop` handler for tests.
3. Graceful shutdown on SIGTERM and SIGINT (Windows: `signal.SIGINT` and `SIGBREAK` where available): stop leasing, wait up to `DF_WORKER_DRAIN_S` (default 600) for running jobs, then exit.
4. `deckforge worker` CLI command.
Tests: handler exceptions map to retry or not, shutdown drains, slots respected.
Done when:
- [ ] `deckforge worker` processes `noop` jobs from the queue in lite and server modes.

### T-2.3 Event bus and run event sink          Size: S
Depends on: T-1.1, T-0.7
Files: +`deckforge/events/bus.py` (`MemoryEventBus`, `ValkeyEventBus`), +`deckforge/events/sink.py` (`RunEventSink`), tests
Steps: `RunEventSink.emit(type, message, data, stage)` allocates the next `seq` per run (`SELECT coalesce(max(seq), 0) + 1` inside the insert transaction, retry on conflict), inserts `run_events`, then publishes JSON to channel `run:{run_id}`. Valkey bus uses `redis.asyncio` pub/sub.
Tests: seq monotonic under concurrent emits, publish after insert, memory bus fan-out to two subscribers.
Done when:
- [ ] Tests pass on SQLite and PostgreSQL.

### T-2.4 Runs API          Size: M
Depends on: T-2.1, T-1.8
Files: +`routers/runs.py`, +`deckforge/core/run.py` (`RunOptions`, `RunStatus`, `Stage`), tests
Steps: endpoints from `05` section 3.4 except SSE and regenerate. `POST /runs` requires `Idempotency-Key`, checks quotas and rate limits (T-2.6 provides the functions, stub them first), inserts the run and a `run.execute` job in one transaction. `resume` validates `kind` against `pending_input`, stores `resume_payload`, enqueues `run.resume`. `cancel` sets the flag.
Tests: idempotent replay, resume kind mismatch 409, resume when not waiting 409, tenancy.
Done when:
- [ ] Creating a run produces a job that the `noop` worker completes (temporary handler).

### T-2.5 Server-sent events          Size: M
Depends on: T-2.3, T-2.4
Files: +`deckforge/api/sse.py`, ~`routers/runs.py`, tests
Steps: implement `05` section 4 with `sse-starlette`: replay from `run_events` after `Last-Event-ID` or `after`, then live subscription, ping 15 s, end on terminal status. Event token endpoint (`POST /runs/{id}/events/token`, signed with `itsdangerous`-style HMAC using `DF_JWT_SECRET`, 60 s, bound to run id and user id). JSON polling variant.
Tests: replay correctness, reconnect without gaps (emit while disconnected), token expiry, terminal close.
Done when:
- [ ] A browser `EventSource` on a test page receives events from a run driven by a test handler.

### T-2.6 Rate limits, quotas, usage ledger          Size: M
Depends on: T-1.4
Files: +`deckforge/api/ratelimit.py`, +`deckforge/api/ratelimit.lua`, +`deckforge/accounting/usage.py`, +`config/limits.yaml`, tests
Steps: token bucket in Valkey via Lua (`EVALSHA`), in-memory equivalent for lite. Middleware applies `default_rps_per_user`. Named limits callable from routes (`runs_per_hour_per_user`, ...). `UsageRecorder.add(org, metric, qty, user, run)`. Quota check with a 60 s cached aggregate. Headers per `05` section 6.1.
Tests: bucket refill maths, 429 with headers, quota exceeded on run creation.
Done when:
- [ ] Limits read from `config/limits.yaml`, overridable by env for org run cap.

### T-2.7 Data file profiling job          Size: L
Depends on: T-2.2, T-1.8
Files: +`deckforge/ingest/tables.py`, +`deckforge/ingest/semantic_rules.py`, +`deckforge/core/dataset.py`, handler `file.profile`, tests with fixture workbooks
Steps:
1. Read xlsx with openpyxl (`read_only=True, data_only=True`), detect tables per sheet (contiguous non-empty blocks with a header row: first row where at least 60% of cells are non-numeric strings), CSV with pandas (`sep=None, engine="python"`, max rows).
2. Clean: strip header whitespace, de-duplicate header names, coerce numeric strings ("1,234", "12%", "₹5,000") to numbers recording units.
3. `ColumnProfile` per column. Semantic type by rules (year-like integers 1900 to 2100 or date dtype gives `time`, ISO country codes or known place names give `geo`, `%` gives `ratio`, currency symbols give `currency`, low-cardinality strings give `category`, else `measure` or `text`). Rules return a confidence. Low-confidence columns are marked for `D_COLUMN_ROLE` (P5 wires the decision, until then the rule result stands).
4. `TableProfile.summary` written by code (template sentence per role).
5. Save each cleaned table as parquet (`pyarrow`) to the blob store. Update `files.profile` and status `ready`.
Tests: the example workbook from `examples/auto_components_margin` converted to xlsx fixture, messy fixture (merged header cells, notes rows, units in headers), CSV with semicolons, Indian number formats.
Done when:
- [ ] Uploading the example xlsx through the API yields `ready` with correct semantic types for every column.

### T-2.8 Lite single-process serve          Size: M
Depends on: T-2.2, T-2.5
Files: ~`deckforge/cli.py`, +`deckforge/api/static/` (placeholder index.html until P9), +`deckforge/serve.py`, tests
Steps: `deckforge serve` in lite mode runs uvicorn programmatically with the app and starts the worker loop as a background task in the app lifespan (same event loop, `DF_WORKER_SLOTS`). Mount `StaticFiles(directory=static, html=True)` at `/` after API routes. `--reload` for development (worker disabled under reload, `deckforge worker` run separately).
Tests: startup and shutdown cleanly, a noop run completes in-process.
Done when:
- [ ] P2 exit demo: create a run (noop graph), watch SSE, cancel works, in lite mode on all three OSes (manual check recorded in PR, automated in T-10.5).

---

## P3 LLM layer

### T-3.1 Model config and registry          Size: M
Depends on: T-0.5
Files: +`config/models.yaml`, +`config/model_pools.yaml`, +`config/pricing.yaml`, +`deckforge/llm/config.py`, +`deckforge/llm/registry.py`, tests
Steps: Pydantic models for the YAML (`07` section 3) with `${VAR:-default}` interpolation: roles (model role, default adapter, thinking flag, max tokens, temperature), profiles (`server`, `laptop`, `test`), `agent_adapters` (agent id to adapter name), backends (`vllm_pool`, `ollama`, `llamacpp`, `fake`). `ModelRegistry.chat_model(role, adapter=None, org=...)` picks the profile (org `model_profile`, else default per mode), resolves the adapter (explicit, else the agent's adapter, else the multitask model) and returns a cached chat model per (profile, role, adapter). There are no cloud providers and no cloud gate (D16).
Tests: profile selection, adapter resolution order, interpolation, thinking flag mapped to `extra_body={"chat_template_kwargs": {"enable_thinking": ...}}` for vLLM, cached instances per key.
Done when:
- [ ] `deckforge llm ping --role planner` sends a one-line request to the configured local endpoint (manual, documented).

### T-3.2 Prompt files, loader and renderer          Size: M
Depends on: T-3.1
Files: +`deckforge/prompting/loader.py`, `render.py`, `filters.py`, +`prompts/LOCK.json`, +`prompts/_example/hello.md`, tests
Steps: parse front matter (YAML between `---` lines) into `PromptSpec`, sections by `## name` headings, Jinja2 `Environment(undefined=StrictUndefined, autoescape=False)` with filters `to_yaml`, `table_md`, `truncate_tokens`. `RenderedPrompt(messages, prompt_id, version, hash, stable_prefix_len)`. `LOCK.json` maps prompt id to version and text hash, a test fails when text changed without a version bump.
Tests: render, undefined variable error, lock check, section ordering.
Done when:
- [ ] `deckforge llm render planning.frame_problem --fixture <file>` prints messages (once that prompt exists in T-4.6).

### T-3.3 Structured calls, repair, usage          Size: L
Depends on: T-3.2, T-1.1
Files: +`deckforge/llm/call.py`, +`deckforge/llm/usage.py`, +`deckforge/llm/errors.py`, tests
Steps: implement `structured()`, `text()`, `vision()` per `07` section 4, `UsageCallback` writing `llm_calls` and usage, error mapping to `ProviderError`, pool reservation through `ModelPool.reserve()` before each call and release after (T-3.4), timeouts.
Tests (with FakeLLM and a fake chat model that returns invalid JSON first): repair path, schema failure raises `ValidationFailed`, timeout maps to retryable error, usage rows written with token counts.
Done when:
- [ ] Coverage of `call.py` at least 90%.

### T-3.4 Local backends and ModelPool router          Size: L
Depends on: T-3.3
Files: +`deckforge/llm/backends/vllm_pool.py`, `ollama.py`, `llamacpp.py`, +`deckforge/llm/pool.py` (ModelPool), +`deckforge/llm/pool_metrics.py`, +`deckforge/llm/budget.lua`, tests
Steps:
1. `VllmPoolBackend` builds `ChatOpenAI(base_url=<replica>, api_key=<pool key>, model=<adapter or base name>, max_retries=0, extra_body=...)`. Tool calls use the hermes parser that the replicas run with. Structured output uses JSON schema mode.
2. `ModelPool` per `22` section 6.1: reads each replica's `/metrics` every 5 s (`vllm:kv_cache_usage_perc`, `vllm:num_requests_running`, `vllm:num_requests_waiting`), routes by load with adapter affinity and run (prefix) affinity, marks a replica down after 3 failed scrapes.
3. Token budget reservation per `22` section 6.2: `reserve(pool, priority, est_tokens)` runs `budget.lua` in Valkey (lite: in-process counter), release returns unused tokens. Priority classes: interactive, run, background.
4. `OllamaBackend` and `LlamaCppBackend` for laptops (OpenAI-compatible endpoints, JSON schema format, model names from the laptop profile).
Tests: router picks the least loaded replica, affinity wins within a load band, down replica skipped, budget reservation and release with a fake Valkey, backend request shapes recorded with respx.
Done when:
- [ ] Two fake replicas behind the pool share 100 concurrent requests within 10% of each other in a unit test, and a dead replica gets no traffic after 15 s.

### T-3.5 Cache adapters and LLM response cache          Size: M
Depends on: T-0.7, T-3.3
Files: +`deckforge/cache/memory.py`, `sqlite.py`, `valkey.py`, `keys.py`, `locks.py`, ~`deckforge/llm/call.py`, tests
Steps: implement the `Cache` port for the three stores (SQLite table `cache_entries(key text primary key, value blob, expires_at)` in the lite DB), key builders exactly as `11` section 2, stampede lock (`11` section 3), LLM cache layer in `structured()` honouring `cacheable` front matter and run option `fresh`.
Tests: TTL expiry, org id mismatch treated as miss, lock contention, key stability across runs of canonical JSON.
Done when:
- [ ] Second identical deterministic call returns from cache with an `llm_calls` row marked `cache_hit`.

### T-3.6 Credential store          Size: S
Depends on: T-1.1
Files: +`deckforge/security/crypto.py`, +`deckforge/security/credentials.py`, ~`routers/org.py`, tests
Steps: AES-256-GCM encrypt and decrypt with associated data `org_id|provider`, `CredentialStore.get(org, provider)` falls back to install-wide env keys. Admin endpoints from `05` section 3.2. `deckforge secrets init|rotate`.
Tests: round trip, tampered ciphertext fails, rotation re-encrypts.
Done when:
- [ ] Search and connector adapters read their keys through the store. The model pool key is read from the `pool_key` secret file, never from the database.

### T-3.7 FakeLLM and fixtures          Size: S
Depends on: T-3.3
Files: ~`deckforge/testing/fake_llm.py`, +`tests/fixtures/llm/`, tests
Steps: implement `FakeLLM` per `17` section 2, returning a fake `BaseChatModel` whose `with_structured_output` returns parsed fixture objects, recording calls. Helper `record_fixture()` to save real outputs during manual runs.
Tests: lookup by prompt id and input hash, scripted errors.
Done when:
- [ ] Graph tests in P4 can run fully offline.

---

## P4 Deck graph v1

### T-4.1 Core domain models          Size: M
Depends on: T-0.7
Files: +`deckforge/core/{brief,dataset,facts,research,design,quality,decision,events,run}.py`, ~`deckforge/core/__init__.py`, tests
Steps: write every model in `04` section 2 exactly (field names and types are contracts). Add `RunOptions.research_enabled` property (option value, else brief `allow_research` and org setting).
Tests: JSON round trips, validators, enum values.
Done when:
- [ ] mypy strict passes on `deckforge/core`.

### T-4.2 Exhibit data models and adapter refactor          Size: L
Depends on: T-4.1
Files: +`deckforge/core/exhibit_data.py`, ~`deckforge/story/render.py`, ~`examples/auto_components_margin/build.py`, tests
Steps: one Pydantic model per `EXHIBITS` key with exactly the fields each adapter reads today (read every `_ex_*` function and `examples/auto_components_margin/data.json`). Discriminated union `ExhibitData`. Adapters accept the model (keep a thin dict-to-model shim for the example). Each model gets `.summary() -> str` (one line for prompts and Laya state builders) and `.profile() -> DataProfile` (for the selector).
Tests: example data validates for every exhibit, invalid data rejected with clear errors, the example deck renders identically (XML snapshot before and after).
Done when:
- [ ] Example build lint-clean and byte-identical slide XML (allowing ids).

### T-4.3 Graph runtime: state, context, worker handlers, checkpointers          Size: L
Depends on: T-2.2, T-2.3, T-4.1
Files: +`deckforge/graphs/state.py`, `context.py`, `events_map.py`, `checkpoint.py`, `deck.py` (skeleton with stub nodes), +`deckforge/jobs/run_handlers.py`, tests
Steps: state and context exactly as `06` sections 3 and 4. `checkpoint.py` builds `AsyncPostgresSaver` (run `setup()` once at worker start) or `AsyncSqliteSaver`, and the node cache (`RedisCache` or `SqliteCache`). `run_handlers.execute_run` and `resume_run` exactly as `06` section 7 (interrupt handling, cancellation, status updates, events). Graph compiled once per process. Stub nodes return minimal valid state so the graph completes.
Tests: interrupt then resume, crash in a node then re-lease continues from checkpoint (inject failure on first attempt), cancellation, events order.
Done when:
- [ ] Stub graph runs through the API with SSE events in lite mode.

### T-4.4 Intake subgraph          Size: M
Depends on: T-4.3, T-3.3, T-2.7
Files: +`deckforge/graphs/intake.py`, +`deckforge/graphs/nodes/intake_nodes.py`, +`prompts/intake/normalise_brief.md`, `prompts/intake/clarify_questions.md`, tests
Steps: nodes from `06` section 5.4. Decisions go through `runtime.context.decisions` (P4 uses `PolicyDecisionEngine` with `NullLaya` once T-5.2 exists, until then a temporary `FallbackOnlyDecisionEngine` in `deckforge/decisions/fallback_only.py` that calls the fallback directly). `clarify` interrupt node with the payload from `05` section 3.5.
Tests: brief with missing audience triggers clarification, `ask_clarifications=false` records assumptions, answers merge into the brief.
Done when:
- [ ] Example brief passes intake with FakeLLM fixtures.

### T-4.5 Knowledge base and vector stores          Size: M
Depends on: T-1.2, T-0.7
Files: +`deckforge/knowledge/frameworks.py` (parse `docs/FRAMEWORK_LIBRARY.md` into cards, later replaced by the card importer in T-17.1), +`deckforge/knowledge/embed.py` (fastembed wrapper), +`deckforge/storage/vectors_pg.py`, `vectors_numpy.py`, CLI `deckforge kb build`, tests
Steps: parse the library into `FrameworkCard(id, name, family, when_to_use, message_types, data_needed, exhibit_hints)`. Embed `name + when_to_use`. Upsert into `kb_items` namespace `frameworks`. Numpy store loads vectors from `vector_json`, cosine top-k. pgvector store with HNSW cosine query.
Tests: parser covers every entry in the library (count matches), search for "margin decline drivers" returns a bridge-type framework in the top 5.
Done when:
- [ ] `deckforge kb build` runs in lite and server modes.

### T-4.6 Planning subgraph and plan review          Size: L
Depends on: T-4.4, T-4.5
Files: +`deckforge/graphs/planning.py`, +`deckforge/graphs/nodes/planning_nodes.py`, +`deckforge/llm/schemas.py` (planning outputs from `07` section 5), +`prompts/planning/{frame_problem,issue_tree,revise_issue_tree,pick_frameworks,storyline,revise_storyline}.md`, +`deckforge/story/validators.py`, tests
Steps: implement the subgraph in `06` section 5.4 with validators, revision loops (max 2), Plan assembly into the existing `Plan` model, and the `plan_review` interrupt node with edit validation (`validate_edited_plan`: same validators, analyses reference existing issues, slide ids unique).
Tests: validators (each rule has a failing and a passing case), revision loop stops at 2, edited plan accepted or rejected with `PLAN_INVALID`, FakeLLM end to end of planning for the example brief producing a plan equivalent in structure to `examples/auto_components_margin/plan.json`.
Done when:
- [ ] Planning on a real local model produces a valid plan for the example brief (manual run log attached to PR).

### T-4.7 Data binding, dummy data, facts          Size: L
Depends on: T-4.6, T-4.2
Files: +`deckforge/graphs/nodes/data_nodes.py`, +`deckforge/data/dummy.py`, +`deckforge/data/calcs.py` (recipe registry), +`deckforge/data/mapping.py`, tests
Steps:
1. `bind_data`: for each analysis, find the table (`dataset_table_id`), map columns to the exhibit data model fields using semantic types and names (rules first, extractor LLM with a small schema when ambiguous). Missing data and `allow_dummy_data`: generate dummy data with `dummy.py` (plausible ranges by unit and semantic type, seeded by analysis id, every value flagged) and set `sticker="ILLUSTRATIVE"` downstream.
2. `compute_facts`: calc recipes keyed by framework id and message type (start with the recipes the example uses: growth, CAGR, bridge shares, profit pool shares, benchmark gaps, value at stake, run-rate). Each recipe returns `Fact` objects with provenance. Move the logic of `examples/auto_components_margin/build.py:compute_facts` into recipes.
3. Reconciliation checks as assertions inside recipes (sums equal totals, shares sum to 100% within rounding).
Tests: example brief facts equal the current `facts.json`, dummy generator determinism, missing column handling.
Done when:
- [ ] Facts for the example match the existing hand-built facts exactly.

### T-4.8 Slide composer subgraph          Size: L
Depends on: T-4.7
Files: +`deckforge/graphs/compose.py`, +`deckforge/graphs/nodes/compose_nodes.py`, +`prompts/compose/{write_copy,exec_summary,decisions,agenda}.md`, tests
Steps: nodes from `06` section 5.4 (`choose_exhibit`, `shape_exhibit_data`, `write_copy`, `check_copy`, `pick_assets`). Archetype-specific prompts for exec summary rows, decision cards, agenda questions. Title fit check uses metrics and the design system title size (at most 2 lines). Icons: embedding search over a Lucide index (`kb_items` namespace `icons`, built by `deckforge kb build --icons` from the bundled Lucide names and tags).
Tests: typed numbers rejected and rewritten, unknown fact token rejected, exhibit fallback to second candidate on data validation failure, icon selection deterministic.
Done when:
- [ ] All 14 slides of the example compose with FakeLLM fixtures, and with a real local model produce a deck that passes Tier 0 (manual log).

### T-4.9 Render, finalize, artifacts, plan report          Size: M
Depends on: T-4.8
Files: +`deckforge/graphs/nodes/render_nodes.py`, ~`deckforge/story/render.py` (accept `DesignSystem` from families for now), +`deckforge/renderer/soffice.py` (lite), +`deckforge/renderer/rasterize.py`, tests
Steps: `assemble_plan` orders composed slides, `render_deck` compiles with the existing renderer in `asyncio.to_thread`, runs lint and repair, saves PPTX, renders previews through the `PreviewRenderer` port (SofficeRenderer or Null), creates `deck_versions`, `slides`, `artifacts` rows, emits `slide.rendered` and `artifact.ready`. `finalize` writes the plan report (existing `report()`), facts JSON, QA placeholder (Tier 0 only, full cascade in P6), sets status.
Tests: deck version increments, artifacts stored, previews skipped gracefully without LibreOffice.
Done when:
- [ ] P4 exit demo works through the API.

### T-4.10 End-to-end graph tests          Size: M
Depends on: T-4.9
Files: +`tests/unit/graphs/test_deck_graph_e2e.py`, +`tests/fixtures/llm/...` for the example brief
Steps: record fixtures from one real run (or write them by hand from the existing plan.json and data.json), run the whole graph offline with interrupts auto-answered, assert final deck passes lint and look-and-feel and storyline consistency, events contain every stage, crash injection in `render_deck` resumes.
Done when:
- [ ] Test runs in under 60 s on CI and passes on all three OSes.

---

## P5 Laya integration

### T-5.1 Decision engine backends and question registry          Size: L
Depends on: T-4.1, T-3.3
Files: +`deckforge/decisions/engine.py` (port re-export), `spec.py` (`QuestionSpec`), `registry.py`, `backends/null.py`, `backends/http.py`, `backends/inproc.py`, +`tests/fixtures/laya/*.json`, ~`deckforge/testing/fake_laya.py`, tests
Steps:
1. `QuestionSpec` Pydantic model matching the YAML in `09` section 2.4. Registry loads all YAMLs at startup, validates option counts (at most 12), description lengths (at most 20 words), forbidden keys (`yes`, `no`, `true`, `false` in choice questions).
2. Raw backend interface: `async def predict(questions: dict, states: list[str], checkpoint: str, min_confidence: float | None) -> list[dict]` returning the raw answer dicts.
3. `HttpLaya` per `09` section 2.3 (single and batch endpoints, auth header, retry once, circuit breaker 30 s, `Retry-After`).
4. `InprocLaya`: lazy `laya.Router(max_loaded=1)` (import inside the function so the package stays optional), calls `predict` or `predict_batch` in `asyncio.to_thread`, guarded by an `asyncio.Lock` (one forward pass at a time per process, MPS-safe).
5. `NullLaya`: every answer `abstained`.
6. Response mapping function `to_answer(raw, qspec) -> (answer, probabilities, confidence, abstained)` tested against fixtures.
7. `FakeLaya` scripted backend.
Tests: registry validation errors, HTTP backend with respx (success, 503 then success, breaker opens), mapping for choice, score and noul fixtures, inproc backend skipped unless `laya` installed (`pytest.importorskip`).
Done when:
- [ ] Contract test suite runs against Fake, Null and Http backends with identical expectations.

### T-5.2 Policy decision engine          Size: L
Depends on: T-5.1, T-3.5
Files: +`deckforge/decisions/policy.py` (`PolicyDecisionEngine`), `rotation.py`, `fallbacks.py`, `rules.py`, ~`wiring.py`, tests
Steps: algorithm in `09` section 4 (modes, thresholds by option-count bucket, rotation averaging for at most 6 options, decision cache, decision log rows, shadow tasks with a 1 s budget and exceptions swallowed and logged, 5% audit sample in `laya_first`). Fallbacks: `llm` (render `prompts/decisions/<id>.md`, judge role, schema `{answer, confidence_0_to_1, reason}` with `answer` restricted to the option keys), `rule` (function registry), `default`. Policies loaded from `decision_policies` with a 60 s refresh, default mode from YAML `default_mode` (`shadow` when `DF_LAYA_MODE != off`, else `llm_only`). Replace the temporary `FallbackOnlyDecisionEngine`.
Tests: each mode, rotation maths (hand-computed example), threshold per bucket, shadow never blocks (timing assertion with a slow fake), cache hit path, log row contents, audit sampling rate.
Done when:
- [ ] All nodes from P4 use `PolicyDecisionEngine` and the example graph test still passes.

### T-5.3 State builders          Size: M
Depends on: T-4.2
Files: +`deckforge/context/state_builders.py`, +`deckforge/context/tokens.py`, tests
Steps: implement every builder named in the catalogue (`brief_state_v1`, `column_state_v1`, `table_state_v1`, `issue_state_v1`, `exhibit_state_v1`, `icon_state_v1`, `tool_state_v1`, `defect_state_v1`, `title_exhibit_state_v1`, `slide_desc_state_v1`, and the judge states) following `10` section 5. Token counting via the Laya tokenizer when importable, else approximate with a 20% margin.
Tests: each builder deterministic, under 380 tokens on oversized inputs (hypothesis-generated long texts), truncation order respected.
Done when:
- [ ] Every catalogue entry's `state_builder` resolves to a function.

### T-5.4 Question catalogue files and fallback prompts          Size: M
Depends on: T-5.1, T-5.3
Files: +`deckforge/decisions/questions/*.yaml` (all ids in `09` section 3), +`prompts/decisions/*.md`, +`deckforge/decisions/rules.py` entries, tests
Steps: write each YAML with instructions, criteria (neutral keys, at most 20 words each), state builder, fallback, defect map for judges, cache scope. Write the fallback prompt for each `llm` fallback.
Tests: registry loads all files, each fallback prompt renders, each judge's defect map covers all non-passing options.
Done when:
- [ ] `deckforge laya questions --validate` passes.

### T-5.5 Wire decisions into nodes          Size: M
Depends on: T-5.2, T-5.4
Files: ~intake, data, planning, compose nodes, ~`deckforge/ingest/tables.py`
Steps: replace rule-only or LLM-only logic at each catalogue location with `runtime.context.decisions.decide(...)` (or `decide_batch` for columns and icons). Keep behaviour identical when Laya abstains (fallback equals previous logic).
Tests: node tests with FakeLaya answers (confident, abstain) take the right branch.
Done when:
- [ ] Decision log contains rows for every catalogue decision after one example run.

### T-5.6 Laya service image and health          Size: M
Depends on: T-5.1
Files: +`deploy/docker/Dockerfile.laya`, +`deploy/docker/laya/entrypoint.sh`, +`deckforge/decisions/pull.py` (CLI `deckforge laya pull`), ~`routers/system.py` (`/readyz` lists Laya status), +`routers/admin_decisions.py` (read-only policies and metrics), tests
Steps: Dockerfile per `09` section 2.1 (CPU and GPU variants via build arg). `deckforge laya pull --to <dir>` downloads base checkpoints with `huggingface_hub.snapshot_download(revision=<pinned sha>)` (needs network, documented). Readiness pings `GET /health` with the key.
Tests: readyz shows Laya degraded when unreachable (respx), admin endpoint permissions.
Done when:
- [ ] `docker compose --profile laya up laya` serves `/v1/systemone` with the base checkpoint (manual, in an environment with Hugging Face access).

### T-5.7 Outcome labelling hooks          Size: S
Depends on: T-5.5
Files: +`deckforge/decisions/outcomes.py`, ~files profile patch route, ~plan review node, ~regenerate flow (T-6.9 calls it)
Steps: write `outcome_label` on the matching decision rows when users correct column types, edit the plan (framework changes, deck type), or regenerate a slide choosing a different exhibit. Include `labeler` and `at` in the JSON.
Tests: correction updates the right row.
Done when:
- [ ] P5 exit demo: decision log shows paired shadow answers and outcome labels after a run with one user correction.

---

## P6 Evaluators and repair

### T-6.1 Tier 0 aggregator and defect catalogue          Size: M
Depends on: T-4.9
Files: +`deckforge/evaluators/tier0.py`, +`deckforge/evaluators/codes.py`, ~`deckforge/qa/lookfeel.py` (expose rule results as codes), tests
Steps: run lint, look-and-feel, consistency (generalised: matrix vs roadmap when both exhibits exist, numbers in decision cards equal facts), fact resolution, typed numbers, font sizes, missing sources. Produce `Defect` objects with codes and severities from `09` section 6.1. Add `renderer_version` constant.
Tests: one fixture deck per code that triggers exactly that code.
Done when:
- [ ] Example deck produces zero blockers, and each fixture triggers its code.

### T-6.2 Tier 1 and Tier 2 judges with escalation          Size: L
Depends on: T-6.1, T-5.5
Files: +`deckforge/evaluators/tier1.py`, `tier2.py`, `cascade.py`, +`prompts/judge/*.md` (one per judge, plus `J2_STORYLINE`, `J2_EXEC_SUMMARY`, `J2_FACTUALITY`), tests
Steps: Tier 1 batches all slide-level judges in one `decide_batch` per judge. Escalation rules exactly as `09` section 6. Shadow-mode rule: Tier 1 findings create defects only after Tier 2 confirmation. Deck-level Tier 2 judges run once per deck version.
Tests: escalation on abstain, confirmation flow, disagreement logged, deck-level judges called once.
Done when:
- [ ] Injected bad title in a fixture deck is flagged as `TITLE_UNSUPPORTED` with Tier 2 evidence.

### T-6.3 Renderer service and remote rendering          Size: L
Depends on: T-4.9
Files: +`deckforge/renderer_service/app.py`, `pool.py`, +`deploy/docker/Dockerfile.renderer`, +`deploy/docker/renderer/fonts.conf`, +`deckforge/renderer/http.py` (`HttpRenderer`), tests
Steps: per `12` section 5.1: unoserver pool, convert endpoint, timeouts and restarts, health. Verify the unoserver 3.7 client call shape and pin it in code. `HttpRenderer` posts PPTX and rasterises locally.
Tests: pool logic with a fake converter (unit), real conversion in the `golden` CI container (integration).
Done when:
- [ ] Six concurrent conversions complete without profile lock errors in the container.

### T-6.4 Tier 3 vision judge          Size: M
Depends on: T-6.2, T-6.3
Files: +`deckforge/evaluators/tier3.py`, +`prompts/judge/visual.md`, tests
Steps: render PNG at 144 dpi, call `vision()` with the rubric (`09` section 6), map low scores to defects, budget modes (all, flagged, off) from run options and org settings.
Tests: FakeLLM vision outputs mapped to defects, budget mode respected.
Done when:
- [ ] Final QA report includes visual scores per slide when enabled.

### T-6.5 Exhibit groups with embedded data          Size: M
Depends on: T-4.2
Files: ~`deckforge/render/canvas.py`, ~exhibit modules, tests
Steps: each exhibit's shapes created inside a group shape (`slide.shapes.add_group_shape()`) named `ex_<slide>_<exhibit>`, alt text (`cNvPr/@descr`) set to the JSON from `12` section 2. Lint must treat group children with absolute geometry (convert child offsets).
Tests: group exists per exhibit, alt text parses back to the same `ExhibitData`, lint unaffected, golden XML updated.
Done when:
- [ ] Example deck opens in PowerPoint and LibreOffice with groups selectable (manual check in PR).

### T-6.6 Native chart mode          Size: L
Depends on: T-6.5
Files: ~`deckforge/render/charts.py`, ~exhibits supporting native mode, tests
Steps: `render_native()` for columns, line, stacked columns, bar, scatter and waterfall (invisible base series technique) with the design system palette, data labels with number formats (`c:numFmt`), no gridlines, direct labels where the exhibit spec says so. Org setting `prefer_native_charts`.
Tests: chart XML contains embedded workbook and expected series, colours from the design system.
Done when:
- [ ] Example waterfall renders natively and passes lint when the setting is on.

### T-6.7 QA router and repair strategies          Size: L
Depends on: T-6.2
Files: +`deckforge/graphs/nodes/qa_router.py`, +`deckforge/evaluators/repairs.py`, +`deckforge/evaluators/owners.py`, +`prompts/repair/{rewrite_title,rewrite_commentary,shorten}.md`, tests
Steps: strategies and owners from `09` section 7. Router steps 1 to 8 from `27` section 8.3: filter, dedupe by fingerprint, owner (provenance, standard default, `D_DEFECT_OWNER`), strategy (standard first, else `D_REPAIR_STRATEGY`), group per (owner, slide), deterministic first then LLM in parallel per slide, re-render, classify fixed, persisting, new. In P6 the owners are the existing composer steps called as functions. T-15.6 replaces them with agent tasks without changing the router's input or output.
Tests: each strategy on a fixture defect clears it after re-QA, owner resolution order, loop stops at max rounds, a regression reverts the artefact.
Done when:
- [ ] P6 exit demo works (bad title repaired, report shows before and after, each fix names its owner).

### T-6.8 QA report persistence and events          Size: S
Depends on: T-6.2
Files: ~`render_nodes.py`, ~`finalize`, ~`DeckRepo`
Steps: write `QAReport` into `deck_versions.qa`, `defects` rows, `qa.defect` events, score computation (`09` section 6.2), QA artifact JSON.
Done when:
- [ ] `GET /runs/{id}/decks/{v}` returns QA with defects.

### T-6.9 Slide regeneration          Size: M
Depends on: T-6.7
Files: +`deckforge/graphs/regen.py`, ~`routers/runs.py`, handler `slide.regenerate`, tests
Steps: load the latest deck version state, run `slide_composer` for one slide with the user instruction added to the writer prompt (and `keep_exhibit`), re-render the deck as a new version, run QA on the changed slide plus deck-level checks, outcome labels (T-5.7).
Tests: new version created, other slides unchanged (spec hashes equal).
Done when:
- [ ] Endpoint works through the API with SSE events.

---

## P7 Tools and research

### T-7.1 Tool executor          Size: L
Depends on: T-3.5, T-1.1
Files: +`deckforge/tools/spec.py`, `registry.py`, `executor.py`, `context.py`, tests
Steps: exactly `08` sections 2 and 4 (validation, features, permissions, cache, breaker, timeout, retries, output validation, offload, `tool_calls` rows, metrics).
Tests: every branch of the executor with a fake tool.
Done when:
- [ ] Coverage of `executor.py` at least 90%.

### T-7.2 Tool implementations (internal groups)          Size: L
Depends on: T-7.1, T-4.7
Files: +`deckforge/tools/impl/{data,calc,knowledge,viz,assets,documents,render,qa,storage}.py`, +`deckforge/tools/cards.yaml`, tests
Steps: implement the catalogue in `08` section 3 except research. Typed `query_table` per section 3.1. Wrap existing asset sources.
Tests: per tool as `08` section 8.
Done when:
- [ ] Nodes from P4 that compute things call tools through the executor where the catalogue covers them (`compute_facts` uses `calc`, `pick_assets` uses `assets`).

### T-7.3 Egress guard and fetch          Size: M
Depends on: T-7.1
Files: +`deckforge/security/egress.py`, +`deckforge/tools/impl/research_fetch.py`, tests
Steps: implement `15` section 5 (resolver, IP checks, pinned connection, manual redirects, size and type limits, proxy). `fetch_url` tool extracts main text with trafilatura (HTML) or pdfplumber (PDF), stores page text as a blob, returns a summary and handle, runs `D_GUARD_INJECTION` over chunks.
Tests: SSRF cases from `15` section 9, extraction on fixture pages.
Done when:
- [ ] All SSRF tests pass.

### T-7.4 Search adapters          Size: S
Depends on: T-7.1
Files: +`deckforge/research/search.py` (`SearxngSearch`, `BraveSearch`, `NullSearch`), `web_search` tool, tests
Steps: SearXNG JSON API (`/search?q=...&format=json`), recency and language params, normalise to `SearchHit(title, url, snippet, published)`. Brave as an example commercial adapter behind `DF_SEARCH_API_KEY`.
Tests: response parsing fixtures, disabled backend returns `unavailable`.
Done when:
- [ ] `web_search` works against a local SearXNG (manual) and fixtures (CI).

### T-7.5 Tool cards and Laya tool selector middleware          Size: M
Depends on: T-7.2, T-5.2
Files: +`deckforge/tools/selector.py`, +`deckforge/tools/cards.py`, tests
Steps: exactly `08` section 5 (pipeline, middleware, option rules, outcome labeller).
Tests: with `create_agent` and a fake chat model: tool list bound equals expectation for scripted FakeLaya answers (answer, tool with group, abstain), outcome labels written.
Done when:
- [ ] Middleware tests pass and decision rows carry outcome labels.

### T-7.6 Research agent          Size: L
Depends on: T-7.3, T-7.4, T-7.5
Files: +`deckforge/graphs/research.py`, +`prompts/research/agent.md`, `extract_facts.md`, ~`deck.py` (fan-out and merge), tests
Steps: `08` section 6 (agent construction with the `df-researcher` adapter when present, limits, citation verification by quote matching, fallbacks to dummy, merge into exhibit data and facts with `source=research`).
Tests: FakeSearch plus FakeLLM scripted agent produces findings with verified quotes, an unverifiable quote is rejected, research disabled path.
Done when:
- [ ] P7 exit demo with fixtures in CI and with SearXNG plus a local model manually.

### T-7.7 Reference documents          Size: M
Depends on: T-7.1, T-4.5
Files: handler `reference.extract`, +`deckforge/ingest/references.py`, tools `reference_search`, `read_reference_section`, tests
Steps: extract text (pdfplumber, python-docx), chunk by headings and length (about 380 tokens), guard check, embed into `kb_items` namespace `refs:{project_id}` with org id, search tool returns chunk summaries and handles.
Tests: extraction fixtures, injection chunk quarantined, search relevance on a fixture.
Done when:
- [ ] Planning prompts include relevant reference excerpts for a brief with an attached PDF.

### T-7.8 MCP server and client (optional)          Size: M
Depends on: T-7.1, T-2.4
Files: +`deckforge/tools/mcp_server.py`, +`deckforge/tools/mcp_client.py`, CLI `deckforge mcp serve`, tests
Steps: `08` section 7.
Done when:
- [ ] An MCP client lists DeckForge tools and creates a run with an API key.

### T-7.9 Tool sandbox mode and recordings          Size: M
Depends on: T-7.1, T-7.3
Files: +`deckforge/tools/sandbox.py`, +`training/sandbox/recordings/`, CLI `deckforge tools record|replay`, tests
Steps: `21` section 4. External tools (`web_search`, `fetch_url`, `image_search`) run against recorded responses keyed by normalised arguments. Recording mode stores request, response, timestamp and licence note. Replay mode never touches the network and returns `status="not_recorded"` for unknown keys. Training environments and tool benchmarks use replay only.
Tests: record then replay returns identical results, unknown key path, no socket opened in replay mode (socket guard fixture).
Done when:
- [ ] The research agent test suite runs fully on recordings with the network disabled.

### T-7.10 Tool benchmark          Size: M
Depends on: T-7.9, T-7.5
Files: +`evals/tools/*.yaml`, +`deckforge/evals/tools.py`, CLI `deckforge eval --suite tools`
Steps: `21` section 6.2. At least 20 tasks per tool group with the expected tool, expected argument constraints and the expected outcome. Metrics: tool selection accuracy, argument validity, task success, calls per task, Laya and CLM shortlist recall. Report per tool and per group, compared with the last release.
Tests: scoring functions on hand-made traces.
Done when:
- [ ] Benchmark report for the base model committed under `evals/reports/tools/`.

### T-7.11 Tool description optimisation loop          Size: M
Depends on: T-7.10
Files: +`training/tools/describe_opt.py`, job `train.tool_descriptions`, tests
Steps: `21` section 7.2. For tools below their selection-accuracy target, generate 8 description variants with the planner role, run the benchmark on each (replay mode), keep the best only if it beats the current one by at least 2 points on the held-out split and does not lower any other tool's accuracy by more than 1 point. Output a PR-ready diff of the tool spec description and the report.
Tests: selection rule on synthetic scores, held-out split never used for choosing.
Done when:
- [ ] One loop run on two weak tools produces a report and a description diff.

---

## P8 Templates and design systems

### T-8.1 Template ingestion graph          Size: L
Depends on: T-2.2, T-4.1
Files: +`deckforge/ingest/template.py`, +`deckforge/graphs/template.py`, +`deckforge/design/palette.py` (OKLab, contrast, ramp builder), handler `template.ingest`, tests with two fixture templates
Steps: `12` section 3 steps 1 to 10.
Tests: theme colours and fonts extracted, zones derived, colour role mapping obeys contrast rules, heat ramp text contrast at least 4.5:1, logo detection, macro template rejected.
Done when:
- [ ] Both fixture templates produce valid `DesignSystem` rows and previews.

### T-8.2 Design systems API and preview          Size: M
Depends on: T-8.1
Files: +`routers/design.py`, +`deckforge/design/preview.py` (sample deck), tests
Steps: endpoints from `05` section 3.3, versioning on patch, preview generation job.
Done when:
- [ ] Editing the accent colour creates version 2 and a new preview.

### T-8.3 Style system driven by DesignSystem          Size: L
Depends on: T-4.1
Files: ~`deckforge/viz/style.py`, ~`deckforge/viz/frame.py`, +migration seeding MERIDIAN and VERDANT rows, tests
Steps: `Family.from_design_system`, `use(ds)`, zones from `ds.zones`, families exported as `DesignSystem` seeds. Keep `use("meridian")` working.
Tests: golden decks unchanged for both families, a custom design system changes colours and fonts.
Done when:
- [ ] Golden XML identical for MERIDIAN and VERDANT.

### T-8.4 Decks on customer templates          Size: L
Depends on: T-8.3, T-8.1
Files: ~`deckforge/render/canvas.py` (`Deck(template_path)`), ~`deckforge/story/render.py` (layout map, title placeholder), tests
Steps: open template, delete sample slides safely (remove slide ids and relationships), add slides from mapped layouts, put titles into title placeholders when present, place content in derived zones, keep master footers and logos. Lint treats placeholder text frames correctly.
Tests: deck from each fixture template passes lint and look-and-feel, master elements present, no orphan relationships (zip integrity check).
Done when:
- [ ] P8 exit demo.

---

## P9 Frontend

### T-9.1 SPA scaffold and auth          Size: M
Depends on: T-1.5, T-2.5
Files: +`frontend/` scaffold per `13` section 2, ~`pyproject.toml` (poe `openapi` task), tests
Steps: Vite React TypeScript app, Tailwind v4 with CSS variables for light and dark, TanStack Router and Query, openapi-typescript generation from the running app (`poe openapi` starts the app in-process, writes `openapi.json`, runs `npx openapi-typescript`), openapi-fetch client with Bearer injection and one refresh retry on 401, login page, protected route wrapper, OIDC button when `system/info` says it is configured.
Tests: vitest for the client refresh logic.
Done when:
- [ ] Log in and see an empty projects page in lite mode with the built SPA served by FastAPI.

### T-9.2 Projects and data          Size: M
Depends on: T-9.1, T-2.7
Files: `frontend/src/features/projects/*`, `files/*`
Steps: projects list and create, project workspace tabs, file drop zone (multiple files, progress via XHR upload events), file status polling, profile viewer with semantic type and unit editing (`PATCH /files/{id}/profile`).
Done when:
- [ ] Upload the example xlsx and correct a column type in the browser.

### T-9.3 Brief form          Size: S
Depends on: T-9.2
Files: `frontend/src/features/briefs/*`
Steps: `13` section 4 with zod validation mirroring the API schema, generate button creating brief and run with an idempotency key.
Done when:
- [ ] Creating a run navigates to the run page.

### T-9.4 Run page: timeline, questions, plan review          Size: L
Depends on: T-9.3
Files: `frontend/src/features/runs/*`, `frontend/src/api/sse.ts`, `frontend/src/lib/useRunEvents.ts`
Steps: `13` sections 5 and 5.1. Plan review editor: editable cards, drag to reorder (keyboard accessible), framework and data status badges, approve, save edits, revise with instruction. Client-side validation mirrors server validators where cheap (unique ids, section references).
Tests: vitest for SSE reconnection and plan editor validation.
Done when:
- [ ] Full flow through clarification and plan approval in the browser.

### T-9.5 Slides, QA, reasoning, downloads          Size: L
Depends on: T-9.4, T-6.8, T-6.9
Files: `frontend/src/features/runs/slides/*`, `qa/*`, `reasoning/*`
Steps: slide grid filling live, slide detail with facts provenance, defects, regenerate with instruction, feedback buttons, QA tab, reasoning tab (markdown rendered with a sanitising renderer), downloads.
Done when:
- [ ] A user regenerates one slide and downloads the new version.

### T-9.6 Design page          Size: M
Depends on: T-9.1, T-8.2
Files: `frontend/src/features/design/*`
Steps: family picker with previews, template upload with ingestion status, token editor (colour pickers with live contrast warnings, font selects from bundled and template fonts, layout map selects), preview grid.
Done when:
- [ ] Template uploaded and selected for a project in the browser.

### T-9.7 Admin pages          Size: M
Depends on: T-9.1, T-1.7, T-1.6, T-3.6
Files: `frontend/src/features/admin/*`
Steps: members and roles, API keys (show once dialog), provider credentials (write-only fields), org settings (data policies: `allow_training`, `allow_exploration`, research toggle, retention, with the data processing record from `15`), model and adapter versions in use (read-only), usage chart (SVG), audit log table, decision policies (read-only view with metrics).
Done when:
- [ ] Owner can invite an editor and create an API key in the browser.

### T-9.8 End-to-end tests          Size: M
Depends on: T-9.5
Files: +`tests/e2e/*.spec.ts`, +`deckforge/testing/profile.py` (fake profile wiring)
Steps: the flow in `13` section 8 plus: viewer cannot create runs, cancel a run, reconnect SSE after a network drop (Playwright offline toggle).
Done when:
- [ ] `poe test-e2e` passes locally and in the nightly CI job.

---

## P10 Packaging and deployment

### T-10.1 Container images          Size: M
Depends on: T-6.3, T-5.6, T-9.1
Files: +`deploy/docker/Dockerfile.app`, `Dockerfile.nginx`, ~`Dockerfile.renderer`, ~`Dockerfile.laya`, +`.dockerignore`
Steps: app image: `python:3.12-slim`, uv sync from lockfile (`--extra server`), non-root user, `HEALTHCHECK`, entrypoint `deckforge`. nginx image: Node build stage for the SPA, then `nginx:stable` with config and snippets. All images multi-arch (`docker buildx`, amd64 and arm64 except GPU variants).
Done when:
- [ ] `docker buildx bake` builds all images. Trivy shows no critical vulnerabilities.

### T-10.2 Compose stack, nginx config, secrets CLI          Size: M
Depends on: T-10.1
Files: +`deploy/compose/docker-compose.yml`, `.env.server.example`, +`deploy/nginx/*`, ~`deckforge/cli.py` (`secrets init`)
Steps: files exactly as `14` sections 2 and 3. `deckforge secrets init --dir deploy/compose/secrets` generates all secret files and writes `POSTGRES_PASSWORD` to `.env`. Self-signed certificate helper for evaluation installs (`deckforge certs selfsigned`).
Done when:
- [ ] On a fresh Linux VM: `deckforge secrets init`, `docker compose up -d` (core profile), browse to https, log in, complete a run with an Ollama or vLLM endpoint.

### T-10.3 Model pull, registry and serving profiles          Size: M
Depends on: T-10.2, T-3.4
Files: +`deckforge/models/pull.py`, +`deckforge/models/manifest.py`, CLI `deckforge models pull|verify|list`, ~`deploy/compose/docker-compose.yml` (GPU profile services from `14` section 2), tests
Steps: a signed model manifest (name, version, files, sha256, licence) per release of `df-lm`, adapters, `df-vlm`, `df-laya`, `df-laya-vision`, CLM heads and the base CLM encoder. `pull` downloads into `/models` (server) or the platform data dir (lite) with resume and hash checks, `verify` re-hashes, air-gapped installs import a tarball. Writes `model_registry` rows. Ollama profile: `ollama create` from the GGUF and Modelfile in the bundle.
Tests: manifest signature check, hash mismatch fails, resume after interruption (fake server).
Done when:
- [ ] On a GPU server, `deckforge models pull --release <v>` then `docker compose --profile gpu up -d` serves all model services and `deckforge llm ping` succeeds for every role.

### T-10.4 Observability          Size: M
Depends on: T-2.2
Files: +`deckforge/observability/{tracing,metrics}.py`, +`deploy/observability/*` (collector config, Prometheus config, alert rules, Grafana dashboards JSON)
Steps: `16` sections 2 to 5. Metrics server on port 9100 for api and worker. `OtelGraphCallback` for node and LLM spans.
Done when:
- [ ] Observability profile shows the five dashboards with live data from a test run.

### T-10.5 Lite packaging and three-OS smoke          Size: M
Depends on: T-2.8, T-9.5
Files: ~`pyproject.toml` (build hook copying `frontend/dist`), +`deckforge/doctor.py`, ~CI
Steps: wheel includes the SPA and fonts. `deckforge init` non-interactive mode for CI. `deckforge doctor` checks (`14` section 1). CI job `lite-smoke` on three OSes (`17` section 5).
Done when:
- [ ] `lite-smoke` green on macOS, Windows, Linux.

### T-10.6 CI workflow          Size: S
Depends on: T-0.2
Files: ~`.github/workflows/ci.yml`, +`.github/workflows/nightly.yml`, +`.github/workflows/release.yml`
Steps: jobs from `17` section 5. Release workflow on tags builds images, wheel, SBOM, and attaches eval summary.
Done when:
- [ ] All jobs green on main.

### T-10.7 Retention, purge and maintenance jobs          Size: S
Depends on: T-2.2
Files: handlers `project.purge`, `org.purge`, `maintenance.prune_checkpoints`, `maintenance.redact_decision_log`, scheduler in the worker (one worker holds an advisory lock and enqueues maintenance jobs daily)
Done when:
- [ ] Purge removes rows and blobs, verified by a test that lists the blob store afterwards.

### T-10.8 Webhooks          Size: S
Depends on: T-7.3, T-2.2
Files: migration `0002_webhooks.py`, +`routers/webhooks.py`, handler `webhook.deliver`, tests
Steps: `05` section 6.6.
Done when:
- [ ] Signature verifies with the documented algorithm (test vector in docs).

---

## P11 Learning loop

### T-11.1 Training data format and converters          Size: M
Depends on: T-5.4
Files: +`training/laya/convert.py`, +`training/laya/FORMATS.md`, +`training/data/README.md`, tests
Steps: implement the JSONL format (`09` section 8.2) with a Pydantic model, group-aware splitting, converters to the vendored fine-tune script input and to `laya-evals` datasets. Read the pinned package's `evals` dataset parser and the fine-tune script to confirm field names, record them in `FORMATS.md`.
Done when:
- [ ] `laya-evals validate` accepts a converted sample file.

### T-11.2 Synthetic perturbation generators (S1)          Size: L
Depends on: T-11.1, T-6.1
Files: +`training/generators/*.py` (one per decision family), tests
Steps: generators from `09` section 8.1 S1. Each generator takes a good slide or brief (from golden decks and corpus reconstructions) and returns labelled items with a `group` id of the source. LLM-assisted rewrites (casual, promotional, topic-only titles) use the `writer` role with fixed prompts and are tagged.
Tests: label correctness by construction checks (for example a number swap really changes a number present in the exhibit).
Done when:
- [ ] At least 2,000 items per judge family generated from the available sources (report in PR).

### T-11.3 Corpus positives, teacher labels, production export          Size: L
Depends on: T-11.1, T-6.2
Files: +`training/sources/corpus.py`, `teacher.py`, `production.py`, job kind `eval.run` reuse
Steps: S2 from corpus slide descriptions. S3 teacher labelling with 3 samples and unanimity filter (job runs on the eval host with the open teacher models allowed by D18, never a closed API). S4 export from `decision_log` (install-local, respects `allow_training`).
Done when:
- [ ] Dataset summary per decision id (counts by source and label) generated.

### T-11.4 Fine-tune, calibrate, evaluate, register          Size: L
Depends on: T-11.2, T-11.3
Files: +`training/laya/finetune.py` (vendored, pinned commit, NOTICE), +`training/laya/calibrate.py`, +`training/laya/evaluate.py`, job `laya.train`, CLI `deckforge laya train|eval|register`
Steps: `09` sections 5 and 8.3. Output a checkpoint directory, calibration payload, eval report, `model_registry` row (candidate) and candidate `decision_policies` rows (mode `shadow`).
Done when:
- [ ] A training run on a 16 GB GPU or Apple Silicon completes and writes all outputs (log attached).

### T-11.5 Shadow rollout and promotion          Size: M
Depends on: T-11.4, T-10.4
Files: +`deckforge/decisions/promotion.py`, CLI `deckforge laya promote --decision <id> --checkpoint <v>`, Grafana panels
Steps: compute shadow metrics from `decision_log` (agreement, accuracy against outcome labels, coverage at threshold, ECE by bucket), check gates (`09` section 9.2), flip policy to `laya_first`, rollback command.
Done when:
- [ ] P11 exit demo: three decisions promoted on measured gates, with the report committed under `evals/reports/`.

### T-11.6 Eval harness          Size: L
Depends on: T-4.10, T-6.4
Files: +`deckforge/evals/*.py`, +`evals/briefs/*` (30 briefs), CLI `deckforge eval --suite ...`
Steps: suites and pass bars from `17` section 6. Model selection procedure (`07` section 8).
Done when:
- [ ] Nightly eval report produced on the eval host.

### T-11.7 Gold review page (S5)          Size: S
Depends on: T-9.7, T-11.1
Files: `frontend/src/features/admin/gold/*`, +`routers/admin_gold.py`
Steps: superadmin-only page showing one item at a time (state, question, options), keyboard shortcuts to label, skip, export to `training/data/<id>/gold.jsonl`.
Done when:
- [ ] 200 items per judge family can be labelled in about an hour per family.

---

## P12 Hardening and scale

### T-12.1 Security test suite          Size: M
Depends on: T-7.3, T-1.8
Files: tests listed in `15` section 9
Done when:
- [ ] All security tests pass in CI.

### T-12.2 Permission introspection and audit completeness          Size: S
Depends on: T-9.7
Files: +`tests/unit/api/test_route_permissions.py`, ~routers
Steps: iterate `app.routes`, assert each non-public route depends on `require_role` or `require_scope`. Assert every admin mutation writes an audit row.
Done when:
- [ ] Test passes.

### T-12.3 Load tests and capacity measurement          Size: M
Depends on: T-10.2
Files: +`tests/load/locustfile.py`, ~`docs/build/01_architecture.md` section 8 (measured numbers)
Steps: scenarios from `17` section 7, then one real-model run on the reference node.
Done when:
- [ ] Capacity table in `01` replaced with measurements and the date.

### T-12.4 Backups and restore drill          Size: S
Depends on: T-10.2
Files: +`deploy/compose/backup/` (pgBackRest config, scripts), +`docs/operations/restore.md`
Done when:
- [ ] Restore drill from `14` section 8 performed and recorded.

### T-12.5 Optional row-level security          Size: M
Depends on: T-1.2
Files: migration `0003_rls.py`, ~`deckforge/db/session.py` (`SET LOCAL app.org_id`)
Done when:
- [ ] Tenancy integration tests pass with RLS enabled.

### T-12.6 Platform installers          Size: L
Depends on: T-10.5
Files: +`deploy/installers/*` (PyInstaller spec, Windows MSI via WiX, macOS dmg, Linux AppImage)
Steps: raise a decision request for code signing certificates first.
Done when:
- [ ] Installers start DeckForge and open the browser on clean VMs of each OS.

### T-12.7 Helm chart          Size: L
Depends on: T-10.2
Files: +`deploy/helm/deckforge/*`
Steps: `14` section 7.
Done when:
- [ ] `helm install` on a kind cluster completes a run with fake models.

### T-12.8 Air-gapped bundle          Size: M
Depends on: T-10.1, T-5.6
Files: +`deckforge/bundle.py`, CLI `deckforge bundle`
Steps: `14` section 6.
Done when:
- [ ] Install from the bundle on a VM with outbound traffic blocked.

### T-12.9 PII redaction option          Size: M
Depends on: T-5.2
Files: +`deckforge/security/pii.py` (optional `presidio-analyzer` extra), ~decision log and llm_calls writers
Done when:
- [ ] With the org setting on, names and emails in logged state text are replaced by placeholders.

---

### T-12.10 Query plan and index test          Size: M
Depends on: T-1.2, T-18.1
Files: +`tests/integration/db/test_query_plans.py`, +`tests/integration/db/seed_large.py`
Steps: seed a PostgreSQL test database with production-like volumes (`23` section 1 sizes, scaled to 10 orgs and 50k runs). For each query Q1 to Q16 in `23` section 2, run `EXPLAIN (FORMAT JSON)` and fail when a table above 10k rows shows a sequential scan, or when the plan's estimated cost is above the recorded baseline by 50%.
Tests: the test itself, run in the nightly CI job with the `pgvector/pgvector:pg17` service.
Done when:
- [ ] All Q1 to Q16 plans use their indexes. Baselines committed.

### T-12.11 Telemetry partitioning and buffered writer          Size: M
Depends on: T-1.2, T-10.7
Files: +`migrations/versions/*_partition_telemetry.py`, +`deckforge/db/partitions.py`, +`deckforge/db/telemetry_writer.py`, job `db.partitions`, tests
Steps: `23` sections 4 and 7. Convert `run_events`, `decision_log`, `llm_calls`, `tool_calls`, `agent_traces`, `agent_messages`, `audit_log` and `usage_ledger` to monthly range partitions on `created_at`. The daily `db.partitions` job creates the next 2 months and detaches, exports (parquet) and drops partitions past retention. `TelemetryWriter` buffers rows in-process and flushes every 200 ms or 500 rows with `COPY` (server) or `executemany` (lite), and flushes on shutdown. Run state tables are never buffered.
Tests: partitions created ahead, retention drop, writer flush on size and on time, flush on shutdown, crash loses at most the buffer.
Done when:
- [ ] Load test (T-12.3) shows telemetry inserts below 5% of database CPU at the target run rate.

---

## P13 DeckForge-LM

Training tickets run on vendor GPUs (`19` section 8). Every training script is deterministic given a seed and a dataset version, logs to MLflow (T-13.11) and writes a report under `evals/reports/`.

### T-13.1 Base model bake-off          Size: L
Depends on: T-4.10, T-7.10
Files: +`training/bakeoff/run.py`, +`training/bakeoff/candidates.yaml`, +`evals/reports/bakeoff/`, decision record `docs/decisions/DR-xxx-base-model.md`
Steps: candidates and criteria from `19` section 2 (Qwen3 dense, gpt-oss, Mistral Small, plus a VLM shortlist for `df-vlm`). Verify each licence text from the model card and record it. Serve each candidate with the pinned vLLM, run the agent suites, 30 golden briefs, the tool benchmark and the latency and memory probes with the same prompts. Score with the weights in `candidates.yaml`.
Tests: none new (evaluation ticket). The scoring script has unit tests for weighting and ties.
Done when:
- [ ] Decision record names the base family and the `df-vlm` base with the scores table, licence evidence and the runner-up.

### T-13.2 Training data engine C1 to C7          Size: L
Depends on: T-13.1, T-11.1
Files: +`training/data_engine/{c1_corpus.py,c2_briefs.py,c3_teacher.py,c4_self.py,c5_repairs.py,c6_feedback.py,c7_public.py}`, ~`training/DATA_REGISTER.md` (data register with licences), +`training/data_engine/filters.py`, tests
Steps: `19` section 4. C1 corpus inversion pipeline, C2 synthetic briefs with code-generated data, C3 teacher trajectories with rejection sampling (open teachers only, D18), C4 best-of-N self runs, C5 repair pairs, C6 install-local feedback when `allow_training` is on, C7 public datasets from the register. Filters from `19` section 4.6 in order: schema, verifiable checks, MinHash dedupe, decontamination against `evals/` and gold sets, PII scrub, length, balance, licence register. Output JSONL in the formats of `19` section 4.7 with a dataset version.
Tests: each source produces valid records on a small fixture, decontamination removes a planted eval item, licence filter drops a record from an unlisted source.
Done when:
- [ ] Dataset card with counts per source, agent and task type for dataset `v1`.

### T-13.3 Agent traces table, writer and dataset builders          Size: M
Depends on: T-1.2, T-12.11
Files: +`migrations/versions/*_agent_traces.py`, +`deckforge/agents/traces.py`, +`training/builders/{sft.py,dpo.py,grpo.py}`, tests
Steps: table `app.agent_traces` from `23` section 3 (partitioned). `TraceWriter` writes one row per agent invocation with inputs, outputs, model and tool calls, decisions, verdicts and outcome, through the buffered telemetry writer. Builders turn traces into SFT examples (accepted outputs), DPO pairs (rejected attempt then accepted fix on the same task) and GRPO prompts with reward specs (`20` section 10.1).
Tests: trace round trip, builder outputs validate against the formats, PII flag respected.
Done when:
- [ ] A golden-brief run produces traces for every agent and the builders emit at least one example of each kind.

### T-13.4 Stage 1 multitask SFT          Size: L
Depends on: T-13.2, T-13.3
Files: +`training/lm/sft.py`, +`training/lm/configs/sft_*.yaml`, job `train.lm_sft`
Steps: `19` section 5.1. TRL `SFTTrainer` with PEFT LoRA r32 on all linear layers, task mixture weights from the config, chat template of the base, completion-only loss, packing off for tool trajectories. Merge the adapter into the base for serving (`df-lm-<size>-v1.0`).
Tests: a 50-step smoke run on a tiny model in CI (CPU) checks the pipeline end to end.
Done when:
- [ ] `df-lm-32b-v1.0` candidate trained, agent suites run, report committed.

### T-13.5 Stages 2 and 3: DPO and GRPO with verifiable rewards          Size: L
Depends on: T-13.4, T-7.9
Files: +`training/lm/dpo.py`, +`training/lm/grpo.py`, +`training/lm/rewards/*.py`, +`training/lm/envs/{research_env.py,repair_env.py,data_env.py}`, tests
Steps: `19` sections 5.2 and 5.3, `21` section 5.2. DPO on C5 and C4 pairs. GRPO with `num_generations=8`, rewards from the agent cards (schema, fact tokens, fits, action title, title supported, banned phrases, length), tool environments in replay mode, KL and reward hacking checks from `24` section 8.
Tests: every reward function has unit tests with passing and failing examples, environments reset deterministically.
Done when:
- [ ] DPO and GRPO candidates beat the SFT candidate on at least two agent suites with no gate regression.

### T-13.6 Distillation, exports and measured hardware          Size: L
Depends on: T-13.5
Files: +`training/lm/distill.py`, +`training/lm/export.py`, ~`19` section 8 (replace estimates with measurements)
Steps: `19` sections 5.4 and 7. Distil 32B to 14B and 8B on teacher outputs over the full task mix. Export FP8 (server), AWQ 4-bit (24 GB GPUs), GGUF Q4_K_M, Q5_K_M and Q8_0 (laptops) with Modelfiles. Record GPU hours, wall time and memory per stage.
Tests: export round trip loads in vLLM and llama.cpp and answers a fixed prompt identically at temperature 0 within tolerance.
Done when:
- [ ] Size and quantisation bars in `19` section 6 met, measured table committed in `19` section 8.

### T-13.7 DF-LM gates, registry, shadow and promotion          Size: M
Depends on: T-13.6, T-11.5
Files: +`deckforge/models/promotion_lm.py`, CLI `deckforge lm promote|rollback`, Grafana panels
Steps: `19` sections 6 and 9. Run the gate suite, write `model_registry` rows, run shadow on eval traffic (10% of eligible calls), compare rewards, switch role mappings in `config/models.yaml` on promotion, rollback command.
Tests: gate evaluation on synthetic reports, role mapping switch and rollback.
Done when:
- [ ] P13 exit demo: `df-lm-v1` promoted on the reference server with the gate report.

### T-13.8 Counterfactual replay engine          Size: L
Depends on: T-4.3, T-13.3
Files: +`deckforge/replay/sample.py`, `fork.py`, `utility.py`, +`config/utility.yaml`, CLI `deckforge replay sample|run|label`
Steps: `24` section 3.2. Sample checkpoints just before a decision, fork once per option with `aupdate_state` and `astream(None, forked_config)`, run to the end with Fake renderer timing off, compute utility from `config/utility.yaml`, write labels for Laya and CLM heads. Runs only on internal eval briefs.
Tests: fork produces independent branches, utility computation, labels written with the source checkpoint id.
Done when:
- [ ] 500 replays for `D_REPAIR_STRATEGY` produce labels and a report of option win rates.

### T-13.9 CLM heads and clm-serve integration          Size: M
Depends on: T-13.8, T-17.2
Files: +`deckforge/decisions/clm.py` (`HttpClm`), +`training/clm/train_heads.py`, +`training/clm/configs/*.yaml`, tests
Steps: `09` section 10 and `24` section 5. Implement `rank()` on the `DecisionEngine` port through `POST /v1/rank` with the pgvector cosine fallback. Train the six heads on the frozen base encoder, evaluate against the gates in `09` section 10.2, register candidates. Upload candidate set embeddings on each `kb_version` and registry change.
Tests: `HttpClm` contract tests with recorded fixtures, fallback on outage, candidate set version invalidates the cache.
Done when:
- [ ] `framework-rank` and `verifier` pass their gates and run in shadow.

### T-13.10 df-vlm fine-tune          Size: L
Depends on: T-13.1, T-16.1
Files: +`training/vlm/sft.py`, +`training/vlm/data.py`, +`training/vlm/configs/*.yaml`
Steps: `25` sections 5 and 8. Data from rendered golden and perturbed slides with geometry ground truth (boxes from L2) and rubric labels. SFT with LoRA on the chosen VLM base, then merge and export FP8 and GGUF.
Tests: data builder produces boxes that match the PDF geometry on a fixture slide.
Done when:
- [ ] Region recall on the visual defect set at least 0.85 with box IoU at least 0.5, report committed.

### T-13.11 Experiment tracking and the monthly cycle          Size: M
Depends on: T-13.7
Files: +`deploy/compose/mlflow.yml` (training host only), +`training/cycle.py`, job `train.cycle`
Steps: MLflow tracking for every training job (params, dataset version, metrics, artefacts). `train.cycle` runs `19` section 10 steps 1 to 6 as a pipeline with manual approval before promotion.
Done when:
- [ ] One full cycle executed with all runs visible in MLflow and the promotion decision recorded.

---

## P14 Memory and performance

### T-14.1 Memory calculator from model configs          Size: M
Depends on: T-3.1
Files: +`deckforge/models/memory.py`, CLI `deckforge mem plan --hardware <file>`, tests
Steps: formulas in `22` section 2 computed from each served model's `config.json` (layers, KV heads, head dim, hidden and intermediate sizes) and the dtype flags. Output per GPU: weights, LoRA slots, KV capacity in tokens, concurrent sequences at a given context, and the sum check against 0.95. Fail when a planned layout exceeds the limit.
Tests: numbers for Qwen3-32B match `22` section 3 within 2%, LoRA formula example matches section 2, the GPU 3 layout passes and an over-committed layout fails.
Done when:
- [ ] `deckforge mem plan` prints the `22` section 4.1 table for the reference server.

### T-14.2 Admission control and degradation ladder          Size: L
Depends on: T-3.4, T-10.4
Files: ~`deckforge/llm/pool.py`, +`deckforge/llm/admission.py`, tests
Steps: `22` sections 6.2 to 6.4. Adaptive concurrency per replica (multiply the limit by 0.8 on waiting requests or KV above 95%, add 1 when KV is below 70% and nothing waits), priority queues, and the five-step degradation ladder of `22` section 6.4 applied in order after 60 s of saturation and undone in reverse.
Tests: simulated replica metrics drive each ladder step and the undo, interactive calls are never starved by background calls.
Done when:
- [ ] Under a synthetic overload, vLLM never reports preemptions and the degradation gauge returns to 0 after the load drops.

### T-14.3 Server benchmarks          Size: M
Depends on: T-14.2, T-13.7
Files: +`benchmarks/server/*.py`, ~`22` (replace estimates), ~`01` section 8
Steps: `22` section 11 items 1 to 4 on the reference server.
Done when:
- [ ] Measured tables replace the estimates in `22` and `01`. FP8 KV within 0.5 QA points of bf16.

### T-14.4 Laptop and companion-model benchmarks          Size: M
Depends on: T-13.6, T-13.9
Files: +`benchmarks/laptop/*.py`, ~`22` section 5
Steps: `22` section 11 item 5, plus CLM ranking throughput and Laya-Vision images per second on the reference server.
Done when:
- [ ] Laptop tier table and GPU 3 throughput numbers in `22` are measured, not estimated.

### T-14.5 GPU scheduler          Size: M
Depends on: T-14.2
Files: +`deckforge/ops/gpu_schedule.py`, CLI `deckforge gpu-schedule`, tests
Steps: `22` section 4.2. Night window from config. Put `vllm-lm-b` to sleep (`POST /sleep?level=1`) or stop the container when dev mode is not allowed, start the training or teacher job on GPU 2, checkpoint and stop it when the run queue backs up or the window ends, then `POST /wake_up` and wait for `/is_sleeping` false before routing traffic back.
Tests: state machine with fake endpoints, queue backlog interrupts training, wake failure falls back to container restart.
Done when:
- [ ] A night window on the reference server trains for 2 hours and serves again within 3 minutes of a simulated morning backlog.

---

## P15 Agents and protocol

### T-15.1 Agent cards, registry and contracts          Size: M
Depends on: T-4.10, T-5.4
Files: +`deckforge/agents/{base.py,registry.py,contracts.py}`, +`deckforge/agents/<id>/card.yaml` for the 12 agents, tests
Steps: `20` sections 2, 3 and 5. `AgentCard` model and startup validation (tools exist, decisions exist, prompts exist, models import). Contracts with `schema_version`.
Tests: every card loads and validates, a card with an unknown tool fails startup, unknown major schema version is rejected.
Done when:
- [ ] `deckforge agents list` prints the roster with adapters, tools and limits.

### T-15.2 DAP envelope, blackboard and ownership          Size: L
Depends on: T-15.1
Files: +`deckforge/agents/protocol.py`, +`deckforge/agents/blackboard.py`, +`migrations/versions/*_agent_messages.py`, tests (`27` section 12 list)
Steps: `27` sections 2 to 4 and 10. Envelope and performatives, message contracts, artefact references with versions, blackboard reads and writes with owner enforcement, the permission matrix, `app.agent_messages` writes through the telemetry writer.
Tests: `tests/unit/agents/test_protocol.py` per `27` section 12.
Done when:
- [ ] A write by a non-owner is refused and logged, every message of a golden run is stored with its conversation id.

### T-15.3 Dependency graph and redo          Size: M
Depends on: T-15.2
Files: +`deckforge/agents/dependencies.py`, tests
Steps: `27` section 5 and 6.3. Artefact dependency DAG, invalidation on a new version, `TASK(kind="redo")` fan-out to dependants in order, skip when the dependant's inputs hash is unchanged.
Tests: `tests/unit/agents/test_dependencies.py`.
Done when:
- [ ] Changing the exhibit of one slide redoes only that slide's copy and asset checks.

### T-15.4 Workflow agents over the existing nodes          Size: L
Depends on: T-15.2, T-6.7
Files: +`deckforge/agents/<id>/{graph.py,steps.py}` for the workflow agents, ~`deckforge/graphs/deck.py`, tests
Steps: `20` section 4 workflow pattern. Wrap intake, planning, data binding, composer steps (viz, copy, assets), fact checking and review as agent subgraphs that take `TaskOrder` and return `TaskResult`. Replace direct owner calls in `qa_router` with agent tasks. Outputs and events must stay identical to P6 on the golden briefs.
Tests: golden-brief graph tests unchanged and green, each agent has a unit test with FakeLLM.
Done when:
- [ ] P4 and P6 demos pass through agents with identical artefacts on fixtures.

### T-15.5 ReAct factory, supervisor and revision graph          Size: L
Depends on: T-15.4
Files: ~`deckforge/agents/factory.py`, +`deckforge/agents/supervisor/*`, +`deckforge/graphs/revision.py`, job `run.revise`, tests
Steps: `20` section 4 ReAct pattern and W2, `27` section 6.4. Supervisor returns a `RevisionPlan` through `D_REVISION_ROUTE` and `D_REVISION_SCOPE` with LLM fallback, the orchestrator validates and dispatches, dependants are redone, incremental QA runs.
Tests: scripted revision requests map to the right owner and scope with FakeLaya, invalid plans are rejected, the supervisor never writes an artefact.
Done when:
- [ ] "Show this as a map" on a fixture slide produces a new exhibit, updated copy and a new deck version.

### T-15.6 NEED routing, arbitration and loop control          Size: L
Depends on: T-15.4
Files: ~`deckforge/graphs/nodes/qa_router.py`, +`deckforge/agents/arbitration.py`, +`deckforge/agents/needs.py`, tests
Steps: `27` sections 6.2, 6.6 and 8.4. `NEED` routing with `D_NEED_ROUTE` fallback, limits on needs per task, placeholders for non-blocking needs. Arbitration order for `REJECT(constraint_conflict)`. Loop control table: re-task, reroute, regression revert, residual acceptance with `D_REPAIR_STOP`.
Tests: `tests/unit/graphs/test_need_flow.py`, `test_qa_router.py`, arbitration cases from `27` section 6.6.
Done when:
- [ ] The worked example in `27` section 8.5 runs as an integration test.

### T-15.7 Escalation, cancellation and progress          Size: M
Depends on: T-15.4
Files: ~`deckforge/graphs/deck.py`, +`deckforge/agents/control.py`, tests
Steps: `27` sections 6.7 to 6.9. `ESCALATE` to LangGraph `interrupt` with batching of non-blocking questions, `CANCEL` checked between model and tool calls, `INFO` mapped to `node.progress` events.
Tests: blocking escalation pauses and resumes with the answer in `reads`, cancel stops a running agent within one step.
Done when:
- [ ] A blocking question from data_analyst reaches the UI and the run resumes after the answer.

### T-15.8 Cross-worker transport          Size: M
Depends on: T-15.2, T-2.2
Files: +`deckforge/agents/transport_jobs.py`, tests
Steps: `27` section 9 level L-B. Envelope in a `jobs` row with kind `agent.task` and a worker-kind filter, reply into `agent_messages` and pub/sub, deadline handling counts a failed attempt, idempotency key reuse on retries.
Tests: reply delivered across two worker processes, deadline expiry, duplicate delivery ignored.
Done when:
- [ ] Researcher runs on a separate network-enabled worker in the compose stack.

### T-15.9 A2A v1 bridge          Size: M
Depends on: T-15.2, T-2.4
Files: +`deckforge/api/routers/a2a.py`, +`deckforge/agents/a2a_bridge.py`, tests
Steps: `27` section 9, level L-C and the A2A mapping. Publish `/.well-known/agent-card.json` for the orchestrator only (skills `generate_deck`, `revise_deck`, `review_deck`), map A2A tasks to runs and revisions, stream status updates from run events, authenticate with API keys and scopes. Internal agents are never exposed.
Tests: `tests/integration/test_a2a_bridge.py` (Agent Card, SendMessage round trip, state mapping), scope checks.
Done when:
- [ ] An external A2A client creates a deck and receives the artefact link.

### T-15.10 Agent eval suites and observability          Size: M
Depends on: T-15.4, T-10.4
Files: +`evals/agents/<id>/*`, +`deckforge/evals/agents.py`, Grafana agents dashboard
Steps: `20` sections 11 and 12. Suite per agent with the sizes and bars in the table, metrics and dashboard from `16` section 4 item 6.
Done when:
- [ ] Nightly agent suite report produced, dashboard shows tasks, rejects and repair outcomes per agent.

### T-15.11 Per-agent adapters and weekly refinement report          Size: M
Depends on: T-15.10, T-13.5
Files: +`training/agents/train_adapter.py`, +`training/agents/report.py`, job `train.agent_report`
Steps: `19` section 5.5 and `20` section 10.2. Train an r16 adapter only for agents below their card targets after the multitask model, gate on the agent suite plus no regression elsewhere. Weekly report per agent: failure clusters, traces, suggested data.
Done when:
- [ ] At least one adapter trained, gated and served through `agent_adapters`, with the report committed.

---

## P16 Visual inspector

### T-16.1 L2 rendered geometry checks          Size: M
Depends on: T-6.3
Files: +`deckforge/inspect/geometry.py`, tests
Steps: `25` section 2. Extract words, lines and images with boxes from the rendered PDF, compare with the object model, emit the defect codes in the table with bounding boxes.
Tests: fixture decks with planted overflow, overlap, off-safe-area and font substitution are each detected with the right box.
Done when:
- [ ] Inspector findings carry slide, box and standard id, and appear in the QA report.

### T-16.2 L3 pixel checks          Size: M
Depends on: T-16.1
Files: +`deckforge/inspect/pixels.py`, tests
Steps: `25` section 3 with numpy and Pillow on the 144 dpi snapshot: rendered contrast, palette adherence, visual density, balance, collisions as drawn, near-duplicate slides.
Tests: planted low contrast text over an image is caught, an off-palette colour is caught, two near-identical slides are flagged.
Done when:
- [ ] Pixel checks run on a 15-slide deck in under 2 s on CPU.

### T-16.3 Laya-Vision service and df-laya-vision          Size: L
Depends on: T-16.1, T-5.6
Files: +`deploy/docker/Dockerfile.laya_vision`, +`deckforge/decisions/visual.py` (`VisualJudge`), +`training/laya_vision/*`, tests
Steps: `25` sections 4 and 8, `09` section 10.3. Vendor the fork code at a pinned commit with NOTICE, never download the upstream weights. Train `df-laya-vision` on Apache-licensed backbones with perturbation labels, calibrate, serve on port 8210, batch per deck.
Tests: `VisualJudge` contract tests with recorded fixtures, licence check script fails if an upstream checkpoint hash is present in `/models`.
Done when:
- [ ] `V_FOCAL` and `V_TEXT_ON_IMAGE` pass the judge gates in `09` section 9.2 and run in shadow.

### T-16.4 L5 rubric review with regions          Size: M
Depends on: T-6.4, T-13.10
Files: ~`deckforge/evaluators/tier3.py`, +`prompts/judge/visual_regions.md`, tests
Steps: `25` section 5. `df-vlm` returns rubric scores plus regions as normalised boxes, snapped to the nearest shape from the object model so findings point at an element and its owner.
Tests: box snapping, invalid boxes discarded, mapping to owners.
Done when:
- [ ] Every L5 finding names a shape id and an owner.

### T-16.5 L6 clicks: object model and UNO session          Size: M
Depends on: T-16.1
Files: +`deckforge/inspect/clicks.py`, +`deckforge/inspect/uno_session.py`, tests
Steps: `25` sections 6a and 6b. Object-model clicks (embedded chart workbooks, exhibit alt text JSON, real text frames, z-order reading order, section tracker, agenda, links, notes, hidden content, template layouts), then a LibreOffice UNO session on the renderer that opens the deck and verifies the same properties after a real load.
Tests: planted broken link, wrong tracker, workbook and chart value mismatch and wrong reading order detected, UNO check in the golden CI container.
Done when:
- [ ] Click checks run on every deck in under 3 s for 15 slides.

### T-16.6 PowerPoint fidelity runner (optional)          Size: M
Depends on: T-16.5
Files: +`tools/ppt_fidelity/runner.py` (Windows host), +`docs/ops/ppt_fidelity.md`
Steps: `25` section 6c. COM automation opens each golden deck in PowerPoint, exports PNGs, compares with LibreOffice renders, reports differences above a pixel threshold. Runs nightly on a Windows host, never in customer installs by default.
Done when:
- [ ] Nightly fidelity report for golden decks, with the diff images.

### T-16.7 L7 flow checks and L8 UI journeys          Size: M
Depends on: T-16.2, T-9.8
Files: +`deckforge/inspect/flow.py`, +`tests/e2e/journeys/*.spec.ts`, axe checks
Steps: `25` sections 7 and 9. Deck-level flow (storyboard review on a contact sheet, sequence rules, narrative flow judges, click-through continuity, exec summary coverage), and Playwright journeys for the stories in `26` with axe accessibility checks.
Tests: three identical layouts in a row and an exec summary number that differs from the body are detected, journeys green.
Done when:
- [ ] P16 exit demo passes, and every `26` story with a journey id has a passing test.

---

## P17 Knowledge base

### T-17.1 Card schema, validator and import          Size: L
Depends on: T-4.5
Files: +`deckforge/knowledge/schema.py`, +`deckforge/knowledge/validate.py`, +`knowledge/**` (cards), +`training/kb/import_*.py`, CLI `deckforge kb validate`, tests
Steps: `28` sections 2 to 4. Card models, validator (ids, links, detectors, strategies and owners exist), importers from `docs/FRAMEWORK_LIBRARY.md`, the TRD chart and QA rules, existing look-and-feel and consistency code, and the exhibit registry.
Tests: every imported card validates, a broken link or unknown detector fails validation.
Done when:
- [ ] About 800 global cards validate, with counts per type in the PR.

### T-17.2 KB build, release and kb_version          Size: M
Depends on: T-17.1
Files: +`deckforge/knowledge/build.py`, +`migrations/versions/*_runs_kb_version.py`, +`knowledge/RELEASES.md`, CLI `deckforge kb build --release`
Steps: `28` section 5. Compile cards into `kb_items` per namespace with embeddings, upload CLM candidate embeddings for rankable namespaces, write `kb_version`. Migration adds `runs.kb_version` and `runs.model_versions`. Every run stores both.
Tests: build is reproducible (same inputs give the same version hash), lite and server stores agree on search results for fixtures.
Done when:
- [ ] Runs show `kb_version` in the plan report.

### T-17.3 Retrieval modes and per-agent context packs          Size: M
Depends on: T-17.2, T-15.1
Files: +`deckforge/knowledge/kb.py` (`KnowledgeBase`), +`deckforge/tools/impl/knowledge.py` (`kb_search`, `kb_get`), ~`deckforge/context/builder.py`, tests
Steps: `28` section 6. By id, shortlist, rank (CLM), typed pick (Laya), context injection into prompt sections 2 and 3, tools for ReAct agents. Every output records `kb_refs`.
Tests: per-agent packs match the table in `28` section 6.2, digests stay within token budgets, `kb_refs` written.
Done when:
- [ ] Plan report cites card ids for frameworks, exhibits and standards.

### T-17.4 Design standards as the QA registry          Size: M
Depends on: T-17.1, T-6.1
Files: ~`deckforge/evaluators/*`, +`deckforge/knowledge/standards.py`, tests
Steps: `28` section 7 and `27` section 8.1. DS cards define severity, detectors, owner, strategies and acceptance. The cascade and `qa_router` read them instead of hard-coded maps. A sync test fails when a detector exists in code without a card or a card names a missing detector.
Tests: sync test, severity change in a card changes routing without code changes.
Done when:
- [ ] Every finding in the QA report carries a standard id.

### T-17.5 KB evals and maintenance loop          Size: M
Depends on: T-17.3
Files: +`evals/kb/*`, +`deckforge/evals/kb.py`, job `kb.maintenance`
Steps: `28` sections 8 and 9. Retrieval eval (recall at 5 per namespace), usefulness from accepted outputs that cite a card, stale and unused card report, teacher-drafted card proposals queued for review.
Done when:
- [ ] Monthly maintenance report generated and the retrieval eval meets its bar.

### T-17.6 Org knowledge cards          Size: M
Depends on: T-17.3, T-9.7
Files: +`deckforge/api/routers/knowledge.py`, `frontend/src/features/admin/knowledge/*`, tests
Steps: `28` section 10 and `26` US-11.5. Org cards (terminology, banned phrases, house frameworks, exemplars) with YAML import and export, validated with the same validator, scoped by `org_id`.
Tests: org isolation, validation errors surfaced in the UI.
Done when:
- [ ] An org admin adds a banned phrase and the next run's copy avoids it.

---

## P18 Product stories and data

### T-18.1 Later-phase tables          Size: M
Depends on: T-1.2
Files: +`migrations/versions/*_revisions_comments_variants_shares_usage.py`, ~`deckforge/db/models.py`, repositories, tests
Steps: tables `revisions`, `comments`, `slide_variants`, `shares`, `usage_daily` exactly as `23` section 3, with the indexes from `23` section 2.
Tests: migration up and down on PostgreSQL and SQLite, repository org filters.
Done when:
- [ ] `alembic upgrade head` and `downgrade -1` succeed in both modes.

### T-18.2 Revisions, variants, diff and restore APIs          Size: L
Depends on: T-18.1, T-15.5
Files: +`deckforge/api/routers/{revisions.py,variants.py}`, ~`runs.py`, tests
Steps: endpoints from `26` section 8 for US-6.2 to US-6.6 and US-7.1, US-7.2. Diff compares slide specs and renders per-slide change flags.
Tests: API tests per story acceptance criteria.
Done when:
- [ ] A revision, a variant choice and a restore each create the expected deck version.

### T-18.3 Review links, comments and approval          Size: L
Depends on: T-18.1
Files: +`deckforge/api/routers/{shares.py,comments.py}`, ~`deckforge/security/*`, tests
Steps: `26` US-10.1 to US-10.4. Signed expiring share links with view or comment rights, comments anchored to slide and shape, comment to revision, approval with audit entries.
Tests: link expiry, rights enforcement, anchor survives a new version when the shape still exists.
Done when:
- [ ] P18 exit demo passes end to end.

### T-18.4 Deck studio UI: revise, variants, diff, comments          Size: L
Depends on: T-18.2, T-18.3, T-9.5
Files: `frontend/src/features/studio/*`
Steps: `26` sections 5.3 and 6 (selection, revision panel, variant picker, diff view, comment threads, approve).
Done when:
- [ ] The `26` E6 and E10 journeys pass in Playwright.

### T-18.5 Brief quality meter and onboarding          Size: M
Depends on: T-9.3, T-5.5
Files: ~`frontend/src/features/briefs/*`, +`POST /briefs/{id}/check`
Steps: `26` US-3.1 and E1. Synchronous Laya `D_BRIEF_GAPS` check shows which inputs are missing before a run starts. First-run onboarding with the example project.
Done when:
- [ ] Meter updates within 300 ms while typing (debounced) on the reference server.

### T-18.6 Notifications and exports          Size: M
Depends on: T-18.1, T-10.8
Files: +`deckforge/notify/*`, +`deckforge/api/routers/exports.py`, `frontend/src/features/notifications/*`
Steps: `26` E8 and E13. Exports (pptx, pdf, png zip, xlsx of exhibit data) as jobs, in-app and email notifications with per-user preferences.
Done when:
- [ ] A finished run notifies its creator and the export bundle downloads.

### T-18.7 Product metrics          Size: S
Depends on: T-18.1
Files: +`deckforge/accounting/product_metrics.py`, admin usage page
Steps: `26` section 9 metrics computed install-locally from `usage_daily` and run tables. Nothing leaves the install.
Done when:
- [ ] Admin page shows the metrics for the last 30 days.

---

## 3. Release checklist (v1.0)

- [ ] All tickets P0 to P10 merged. P11 at least T-11.1 to T-11.5 with one promotion. P12 T-12.1 to T-12.4, T-12.10 and T-12.11.
- [ ] P13: `df-lm-v1` (32B and one smaller size) promoted on the gates in `19` section 6, with exports for every supported tier. No closed-model API in code or training data (CI grep and data register check).
- [ ] P14: memory plan and benchmarks measured on the reference server and the three laptop tiers. No OOM and no vLLM preemption in the load test.
- [ ] P15: all workflows run through agents and the DAP, the `27` section 8.5 worked example passes, agent suites meet their bars.
- [ ] P16: inspector L1 to L7 on by default, L4 judges promoted or in shadow with recorded metrics. The upstream Laya-Vision checkpoint is absent (licence check script).
- [ ] P17: KB release recorded on every run, design standards drive QA, retrieval eval passes.
- [ ] P18: stories with journey ids pass in Playwright.
- [ ] Eval suite `briefs` meets its pass bar on the reference node with on-prem models.
- [ ] Founder blind review: 20 slide pairs vs the previous release, preferred or tied in at least 60%, and the three sample-deck quality bars (Accenture, Bain, BCG, McKinsey style) reviewed on five briefs.
- [ ] Security suite green, Trivy and audits without critical findings, SBOM published.
- [ ] Load test pass bars met. Capacity table updated with measurements.
- [ ] Backup and restore drill recorded.
- [ ] Lite smoke green on three OSes. Installers available or the decision to defer recorded.
- [ ] Docs: `README`, operations guide, admin guide, API reference (OpenAPI rendered), licence notices.
