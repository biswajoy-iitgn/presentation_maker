# DeckForge Build Plan V3

| Field | Value |
|---|---|
| Status | V3 draft, 2026-10-04. Supersedes `docs/BUILD_PLAN.md` (V2) for everything after the M1 renderer |
| Product scope | `docs/PRD_V2.md` (decisions D1 to D15) |
| Design depth | `docs/TRD_V2.md` (slide grammar, chart tiers, QA-1 to QA-11, data engine) |
| Audience | A coding agent (a small model such as Claude Haiku 4.5 is the target reader) or an engineer implementing tickets in order |
| Goal | A commercial, on-prem-first presentation maker that runs on macOS, Windows and Linux for one user, and as a multi-tenant server behind nginx for many concurrent users |

---

## 1. How to use this plan

This plan is written so that a model with limited context can build the product one ticket at a time without making architecture decisions. Every decision is already made here. If something is missing, the agent stops and writes a decision request (section 5), it does not improvise.

Read in this order the first time:

1. This file (rules, glossary, defaults).
2. `01_architecture.md` (what the system is).
3. `03_repo_layout_and_conventions.md` (where code goes, how to write it).
4. `18_work_breakdown.md` (the tickets). Then, for each ticket, only the documents the ticket links to.

### 1.1 Rules for the implementing agent

| # | Rule |
|---|---|
| R1 | Implement tickets in the order of `18_work_breakdown.md`. A ticket starts only when every ticket in its "Depends on" list is merged |
| R2 | Touch only the files a ticket lists. If another file must change, add it to the ticket's PR description with one line of reason |
| R3 | Never change a contract (a Pydantic model, a DB table, an API path, an env var, an event type, a Laya question id) except through a ticket that says so. Contracts are listed in `04_domain_and_data_model.md`, `05_api.md` and `09_laya_decisions_and_evaluators.md` |
| R4 | Use only the libraries and versions in `02_tech_stack.md`. Adding a dependency needs a decision request |
| R5 | Every ticket ships with the tests its "Tests" section names. `uv run poe check` must pass before commit (lint, types, unit tests) |
| R6 | No network calls in unit tests. Use the fakes defined in `17_testing_ci_evals.md` (FakeLLM, FakeLaya, FakeBlobStore, FakeRenderer) |
| R7 | Code must run on macOS, Windows and Linux in lite mode. Use `pathlib`, never hard-coded `/` paths, never `os.fork`, never shell pipelines in Python code |
| R8 | Secrets come from environment variables or the encrypted credentials table. Never commit a key. Never log a prompt that contains customer data at INFO level |
| R9 | Each PR: one ticket, title `T-x.y: <ticket title>`, body lists files changed, tests added, and the "Done when" checklist ticked |
| R10 | When a ticket's instructions conflict with existing code, the ticket wins for new code, and existing code is changed only if the ticket says so |

### 1.2 Definition of done (every ticket)

- All "Done when" items in the ticket are true and checked by a test or a command whose output is pasted in the PR.
- `uv run poe check` passes locally (ruff, mypy on changed packages, pytest unit suite).
- New public functions have type hints and a one-line docstring.
- No TODO without a ticket id (`# TODO(T-7.4): ...`).
- Docs updated when the ticket changes a contract.

---

## 2. Document map

| File | Answers |
|---|---|
| `01_architecture.md` | Components, deployment modes, request lifecycle, capacity model, ports and adapters |
| `02_tech_stack.md` | Every library and service with pinned version, licence and the reason it was chosen |
| `03_repo_layout_and_conventions.md` | Folder structure, module boundaries, coding standards, task runner commands |
| `04_domain_and_data_model.md` | Pydantic domain contracts, PostgreSQL DDL, blob layout, retention |
| `05_api.md` | REST API, auth, SSE events, errors, rate limits, quotas, webhooks, API keys |
| `06_orchestration_langgraph.md` | LangGraph graphs, state schema, nodes, edges, interrupts, checkpointing, streaming, worker loop |
| `07_llm_layer.md` | Model roles, providers, gateway, structured output, prompts, retries, cost accounting |
| `08_tools.md` | Tool contract, registry, executor, Laya-based tool selection, MCP |
| `09_laya_decisions_and_evaluators.md` | Laya deployment, decision catalogue, question schemas, calibration, evaluator cascade, fine-tuning pipeline |
| `10_context_and_memory.md` | Context builder, token budgets, compaction, retrieval, long-term memory, untrusted content |
| `11_caching.md` | Ten cache layers, keys, TTLs, invalidation, tenancy isolation |
| `12_render_engine_and_assets.md` | PPTX compiler, template ingestion, preview renderer, fonts across OS, asset pipeline |
| `13_frontend.md` | Web app pages, components, state, SSE client |
| `14_deployment_nginx_scaling.md` | Lite install on three OSes, Docker Compose, nginx config, scaling, air-gapped install, backups |
| `15_security.md` | AuthN/Z, tenancy, upload safety, SSRF, prompt injection, secrets, compliance checklist |
| `16_observability.md` | Logs, traces, metrics, dashboards, alerts |
| `17_testing_ci_evals.md` | Test pyramid, fakes, CI matrix, golden decks, eval harness, load tests |
| `18_work_breakdown.md` | Phases P0 to P12 and every ticket with files, steps, tests and done criteria |

