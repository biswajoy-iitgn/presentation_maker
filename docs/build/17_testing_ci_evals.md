# 17. Testing, CI and evals

## 1. Test pyramid

| Level | Folder | Needs | Runs in | Target count by P10 |
|---|---|---|---|---|
| Unit | `tests/unit/` | nothing (fakes only), no network | every commit, all three OSes | 600+ |
| Integration | `tests/integration/` | PostgreSQL + Valkey (testcontainers), renderer optional | every PR, Linux | 120+ |
| Golden decks | `tests/golden/` | LibreOffice for PNG comparison (Linux) | every PR touching render, viz, story | 6 briefs x 2 families |
| End to end | `tests/e2e/` | built SPA, lite server with fakes, Playwright Chromium | nightly and before release | 10 flows |
| Evals | `evals/` | real models (staging) | nightly on the eval host, on demand | 30 golden briefs |
| Load | `tests/load/` | server stack | before release | 3 scenarios |
| Security | `tests/unit/security`, `tests/integration/test_tenancy.py` etc. | as above | every PR | `15` section 9 |

## 2. Fakes (all in `deckforge/testing/`, importable by tests and by `DF_TEST_PROFILE=fake`)

| Fake | Behaviour |
|---|---|
| `FakeLLM` | Implements `LLMProvider`. Returns canned outputs keyed by `prompt_id` from `tests/fixtures/llm/<prompt_id>/*.json` (picked by a hash of the rendered input, else `default.json`). Records every call for assertions. Can be scripted to raise `ProviderError` on the n-th call |
| `FakeLaya` | Implements the raw backend. Scripted answers per decision id: fixed answer, probability map, or `abstain`. Default: abstain everything (so tests exercise fallbacks unless they script answers) |
| `FakeBlobStore`, `MemoryCache`, `MemoryEventBus`, `FakeJobQueue` | In-memory versions of the ports |
| `FakeRenderer` | Returns a 1-page blank PDF per slide and grey PNGs |
| `FakeSearch` | Returns fixture search hits and page texts from `tests/fixtures/research/` |
| `fake_runtime()` | Builds a `Runtime[GraphContext]` with all fakes for node tests |

## 3. What each package must test

| Package | Must cover |
|---|---|
| `core` | Model validation edge cases, JSON round trips, discriminated union of exhibit data |
| `ingest` | Profiling of the example xlsx, semantic type rules, template theme extraction on two fixture templates (one corporate-like, one minimal), malformed inputs |
| `llm` | Structured output repair path, backend rules (vLLM: `extra_body` with `chat_template_kwargs.enable_thinking`, adapter name as model, hermes tool parser. Ollama and llama.cpp: JSON schema format), `ModelPool` routing and budget reservation, usage recording, cache key stability, error mapping |
| `prompting` | Every prompt renders with fixtures, version lock, token budgets |
| `context` | Budget shrinking order, overflow error, state builders under 380 tokens on long inputs |
| `decisions` | Policy modes, rotation averaging maths, thresholds per bucket, fallback paths, cache, decision log rows, circuit breaker |
| `tools` | Each tool: happy, invalid args, timeout, cache key. Executor offload. Selector middleware with scripted FakeLaya |
| `graphs` | Every route function, every node with fake runtime, full graph on the example brief (FakeLLM), interrupt and resume, crash and resume, cancellation |
| `jobs` | Lease, heartbeat, reaper, org cap, retries and dead-lettering (integration on PostgreSQL), lite polling |
| `api` | Each endpoint: success, validation error, auth errors, permission, tenancy, idempotency, SSE replay with Last-Event-ID |
| `render`, `viz`, `qa` | Existing tests plus metrics from bundled fonts give the same widths on all OSes (fixed expectations) |

## 4. Golden decks

