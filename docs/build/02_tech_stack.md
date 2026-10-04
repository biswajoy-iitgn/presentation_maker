# 02. Tech stack

Versions were read from PyPI and npm on 2026-10-04. The lockfiles (`uv.lock`, `frontend/package-lock.json`) are the source of truth after T-0.1. Upgrades go through a ticket that runs the full test suite and the golden-deck suite.

Licence check rule: only permissive licences (MIT, BSD, Apache-2.0, ISC, MPL-2.0 as a library, PSF, OFL for fonts) in anything we ship inside our images or wheel. Copyleft services (LibreOffice MPL/LGPL, SearXNG AGPL) run as separate, unmodified processes and are listed in `NOTICE`.

## 1. Platform

| Item | Choice | Version | Notes |
|---|---|---|---|
| Language | CPython | 3.12.x | Same minor on all OSes. 3.13 allowed once every dependency publishes wheels |
| Package and env manager | uv | 0.12.x | `uv sync`, `uv run`, `uv lock`. Works identically on macOS, Windows, Linux |
| Task runner | poethepoet (`poe`) | 0.48.x | Tasks in `pyproject.toml`. Replaces Make, which Windows lacks |
| Node.js (frontend build only) | Node LTS | 24.x | Not needed at runtime. The built SPA is shipped inside the wheel and the nginx image |
| Containers | Docker Engine with Compose v2 | Engine 27+ | Docker Desktop on macOS and Windows, native on Linux. Images built multi-arch (amd64, arm64) |

## 2. Backend libraries (Python)

| Purpose | Library | Version | Licence | Why this one |
|---|---|---|---|---|
| Web framework | fastapi | 0.142.x | MIT | Async, Pydantic-native, OpenAPI generation |
| ASGI server | uvicorn[standard] | 0.54.x | BSD | Cross-platform. `--workers` uses spawn on Windows. Gunicorn is not used (no Windows support) |
| SSE | sse-starlette | 3.5.x | BSD | Server-sent events with ping and disconnect handling |
| Multipart uploads | python-multipart | 0.0.32 | Apache-2.0 | FastAPI upload parsing |
| Data validation | pydantic | 2.13.x | MIT | Contracts, LLM output schemas |
| Settings | pydantic-settings | 2.15.x | MIT | `DF_*` env vars, `.env` files |
| ORM | sqlalchemy[asyncio] | 2.1.x | MIT | Same models for SQLite and PostgreSQL |
| Migrations | alembic | 1.20.x | MIT | One migration chain, dialect-guarded where needed |
| PostgreSQL driver | psycopg[binary,pool] | 3.3.x | LGPL-3.0 (library, dynamically linked, allowed) | Async, pipeline mode, LISTEN/NOTIFY. Also used by the LangGraph Postgres checkpointer |
| SQLite async driver | aiosqlite | 0.22.x | MIT | Lite mode |
| Vectors (server) | pgvector | 0.5.x | MIT | SQLAlchemy `Vector` type |
| Cache and pub/sub client | redis | 8.1.x | MIT | Talks to Valkey |
| Orchestration | langgraph | 1.2.x | MIT | Graphs, `Send`, `interrupt`, `Command`, `RetryPolicy`, `CachePolicy`, streaming |
| Checkpointer (server) | langgraph-checkpoint-postgres | 3.1.x | MIT | `AsyncPostgresSaver`, `AsyncPostgresStore` |
| Checkpointer (lite) | langgraph-checkpoint-sqlite | 3.1.x | MIT | `AsyncSqliteSaver` |
| LLM abstractions | langchain, langchain-core | 1.4.x, 1.6.x | MIT | `init_chat_model`, `with_structured_output`, prompts, tools, `create_agent` with middleware |
| OpenAI-compatible models | langchain-openai | 1.6.x | MIT | vLLM, Ollama and LiteLLM endpoints (`ChatOpenAI` with `base_url`) |
| Anthropic models | langchain-anthropic | 1.7.x | MIT | Official `anthropic` SDK underneath |
| Ollama native (optional) | langchain-ollama | 1.1.x | MIT | Only if the OpenAI-compatible Ollama endpoint misses a feature |
| MCP client and server | mcp, langchain-mcp-adapters | 2.3.x, 0.3.x | MIT | Expose DeckForge tools, consume customer MCP tools (P7, optional) |
| Decision engine | laya | 0.3.27 (pin exactly) | Apache-2.0 | System 1 decisions and judges. Extras: `laya[serve]` in the laya image, `laya[onnx]` for CPU laptops |
| Embeddings (in-process) | fastembed | 0.8.x | Apache-2.0 | ONNX runtime, no torch, works on all OSes. Default model `BAAI/bge-small-en-v1.5`, multilingual option `intfloat/multilingual-e5-small` |
| HTTP client | httpx | 0.28.x | BSD | Async calls to Laya, renderer, search, fetch |
| Retries | tenacity | 9.1.x | Apache-2.0 | Tool and adapter retries outside LangGraph nodes |
| Templates for prompts | jinja2 | 3.1.x | BSD | Prompt files rendered with `StrictUndefined` |
| YAML | pyyaml | 6.0.x | MIT | Config, question schemas, prompt front matter |
| PPTX | python-pptx | 1.0.2 | MIT | Existing compiler |
| XML | lxml | 6.1.x | BSD | OOXML edits. Parsers created with `resolve_entities=False` |
| Images | pillow | 12.3.x | MIT-CMU | Existing asset pipeline, text metrics |
| Fonts | fonttools | 4.66.x | MIT | Font metadata, metric checks |
| Numerics | numpy | 2.5.x | BSD | Existing code |
| Tabular data | pandas | 3.0.x | BSD | Data profiling and calcs |
| Excel read | openpyxl | 3.1.x | MIT | xlsx ingestion (read-only mode) |
| Columnar snapshots | pyarrow | pin current major | Apache-2.0 | Parquet snapshots of cleaned tables |
| Model downloads | huggingface_hub | pin current major (already a dependency of laya and fastembed) | Apache-2.0 | `deckforge laya pull`, pinned revisions, offline cache |
| PDF to PNG | pypdfium2 | 5.14.x | Apache-2.0 / BSD | Preview rasterisation on all OSes |
| PDF text | pdfplumber | 0.11.x | MIT | Reference document ingestion |
| DOCX text | python-docx | 1.2.x | MIT | Reference document ingestion |
| Web page extraction | trafilatura | 2.3.x | Apache-2.0 | Main text from fetched pages |
| File type detection | filetype | 1.2.x | MIT | Magic-byte checks without libmagic (works on Windows) |
| Safe XML | defusedxml | 0.7.x | PSF | Parsing untrusted XML parts |
| Preview server (renderer image) | unoserver | 3.7 | MIT | Warm LibreOffice instances, `unoconvert` client |
| Auth tokens | pyjwt | 2.15.x | MIT | JWT access tokens |
| Password hashing | argon2-cffi | 25.1.x | MIT | argon2id |
| OIDC | authlib | 1.8.x | BSD | SSO with Azure AD, Okta, Keycloak |
| Encryption of stored secrets | cryptography | 50.x | Apache-2.0 / BSD | AES-GCM for provider credentials |
| Logging | structlog | 26.1.x | MIT / Apache-2.0 | JSON logs with context vars |
| Tracing | opentelemetry-sdk, -exporter-otlp, -instrumentation-fastapi, -httpx, -sqlalchemy | 1.45.x / 0.66b0 | Apache-2.0 | Traces to any OTLP backend |
| Metrics | prometheus-client | 0.26.x | Apache-2.0 | `/metrics` |
| User data dirs | platformdirs | 4.12.x | MIT | Lite mode paths on each OS |
| Fast JSON and hashing | orjson, xxhash | 3.12.x, 4.0.x | Apache/MIT, BSD | Cache keys and payloads |