---

## 3. Glossary

| Term | Meaning |
|---|---|
| Brief | What the user asks for: topic, requirements, audience, data available, what to show (D5). Model `Brief` |
| Project | A workspace that holds briefs, data files, a chosen template and the decks generated for it |
| Run | One execution of the deck graph for one brief. Has a status, a stage, events and artifacts. LangGraph `thread_id` = run id |
| Plan | The typed reasoning chain: problem, issue tree, analyses, storyline, slide plan. Existing model `deckforge.story.plan.Plan` |
| Slide spec | The fully resolved description of one slide (archetype, title, exhibit spec, commentary, assets) that the renderer compiles |
| Exhibit | A chart or visual on a slide (waterfall, profit pool, gap bars, site map, matrix, heat table, roadmap and so on) |
| Fact | A number computed deterministically from data, referenced in text as `{fact_id}` and resolved at render time |
| Design system | Colours, fonts, grid, layouts and logo rules, from a style family or extracted from a customer template |
| Style family | A built-in design system (MERIDIAN, VERDANT and later others) |
| Decision | A fast typed judgement made by Laya (a choice, a score or a probability) with a calibrated confidence |
| Judge | An evaluator question about quality (for example "is this an action title"). Tier 1 judges run on Laya, Tier 2 on an LLM, Tier 3 on a vision LLM |
| Defect | A QA finding with a code, a severity, evidence and a suggested repair |
| Lite mode | Single-user install on a laptop: SQLite, local files, in-process worker, no Docker |
| Server mode | Multi-tenant install: PostgreSQL, Valkey, object storage, nginx, separate workers, renderer and model services |
| Role (LLM) | A named purpose such as `planner`, `writer`, `judge`, mapped in config to a provider and model |
| Org | A tenant (customer company). All data rows carry `org_id` |

---

## 4. Defaults decided in this plan

These are decisions taken so that work can proceed. The founder can override any of them through a decision request. Each default names the document where it is applied.

