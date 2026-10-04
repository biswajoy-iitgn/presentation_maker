# 03. Repository layout and conventions

## 1. Target layout

Existing folders are kept. New ones are marked `(new)`.

```text
presentation_maker/
├── pyproject.toml                 # one distribution: deckforge, extras: lite, server, laya, dev
├── uv.lock                        # (new) committed
├── .gitattributes                 # (new) eol=lf
├── .env.example                   # (new) every DF_* variable with a safe default
├── config/                        # (new)
│   ├── models.yaml                # role -> provider/model mapping (07)
│   ├── models.cloud.yaml          # opt-in cloud profile
│   └── limits.yaml                # quotas, rate limits, run limits (05)
├── prompts/                       # (new) versioned prompt files (07, section 6)
│   ├── intake/ planning/ compose/ judge/ research/ repair/
├── deckforge/
│   ├── __init__.py
│   ├── settings.py                # (new) Settings (section 4)
│   ├── ports.py                   # (new) Protocols from 01, section 5
│   ├── wiring.py                  # (new) builds adapters from Settings
│   ├── cli.py                     # (new) `deckforge serve|worker|migrate|render|eval|laya`
│   ├── core/                      # (new) pure domain models (04, section 2)
│   ├── story/                     # existing: plan schema, render, report
│   ├── viz/                       # existing: style, marks, frame, scale, select, exhibits/
│   ├── render/                    # existing: canvas, metrics, charts
│   ├── assets/                    # existing: sources, treatment, resolver, qa, cache
│   ├── qa/                        # existing: lint, repair, lookfeel, consistency
│   ├── fonts/                     # (new) bundled OFL/Apache fonts + fonts.json index
│   ├── data/                      # (new) pure: dummy data generator, calc recipes, column mapping rules
│   ├── design/                    # (new) pure: palette maths (OKLab, contrast, ramps), sample preview deck spec
│   ├── ingest/                    # (new) excel/csv profiling, template -> DesignSystem, pdf/docx text
│   ├── knowledge/                 # (new) framework cards from FRAMEWORK_LIBRARY.md, embeddings, kb build
│   ├── renderer/                  # (new) preview adapters: soffice (lite), http (server), rasterize (pypdfium2)
│   ├── accounting/                # (new) usage ledger, quotas
│   ├── llm/                       # (new) registry, adapters, structured output, usage accounting
│   ├── prompting/                 # (new) prompt loader and renderer
│   ├── context/                   # (new) ContextBuilder, budgets, compaction, retrieval
│   ├── cache/                     # (new) cache layers and key builders
│   ├── decisions/                 # (new) Laya engine adapters, question registry, decision log
│   │   └── questions/             # (new) one YAML per decision id (09)
│   ├── evaluators/                # (new) cascade, judges, defect model glue
│   ├── tools/                     # (new) ToolSpec, registry, executor, implementations, selector middleware
│   ├── research/                  # (new) search adapters, fetch with SSRF guard, extraction, citations
│   ├── graphs/                    # (new) LangGraph state, nodes, subgraphs, builders
│   ├── jobs/                      # (new) queue adapters, worker loop, job handlers
│   ├── events/                    # (new) event model, bus adapters
│   ├── storage/                   # (new) blob store adapters
│   ├── db/                        # (new) SQLAlchemy models, repositories, session, alembic/
│   ├── api/                       # (new) FastAPI app, routers, schemas, auth, deps, sse, static/
│   ├── renderer_service/          # (new) FastAPI app of the renderer container (unoserver pool)
│   ├── evals/                     # (new) eval harness code (datasets live in /evals)
│   ├── testing/                   # (new) fakes and the fake wiring profile (DF_TEST_PROFILE=fake)
│   ├── security/                  # (new) auth helpers, crypto, upload validation, ssrf guard, pii
│   ├── observability/             # (new) logging, tracing, metrics
│   ├── serve.py, doctor.py, bundle.py, cli_init.py   # (new) CLI command implementations
├── frontend/                      # (new) React SPA (13)
├── deploy/                        # (new)
│   ├── docker/                    # Dockerfile.app, Dockerfile.renderer, Dockerfile.laya, Dockerfile.nginx
│   ├── compose/                   # docker-compose.yml, profiles, .env.server.example
│   ├── nginx/                     # nginx.conf, conf.d/deckforge.conf
│   ├── litellm/                   # config.yaml
│   ├── observability/             # otel-collector.yaml, prometheus.yml, grafana dashboards
│   └── helm/                      # (P12) chart
├── training/                      # (new) Laya data builders, fine-tune scripts, calibration (09)
├── evals/                         # (new) golden briefs, judge datasets, eval configs (17)
├── examples/                      # existing
├── tests/
│   ├── unit/                      # (new) fast, no network, no services
│   ├── integration/               # (new) needs PostgreSQL and Valkey (testcontainers or compose)
│   ├── e2e/                       # (new) Playwright
│   └── (existing test files move to tests/unit/ in T-0.2)
└── docs/
```