Dev and test only:

| Purpose | Library | Version |
|---|---|---|
| Tests | pytest, pytest-asyncio, pytest-xdist, pytest-cov | 9.1.x, 1.4.x, 3.8.x, 7.1.x |
| HTTP mocking | respx | 0.23.x |
| Property tests | hypothesis | 6.168.x |
| Containers in integration tests | testcontainers | 4.15.x |
| Load tests | locust | 2.46.x |
| Lint and format | ruff | 0.16.x |
| Types | mypy | 2.4.x |
| Dependency audit | pip-audit | 2.10.x |

## 3. Frontend

| Purpose | Library | Version |
|---|---|---|
| UI | react, react-dom | 19.3.x |
| Build | vite | 8.3.x |
| Language | typescript | 7.0.x (if a tool fails on 7.x, pin 5.9.x and record a decision) |
| Server state | @tanstack/react-query | 5.104.x |
| Routing | @tanstack/react-router | 1.170.x |
| Styles | tailwindcss | 4.3.x |
| Accessible primitives | @radix-ui/react-* | latest 1.x per component |
| Forms and validation | react-hook-form, zod | 7.89.x, 4.6.x |
| API types and client | openapi-typescript, openapi-fetch | 7.13.x, 0.17.x |
| Unit tests | vitest | 5.0.x |
| End-to-end tests | @playwright/test | 1.63.x |

## 4. Services