| # | Default | Why | Where |
|---|---|---|---|
| A1 | Python 3.12 for all backend code, managed by `uv` | Existing code is Python. numpy 2.5 and SQLAlchemy 2.1 need 3.11 or later. 3.12 has wheels for every dependency on all three OSes | `02` |
| A2 | Two deployment modes from one codebase: lite (SQLite, files, in-process worker) and server (PostgreSQL, Valkey, object storage, workers, nginx) | One user on a laptop and hundreds of users on a server need different infrastructure, but the same domain code | `01`, `14` |
| A3 | LangGraph 1.2 for orchestration, LangChain 1.4 for model, prompt and tool interfaces. No LangChain legacy agents | Durable checkpoints, human-in-the-loop interrupts, parallel fan-out and streaming are built in | `06` |
| A4 | Laya is the fast "System 1" decision layer for routing, tool selection, guardrails and Tier 1 judges. The LLM is "System 2" and the fallback whenever Laya abstains | Laya answers typed questions in one forward pass (tens of ms) with calibrated confidence. Its base checkpoints are near chance on complex typed decisions until fine-tuned, so it starts in shadow mode and earns each decision with measured accuracy | `08`, `09` |
| A5 | On-prem open-weight models are the reference: vLLM on Linux GPU servers, Ollama on laptops. Cloud providers (Anthropic first) are optional per org and off by default | D2: customer data stays in the customer environment | `07` |
| A6 | Anthropic models are called through the official SDK (via `langchain-anthropic`), never through an OpenAI-compatible shim. All roles default to `claude-opus-5-5` with `effort` tuned per role. Cheaper models are a founder decision after evals | Correct feature support (structured outputs, prompt caching, refusal handling) | `07` |
| A7 | Valkey (BSD) instead of Redis 8 (AGPL, RSAL or SSPL) for cache, rate limits and pub/sub | Redistribution to customers without copyleft exposure. The `redis` Python client works with Valkey | `02` |
| A8 | Blob storage behind an interface: local filesystem by default, any S3-compatible store optionally (SeaweedFS in the reference multi-node stack) | MinIO's licence and distribution changes make it a poor default to ship | `02`, `12` |
| A9 | Job queue built on PostgreSQL (`FOR UPDATE SKIP LOCKED` with leases), not Celery | Cross-platform, no extra broker, survives worker crashes, and LangGraph checkpoints make re-leased jobs resume where they stopped | `06` |
| A10 | Preview rendering with LibreOffice (headless, through `unoserver` in server mode) and `pypdfium2` for PDF to PNG | Both run on all three OSes. `pypdfium2` is Apache/BSD, unlike PyMuPDF (AGPL) | `12` |
| A11 | Text metrics from bundled open fonts (metric-compatible with Arial, Georgia, Calibri, Cambria), not from `fc-match` | `fc-match` exists only on Linux. Bundled fonts give identical line breaks on every OS | `12` |
| A12 | Frontend: React 19 + Vite + TypeScript SPA, served as static files by nginx (server) or by FastAPI (lite) | No server-side rendering is needed. One static bundle works in both modes | `13` |
| A13 | Web research uses a pluggable search port: SearXNG (self-hosted) by default in server mode, a customer search API optionally, disabled in air-gapped installs | D7 with D2. Every fetched page passes an SSRF guard and a prompt-injection guard | `08`, `15` |
| A14 | Observability: structured JSON logs, OpenTelemetry traces, Prometheus metrics, plus a `llm_calls` table in PostgreSQL. Langfuse is an optional add-on | Works offline, no SaaS dependency | `16` |
| A15 | Auth: local accounts (argon2) plus optional OIDC SSO, short-lived JWT access tokens, rotating refresh cookies, hashed API keys | Fits small installs and enterprise SSO | `05`, `15` |
| A16 | Package and service names keep the existing `deckforge` Python package. New subpackages are added beside the existing ones | No churn in working code | `03` |

---

## 5. Decision requests

When a ticket cannot be completed without a choice this plan does not make, the agent creates `docs/decisions/DR-<next number>-<slug>.md` with:

```markdown
# DR-012: <one line question>
Ticket: T-x.y
Context: <what blocked, two to five lines>
Options:
1. <option> | cost | risk
2. <option> | cost | risk
Recommendation: <option number and one line why>
Status: open
```

It then moves to the next ticket that does not depend on the blocked one.

---

## 6. What already exists (do not rebuild)

| Area | Location | State |
|---|---|---|
| PPTX compiler, canvas, text metrics, lint and backlight repair | `deckforge/render/`, `deckforge/qa/` | Working, tests pass |
| Exhibits (waterfall, columns over line, profit pool, range benchmark, gap bars, site map, bubble and priority matrix, heat table, roadmap) | `deckforge/viz/exhibits/` | Working |
| Exhibit selector with familiarity weighting | `deckforge/viz/select.py` | Working |
| Style families MERIDIAN and VERDANT | `deckforge/viz/style.py` | Working |
| Plan schema, fact resolution, typed-number check, plan renderer, plan report | `deckforge/story/` | Working, planner stages are filled by hand today |
| Look-and-feel gate, storyline consistency check | `deckforge/qa/lookfeel.py`, `deckforge/qa/consistency.py` | Working |
| Asset sources (procedural, isometric illustration, icons, flags, maps, stock and text-to-image clients) | `deckforge/assets/` | Working, stock and T2I untested (network blocked) |
| Example brief end to end | `examples/auto_components_margin/` | Builds lint-clean in two families |

The build plan wraps these in services, replaces the hand-filled planner with LLM and Laya nodes, and adds persistence, API, UI, deployment and the learning loop.