- Inputs: `evals/briefs/<name>/` with `brief.json`, data files and a frozen `plan.json` and `exhibit_data.json` (so the render test does not depend on LLMs).
- `uv run poe golden` renders each in MERIDIAN and VERDANT and compares:
  1. Normalised XML snapshot (shape name, type, rounded geometry, text, fill colour) with `tests/golden/<name>/<family>.xml.json`. Runs on all OSes.
  2. PNG comparison (Linux CI only, LibreOffice in the CI image): mean absolute difference at most 2.0 and no 32 x 32 tile above 12.0.
  3. Lint clean, look-and-feel pass, storyline consistent.
- Updating references: `uv run poe golden --update` writes new references and a before and after contact sheet into the PR artifacts.

## 5. CI (GitHub Actions)

`.github/workflows/ci.yml` (replaces the current single job):

| Job | Runs on | Steps |
|---|---|---|
| `lint-type` | ubuntu-latest | `uv sync --extra lite --extra dev`, `poe check` minus tests |
| `unit` | matrix: ubuntu-latest, macos-latest, windows-latest | `uv sync --extra lite --extra dev`, `pytest tests/unit -n auto` |
| `frontend` | ubuntu-latest | `npm ci`, `npm run lint`, `npm run test`, `npm run build`, check `openapi.json` is up to date (`poe openapi --check`) |
| `integration` | ubuntu-latest | `uv sync --extra server --extra dev`, `pytest tests/integration` (testcontainers starts PostgreSQL 17 with pgvector and Valkey 8) |
| `golden` | ubuntu-latest container with LibreOffice and bundled fonts | `poe golden` |
| `lite-smoke` | matrix: three OSes | install the built wheel into a fresh venv, `deckforge init --non-interactive`, `deckforge serve` in background, hit `/readyz`, run one fake-profile run through the API, stop |
| `images` | ubuntu-latest, on main and tags | build multi-arch images, Trivy scan, push on tags |
| `audit` | ubuntu-latest, nightly | `poe audit`, SBOM with syft |
| `e2e` | ubuntu-latest, nightly | Playwright against lite server with fakes |

Caching: `astral-sh/setup-uv` with cache, npm cache, Docker layer cache.

## 6. Eval harness

`deckforge/evals/` with CLI `deckforge eval`:

| Suite | Input | Metrics | Pass bar |
|---|---|---|---|
| `briefs` | 30 golden briefs (varied industries, deck types, with and without data, 5 with templates) | run success, time, tokens, QA score, look-and-feel pass, storyline validator first-try pass, Tier 2 judge pass rates, Tier 3 visual scores | success 100%, QA pass at least 90%, median QA score at least 85 |
| `roles` | same briefs with candidate model profiles | per-role quality and cost (`07` section 8) | relative |
| `prompts` | per-prompt datasets (inputs and reference outputs or rubric) | schema validity, judge score | no regression above 2 points |
| `laya` | `training/data/*/test.jsonl` and S5 gold | `laya-evals run` metrics + coverage at threshold | promotion gates (`09` section 9.2) |
| `pairwise` | generated decks vs previous release on the same briefs | VLM pairwise preference on 20 slide pairs per brief, plus founder blind review of 20 pairs per release | new release preferred or tied in at least 60% |

Reports land in `evals/reports/<date>/` (markdown and JSON) and the latest summary is attached to the release notes.

## 7. Load tests

`tests/load/locustfile.py`:

| Scenario | Users | Behaviour | Pass bar |
|---|---|---|---|
| Browse | 200 | login, list projects, open run pages, poll events | p95 under 300 ms, 0 errors |
| Generate | 20 concurrent runs (fake LLM with realistic latency distribution 2 to 20 s per call) | full run with auto-approve | all succeed, queue wait p95 under 60 s, API p95 under 300 ms during the runs |
| Spike | 50 run creations in 10 s | burst | 429s for over-limit users, no 5xx, queue drains |

Run against the reference node with real models once in T-12.3 to replace the capacity estimates in `01` section 8 with measurements.