| Service | Image | Version policy | Licence | Notes |
|---|---|---|---|---|
| Reverse proxy | `nginx` | stable tag, pinned by digest at release | BSD-2 | Config in `deploy/nginx/` |
| Database | `pgvector/pgvector:pg17` | PostgreSQL 17, pgvector 0.8 | PostgreSQL, PostgreSQL | One database `deckforge`, schemas `app`, `lg` (LangGraph) |
| Cache, pub/sub | `valkey/valkey:8` | 8.x | BSD-3 | `maxmemory-policy allkeys-lru` for the cache DB, separate logical DB for rate limits |
| Object storage (optional) | `chrislusf/seaweedfs` | 3.x | Apache-2.0 | Only in the multi-node profile. Any S3-compatible store works |
| LLM gateway | `ghcr.io/berriai/litellm` | pin a tested tag | MIT (core) | Virtual keys per org, budgets, rpm/tpm limits, fallbacks |
| LLM serving (GPU) | `vllm/vllm-openai` | pin a tested tag | Apache-2.0 | `--enable-prefix-caching`, guided JSON for structured output |
| LLM serving (laptop) | Ollama | latest stable | MIT | macOS, Windows, Linux installers. OpenAI-compatible endpoint at `http://localhost:11434/v1` |
| Decision engine | `deckforge-laya` (our image, `laya[serve]==0.3.27`) | ours | Apache-2.0 | `laya-serve` on port 8200, internal only |
| Preview renderer | `deckforge-renderer` (our image: Debian slim, LibreOffice Impress, unoserver, bundled fonts) | ours | MPL/LGPL (LibreOffice, separate process) | Port 8100, internal only |
| Search (optional) | `searxng/searxng` | pin a tested tag | AGPL-3.0 (separate process, unmodified) | Internal only |
| Telemetry | `otel/opentelemetry-collector-contrib`, `prom/prometheus`, `grafana/grafana` | pinned | Apache-2.0, Apache-2.0, AGPL-3.0 (Grafana, separate optional process) | Observability profile only |

## 5. Models

DeckForge never hard-codes a model. Roles map to models in `config/models.yaml` (`07`). Defaults below are starting points, selected finally by the eval harness (T-11.6).

| Role | On-prem default (vLLM or Ollama) | Cloud profile (Anthropic, opt-in per org) |
|---|---|---|
| `planner` | Strongest open-weight instruct model the GPU host fits with at least 64k context and reliable JSON-schema output (candidates to evaluate: gpt-oss-120b, Qwen3 large MoE, Llama large instruct) | `claude-opus-5-5`, effort `high` |
| `writer` | Same model as `planner` (one model keeps one prefix cache) | `claude-opus-5-5`, effort `medium` |
| `extractor` | Same model, or a smaller instruct model if latency demands it | `claude-opus-5-5`, effort `low` |
| `judge` | Same model as `planner` | `claude-opus-5-5`, effort `low` |
| `vision_judge` | Open-weight vision-language model (candidates: Qwen VL family, Llama vision) | `claude-opus-5-5`, effort `medium` |
| `embed` | fastembed `BAAI/bge-small-en-v1.5` in-process | same (embeddings stay local) |
| Laya | `convaiinnovations/laya` and `laya-multilingual` as bases, fine-tuned DeckForge checkpoint `df-laya-v1` after P11 | same (Laya always local) |

Using cheaper Anthropic models (`claude-sonnet-5-5`, `claude-haiku-4-5`) for some roles is a founder decision after the eval harness shows quality holds. Lowering `effort` on `claude-opus-5-5` is the first cost lever.

## 6. Cross-platform notes (apply everywhere)

| Topic | Rule |
|---|---|
| Paths | `pathlib.Path` only. Blob keys are POSIX strings (`/`) and are converted to paths only inside `FsBlobStore` |
| User data | `platformdirs.user_data_dir("DeckForge", "DeckForge")` for lite mode. Never write next to the installed package |
| Processes | No `os.fork`. `multiprocessing` start method `spawn` everywhere. Long work runs in asyncio tasks or subprocesses |
| Event loop | Lite mode on Windows uses the default Proactor loop (aiosqlite is fine). Server mode with psycopg async on Windows needs `asyncio.WindowsSelectorEventLoopPolicy()`. Server mode is supported on Linux and in Docker only |
| LibreOffice discovery | `DF_SOFFICE_PATH`, else search: macOS `/Applications/LibreOffice.app/Contents/MacOS/soffice`, Windows `C:\Program Files\LibreOffice\program\soffice.exe` and the x86 path, Linux `shutil.which("soffice")` |
| Fonts | Bundled in `deckforge/fonts/` (Liberation Sans, Gelasio, Carlito, Caladea and the families' display fonts, all OFL or Apache). Metrics read from these files |
| File names | Uploaded file names are display-only. Stored keys use UUIDs to avoid Windows reserved names and path length limits |
| Line endings | `.gitattributes` sets `* text=auto eol=lf`. Generated files write `\n` |
| Torch | Only the optional `laya` extra pulls torch. Lite mode without it sets `DF_LAYA_MODE=off` and decisions fall back to LLM or deterministic defaults |