## 2. Module boundaries

Imports flow downward only. A lint rule (T-0.4, `tests/unit/test_import_rules.py`) enforces it by parsing imports.

| Layer | Packages | May import |
|---|---|---|
| 0 Domain | `core`, `story`, `viz`, `render`, `qa`, `assets` (sources and treatment only), `data`, `design` | stdlib, pydantic, numpy, pandas, python-pptx, lxml, pillow, each other |
| 1 Ports | `ports` | layer 0 |
| 2 Services | `ingest`, `llm`, `prompting`, `context`, `cache`, `decisions`, `evaluators`, `tools`, `research`, `events`, `storage`, `knowledge`, `renderer`, `accounting` | layers 0 and 1, their own third-party libraries |
| 3 Orchestration | `graphs`, `jobs`, `evals` | layers 0 to 2 |
| 4 Delivery | `api`, `cli`, `renderer_service`, `serve`, `doctor`, `bundle`, `cli_init` | layers 0 to 3 |
| Cross-cutting | `settings`, `observability`, `security`, `db`, `wiring` | anything below delivery. `db` is imported by `jobs`, `api`, `accounting` and repositories only |
| Test support | `testing` | anything. Production modules never import it, except `wiring.py` when `DF_TEST_PROFILE=fake` |

Rules:
- Graph nodes never import `db` directly. They call repositories passed in the runtime context.
- Domain packages never read settings or environment variables.
- Only `wiring.py` imports concrete adapters.

## 3. Coding standards

| Topic | Standard |
|---|---|
| Style | `ruff format` (line length 120), `ruff check` with rules E, F, I, B, UP, ASYNC, S (bandit subset), PL subset |
| Types | Type hints on all public functions. `mypy --strict` on new packages (`deckforge/{llm,decisions,tools,graphs,jobs,api,db,cache,context,evaluators}`). Existing packages: `mypy` default |
| Async | All I/O is async. CPU-heavy work (PPTX compile, pandas profiling) runs via `asyncio.to_thread`. No blocking calls in the event loop |
| Errors | Raise typed exceptions from `deckforge/core/errors.py` (`DeckForgeError` base, `ValidationFailed`, `NotFound`, `QuotaExceeded`, `ProviderError`, `ToolError`, `DecisionUnavailable`). API maps them to problem+json (`05`) |
| Logging | `structlog.get_logger(__name__)`. Bind `org_id`, `run_id`, `node` in context. Never log secrets or full prompts at INFO |
| IDs | UUIDv7 (time-ordered) via `deckforge.core.ids.new_id()`. Stored as `uuid` in PostgreSQL and `CHAR(36)` in SQLite |
| Time | Timezone-aware UTC (`datetime.now(UTC)`). Stored as `timestamptz` |
| Money and tokens | Integers (micro-dollars for cost, raw counts for tokens) |
| Config | All configuration through `Settings` or YAML in `config/`. No magic numbers in code without a named constant |
| Docstrings | One line for most functions. Modules start with a short docstring stating purpose |
| Tests | One test file per module under `tests/unit/<package>/test_<module>.py`. Test names state behaviour: `test_lease_skips_jobs_of_org_at_cap` |

## 4. Settings (complete list of environment variables)

`deckforge/settings.py` defines `class Settings(BaseSettings)` with `model_config = SettingsConfigDict(env_prefix="DF_", env_file=".env", extra="ignore")`. Every variable below must exist with the given default. `.env.example` lists them all.

| Variable | Type | Default | Used by |
|---|---|---|---|
| `DF_MODE` | `lite` or `server` | `lite` | wiring |
| `DF_DATA_DIR` | path | platformdirs user data dir | lite: SQLite file, blobs, cache |
| `DF_PUBLIC_BASE_URL` | url | `http://127.0.0.1:8765` | links in emails and webhooks |
| `DF_HOST`, `DF_PORT` | str, int | `127.0.0.1`, `8765` (lite) / `0.0.0.0`, `8000` (server) | `deckforge serve` |
| `DF_API_WORKERS` | int | `1` (lite), `4` (server) | uvicorn workers |
| `DF_DATABASE_URL` | str | `sqlite+aiosqlite:///{DF_DATA_DIR}/deckforge.db` | db |
| `DF_DATABASE_POOL_SIZE` | int | `10` | db (server) |
| `DF_REDIS_URL` | str or empty | empty (lite) | cache, events, rate limits |
| `DF_BLOB_BACKEND` | `fs` or `s3` | `fs` | storage |
| `DF_BLOB_ROOT` | path | `{DF_DATA_DIR}/blobs` | FsBlobStore |
| `DF_S3_ENDPOINT`, `DF_S3_BUCKET`, `DF_S3_REGION`, `DF_S3_ACCESS_KEY`, `DF_S3_SECRET_KEY` | str | empty | S3BlobStore |
| `DF_MODELS_FILE` | path | `config/models.yaml` | llm |
| `DF_LLM_GATEWAY_URL` | url or empty | empty | llm (server, OpenAI-compatible gateway) |
| `DF_LLM_GATEWAY_KEY` | secret | empty | llm |
| `ANTHROPIC_API_KEY` | secret | empty | llm, Anthropic adapter (standard SDK variable) |
| `DF_ALLOW_CLOUD_LLM` | bool | `false` | llm: global switch, org setting must also allow |
| `DF_LAYA_MODE` | `off`, `inproc`, `http` | `off` (lite), `http` (server) | decisions |
| `DF_LAYA_URL` | url | `http://laya:8200` | HttpLaya |
| `DF_LAYA_API_KEY` | secret | empty | HttpLaya, matches `LAYA_API_KEY` in the laya container |
| `DF_LAYA_CHECKPOINT` | str | `convaiinnovations/laya` | InprocLaya model id or local path |
| `DF_LAYA_TIMEOUT_S` | float | `2.0` | HttpLaya |
| `DF_RENDERER_URL` | url or empty | empty (lite), `http://renderer:8100` | HttpRenderer |
| `DF_SOFFICE_PATH` | path or empty | auto-detect | SofficeRenderer |
| `DF_SEARCH_BACKEND` | `none`, `searxng`, `brave`, `bing`, `custom` | `none` | research |
| `DF_SEARXNG_URL` | url | `http://searxng:8080` | research |
| `DF_SEARCH_API_KEY` | secret | empty | research (non-SearXNG backends) |
| `DF_FETCH_ALLOWED_DOMAINS` | comma list or empty | empty (all public domains) | research fetch |
| `DF_EGRESS_PROXY` | url or empty | empty | all outbound HTTP from workers |
| `DF_JWT_SECRET` | secret, at least 32 bytes | generated at first lite start, required in server | auth |
| `DF_JWT_ACCESS_TTL_S` | int | `900` | auth |
| `DF_REFRESH_TTL_S` | int | `604800` | auth |
| `DF_SECRETS_KEY` | base64 32 bytes | generated at first lite start, required in server | AES-GCM for provider credentials |
| `DF_OIDC_ISSUER`, `DF_OIDC_CLIENT_ID`, `DF_OIDC_CLIENT_SECRET` | str | empty | OIDC |
| `DF_CORS_ORIGINS` | comma list | empty (same origin) | api |
| `DF_MAX_UPLOAD_MB` | int | `50` | api, nginx config must match |
| `DF_WORKER_ID` | str | hostname + pid | jobs |
| `DF_WORKER_SLOTS` | int | `2` (lite), `4` (server) | concurrent jobs per worker process |
| `DF_WORKER_KINDS` | comma list | all | job kinds a worker accepts |
| `DF_WORKER_DRAIN_S` | int | `600` | graceful shutdown wait |
| `DF_RENDERER_INSTANCES` | int | CPU cores / 2 | renderer service pool size |
| `DF_TEST_PROFILE` | `""` or `fake` | `""` | wiring: `fake` builds every port from `deckforge.testing` |
| `DF_<SECRET>_FILE` | path | empty | for each secret above (`JWT_SECRET`, `SECRETS_KEY`, `LAYA_API_KEY`, `LLM_GATEWAY_KEY`, `S3_SECRET_KEY`, `OIDC_CLIENT_SECRET`, `SEARCH_API_KEY`): read the value from this file |
| `DF_RUN_MAX_CONCURRENCY` | int | `6` | LangGraph `max_concurrency` per run |
| `DF_ORG_MAX_ACTIVE_RUNS` | int | `5` | queue admission |
| `DF_LOG_LEVEL` | str | `INFO` | observability |
| `DF_LOG_JSON` | bool | `false` (lite), `true` (server) | observability |
| `DF_OTEL_ENDPOINT` | url or empty | empty | tracing |
| `DF_METRICS_ENABLED` | bool | `false` (lite), `true` (server) | `/metrics` |
| `DF_LANGFUSE_HOST`, `DF_LANGFUSE_PUBLIC_KEY`, `DF_LANGFUSE_SECRET_KEY` | str | empty | optional tracing |

## 5. Task runner commands

Defined in `pyproject.toml` under `[tool.poe.tasks]`. All work on Windows, macOS, Linux.

| Command | Does |
|---|---|
| `uv run poe check` | `ruff check`, `ruff format --check`, `mypy` (strict packages), `pytest tests/unit -n auto` |
| `uv run poe test` | unit tests only |
| `uv run poe test-int` | integration tests (needs Docker for testcontainers) |
| `uv run poe test-e2e` | builds frontend, starts lite server, runs Playwright |
| `uv run poe fmt` | `ruff format` and `ruff check --fix` |
| `uv run poe migrate` | `alembic upgrade head` against `DF_DATABASE_URL` |
| `uv run poe dev` | `deckforge serve --reload` (lite) plus `npm run dev` in `frontend/` (two processes via `poe` parallel task) |
| `uv run poe golden` | renders golden decks and compares (`17`) |
| `uv run poe eval` | runs the eval harness on `evals/` |
| `uv run poe openapi` | writes `frontend/src/api/openapi.json` and regenerates TypeScript types |
| `uv run poe audit` | `pip-audit` and `npm audit --omit=dev` |

## 6. pyproject extras

```toml
[project.optional-dependencies]
lite   = ["aiosqlite==0.22.*", "langgraph-checkpoint-sqlite==3.1.*"]
server = ["psycopg[binary,pool]==3.3.*", "langgraph-checkpoint-postgres==3.1.*", "pgvector==0.5.*",
          "redis==8.1.*", "boto3==1.43.*"]
laya   = ["laya==0.3.27"]
laya-onnx = ["laya[onnx]==0.3.27"]
dev    = ["pytest==9.1.*", "pytest-asyncio==1.4.*", "pytest-xdist==3.8.*", "pytest-cov==7.1.*", "respx==0.23.*",
          "hypothesis==6.168.*", "testcontainers==4.15.*", "ruff==0.16.*", "mypy==2.4.*", "poethepoet==0.48.*",
          "pip-audit==2.10.*", "locust==2.46.*"]
```

Base dependencies are everything in `02` section 2 that both modes need. `uv sync --extra lite --extra dev` is the default developer setup.

## 7. Git and PR conventions

- Branch per ticket: `t-<phase>-<n>-<slug>` unless the environment mandates a branch name.
- Commit message: `T-x.y: <imperative summary>` then a blank line and what changed and why.
- A PR never mixes a refactor with a behaviour change unless the ticket says so.
- Generated files (OpenAPI JSON, TS types) are committed and regenerated by `poe openapi` in the same PR as the API change.
