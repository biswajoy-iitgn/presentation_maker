# 04. Domain contracts and data model

Contracts in this document change only through a ticket (rule R3).

## 1. Existing contracts kept as they are

`deckforge/story/plan.py` already defines `Problem`, `Issue`, `Analysis`, `Point`, `Kpi`, `Slide`, `Plan` and `resolve()`. They stay. `deckforge/core/` re-exports them so new code imports from one place:

```python
# deckforge/core/__init__.py
from deckforge.story.plan import Analysis, Issue, Kpi, Plan, Point, Problem, Slide, resolve  # noqa: F401
```

`deckforge/viz/select.py` defines `MessageType`, `DataProfile`, `Candidate`, `choose()`. Kept.

## 2. New domain models (`deckforge/core/`)

All models are Pydantic v2, `model_config = ConfigDict(extra="forbid")` unless stated. Files and models:

### 2.1 `core/brief.py`

```python
class Audience(StrEnum):
    board = "board"; executive = "executive"; manager = "manager"; analyst = "analyst"; external = "external"

class DeckType(StrEnum):
    board_update = "board_update"; strategy = "strategy"; diagnostic = "diagnostic"; market_entry = "market_entry"
    due_diligence = "due_diligence"; transformation = "transformation"; investor = "investor"; other = "other"

class Brief(BaseModel):
    id: str
    project_id: str
    title: str                                   # short working title
    topic: str                                   # what the deck is about
    requirements: str                            # free text from the user
    audience: Audience = Audience.board
    deck_type: DeckType | None = None            # filled by intake if empty
    decision_asked: str | None = None            # what the audience must decide
    what_to_show: list[str] = []                 # user's explicit asks ("margin bridge", "peer benchmark")
    slide_count_min: int = 8
    slide_count_max: int = 20
    language: str = "en"
    style_family: str = "meridian"
    design_system_id: str | None = None          # customer template overrides style_family
    data_file_ids: list[str] = []
    reference_file_ids: list[str] = []
    allow_research: bool = False
    allow_dummy_data: bool = True
    clarifications: list["Clarification"] = []

class Clarification(BaseModel):
    question: str
    answer: str | None = None
    asked_by: Literal["laya", "llm"] = "llm"
```

### 2.2 `core/dataset.py`

```python
class SemanticType(StrEnum):
    time = "time"; category = "category"; geo = "geo"; measure = "measure"; ratio = "ratio"
    currency = "currency"; identifier = "identifier"; text = "text"; unknown = "unknown"

class ColumnProfile(BaseModel):
    name: str
    dtype: str                                   # pandas dtype string
    semantic: SemanticType
    unit: str | None = None                      # "INR crore", "%", "kt"
    n_missing: int
    n_unique: int
    sample: list[str]                            # up to 5 values as strings
    stats: dict[str, float] = {}                 # min, max, mean, sum for numeric columns

class TableProfile(BaseModel):
    id: str                                      # "<file_id>:<sheet>:<table index>"
    file_id: str
    sheet: str
    n_rows: int
    columns: list[ColumnProfile]
    role: Literal["time_series", "breakdown", "benchmark", "geo", "plan", "lookup", "other"] = "other"
    summary: str                                 # one paragraph, written by code from the profile (no LLM)

class DatasetRef(BaseModel):
    table_id: str
    blob_key: str                                # parquet snapshot of the cleaned table
    profile: TableProfile
```

### 2.3 `core/exhibit_data.py`

Every exhibit adapter in `deckforge/story/render.py` reads a dataset dict. T-4.2 formalises each input as a Pydantic model so that nodes produce validated data. Names follow the `EXHIBITS` registry keys.

```python
class WaterfallStep(BaseModel):
    label: str
    value: float | None = None
    kind: Literal["total", "delta"] = "delta"

class WaterfallData(BaseModel):
    exhibit: Literal["waterfall"] = "waterfall"
    steps: list[WaterfallStep]
    fmt_total: str
    fmt_delta: str
    higher_is_better: bool = True
    floor: float | None = None
    brackets: list[tuple[int, int, str]] = []
    benchmark: tuple[float, str] | None = None
    icons: dict[int, str] = {}

# Same pattern for: ColumnsOverLineData, ProfitPoolData, RangeBenchmarkData, GapBarsData, SiteMapData,
# BubbleMatrixData, PriorityMatrixData, HeatTableData, RoadmapData.
# Field names copy exactly what the adapters read today (examples/auto_components_margin/data.json is the reference).

ExhibitData = Annotated[WaterfallData | ColumnsOverLineData | ProfitPoolData | RangeBenchmarkData | GapBarsData |
                        SiteMapData | BubbleMatrixData | PriorityMatrixData | HeatTableData | RoadmapData,
                        Field(discriminator="exhibit")]
```

### 2.4 `core/facts.py`

```python
class Fact(BaseModel):
    id: str                                      # snake_case, used as {id} in text
    value: str                                   # formatted, ready to print ("₹113 cr", "72%")
    raw: float | None = None
    unit: str | None = None
    source: Literal["data", "dummy", "research", "brief"]
    provenance: str                              # "table t1: sum(EBITDA) where plant in (Pune, Chakan)" or citation id
    calc: str | None = None                      # calc recipe id that produced it
```

### 2.5 `core/research.py`

```python
class Citation(BaseModel):
    id: str
    url: str
    title: str
    publisher: str | None = None
    published: date | None = None
    accessed: datetime
    quote: str                                   # exact supporting text, at most 300 chars

class Finding(BaseModel):
    id: str
    analysis_id: str
    claim: str
    value: float | None = None
    unit: str | None = None
    citation_ids: list[str]
    confidence: float                            # 0 to 1, from the extraction judge
```

### 2.6 `core/design.py`

```python
class TypeScale(BaseModel):
    title: float = 26; exhibit_title: float = 13; unit: float = 11.5; label: float = 12; value: float = 12.5
    value_hero: float = 16; annotation: float = 11; commentary_head: float = 13.5; commentary: float = 13
    source: float = 9; kpi: float = 34

class Zones(BaseModel):                          # inches, matches deckforge/viz/frame.py constants
    x0: float = 0.5; x1: float = 12.83; title_y: float = 0.42; rule_y: float = 1.38; header_y: float = 1.52
    content_y: float = 1.95; content_y1: float = 6.72; footer_y: float = 6.92
    slide_w: float = 13.333; slide_h: float = 7.5

class DesignSystem(BaseModel):
    id: str
    name: str
    source: Literal["family", "template"]
    family: str | None = None                    # "meridian", "verdant" when source == family
    template_blob_key: str | None = None         # customer pptx/potx used as the base presentation
    colors: dict[str, str]                       # keys: ink, text2, muted, rule, track, panel, neutral, accent,
                                                 # accent_dark, accent_light, accent2, negative, positive, sidebar,
                                                 # sidebar_text, sidebar_number
    waves: list[str]                             # 3 ordinal colours
    heat: list[str]                              # 5-step sequential ramp, validated for contrast
    title_font: str
    body_font: str
    title_bold: bool
    header: Literal["rule", "band"]
    type: TypeScale
    zones: Zones
    layout_map: dict[str, str] = {}              # our archetype -> template layout name
    logo_blob_key: str | None = None
    logo_position: Literal["none", "top_right", "bottom_right", "bottom_left"] = "none"
    version: int = 1
```

`deckforge/viz/style.py` gains `Family.from_design_system(ds)` and `use(ds)` accepts a `DesignSystem` (T-8.3).

### 2.7 `core/quality.py`

```python
class Severity(StrEnum):
    blocker = "blocker"; major = "major"; minor = "minor"; info = "info"

class Defect(BaseModel):
    id: str
    code: str                                    # catalogue in 09, section 6.1 (e.g. "TITLE_NOT_ACTION", "LINT_OVERLAP")
    severity: Severity
    slide_id: str | None                         # None for deck-level defects
    tier: Literal[0, 1, 2, 3]                    # which evaluator tier found it
    evidence: str                                # short, human-readable
    element: str | None = None                   # shape name when known
    suggested_repair: str | None = None          # repair strategy id (09, section 7)
    standard_id: str | None = None               # design standard card id (28), e.g. "DS-FOCAL-01"
    owner: str | None = None                     # agent that owns the faulty artefact (27, section 4)
    bbox: tuple[float, float, float, float] | None = None   # slide-relative box from the inspector (25)
    fingerprint: str | None = None               # dedupe key across detectors and rounds (27, section 8.2)
    confidence: float = 1.0
    status: Literal["open", "repaired", "accepted", "wont_fix"] = "open"

class QAReport(BaseModel):
    run_id: str
    deck_version: int
    passed: bool                                 # no open blocker
    score: float                                 # 0 to 100, weighted (09, section 6.2)
    defects: list[Defect]
    lookfeel_markdown: str
    consistency: list[str]
```

`QAReport` is the persisted form stored in `deck_versions.qa`. The QA agents send the same findings to the orchestrator as `REPORT(QAVerdict)` (`27`, section 3), and the `qa_router` writes the `QAReport` after each round. The `Defect` fields above are the persisted shape of a `Finding` (`27`, section 8.2).

### 2.8 `core/decision.py`

```python
class Decision(BaseModel):
    decision_id: str                             # e.g. "D_TOOL_GROUP", catalogue in 09
    question_version: int
    engine: Literal["laya", "llm", "rule", "human"]
    answer: str | float | bool | None            # choice label, score, or probability
    probabilities: dict[str, float] = {}
    confidence: float                            # Laya answer_confidence or LLM self-rating mapped to 0..1
    abstained: bool = False
    fallback_used: str | None = None             # "llm", "default", None
    latency_ms: int
    log_id: str                                  # decision_log row id
```

### 2.9 `core/events.py`

```python
class EventType(StrEnum):
    run_status = "run.status"; stage_started = "stage.started"; stage_completed = "stage.completed"
    progress = "node.progress"; question_asked = "question.asked"; plan_ready = "plan.ready"
    slide_composed = "slide.composed"; slide_rendered = "slide.rendered"; qa_defect = "qa.defect"
    artifact_ready = "artifact.ready"; run_error = "run.error"; usage = "usage.update"

class RunEvent(BaseModel):
    seq: int                                     # monotonic per run, used as SSE id
    run_id: str
    type: EventType
    stage: str | None = None
    message: str                                 # short, user-facing
    data: dict[str, Any] = {}                    # type-specific payload, at most 16 KB
    at: datetime
```

Stages (string enum `Stage` in `core/run.py`): `intake`, `clarify`, `planning`, `plan_review`, `research`, `data`, `compose`, `render`, `qa`, `repair`, `finalize`.

Run statuses (`RunStatus`): `queued`, `running`, `waiting_input`, `succeeded`, `failed`, `cancelled`.

## 3. PostgreSQL schema (server) and SQLite (lite)

SQLAlchemy models in `deckforge/db/models.py` generate both. Types: `Uuid` (native uuid on PostgreSQL, CHAR on SQLite), `JSON().with_variant(JSONB(), "postgresql")`, `DateTime(timezone=True)`. Every table has `created_at timestamptz not null default now()`. Tenant tables have `org_id uuid not null` with an index. The DDL below is the PostgreSQL form, written by the first Alembic migration (T-1.2). Schema name `app`.

```sql
-- Tenancy and identity
CREATE TABLE app.organizations (
  id uuid PRIMARY KEY, name text NOT NULL, slug text UNIQUE NOT NULL,
  settings jsonb NOT NULL DEFAULT '{}',          -- default_family, research_enabled, retention_days, model_profile, allow_training, allow_exploration, fix_minor
  plan text NOT NULL DEFAULT 'standard', created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE app.users (
  id uuid PRIMARY KEY, email citext UNIQUE NOT NULL, name text NOT NULL,
  password_hash text,                            -- null for SSO-only users
  oidc_subject text UNIQUE, is_active boolean NOT NULL DEFAULT true, is_superadmin boolean NOT NULL DEFAULT false,
  last_login_at timestamptz, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE app.memberships (
  org_id uuid REFERENCES app.organizations ON DELETE CASCADE, user_id uuid REFERENCES app.users ON DELETE CASCADE,
  role text NOT NULL CHECK (role IN ('owner','admin','editor','viewer')),
  PRIMARY KEY (org_id, user_id));

CREATE TABLE app.refresh_tokens (
  id uuid PRIMARY KEY, user_id uuid NOT NULL REFERENCES app.users ON DELETE CASCADE,
  token_hash text NOT NULL UNIQUE, family_id uuid NOT NULL,   -- rotation family, reuse detection revokes family
  expires_at timestamptz NOT NULL, revoked_at timestamptz, user_agent text, ip inet,
  created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE app.api_keys (
  id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES app.organizations ON DELETE CASCADE,
  created_by uuid REFERENCES app.users, name text NOT NULL,
  prefix text NOT NULL,                          -- first 8 chars shown in UI, e.g. "df_live_ab12cd34"
  key_hash text NOT NULL UNIQUE,                 -- sha256 of the full key
  scopes text[] NOT NULL DEFAULT '{runs:write,runs:read,files:write}',
  last_used_at timestamptz, expires_at timestamptz, revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE app.provider_credentials (
  id uuid PRIMARY KEY, org_id uuid REFERENCES app.organizations ON DELETE CASCADE,   -- null = install-wide
  provider text NOT NULL,                        -- search, connector (SharePoint, Drive), smtp. No LLM provider keys: models run on-prem (19, D16)
  ciphertext bytea NOT NULL, nonce bytea NOT NULL,   -- AES-GCM with DF_SECRETS_KEY
  label text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

-- Work objects
CREATE TABLE app.projects (
  id uuid PRIMARY KEY, org_id uuid NOT NULL REFERENCES app.organizations ON DELETE CASCADE,
  name text NOT NULL, description text NOT NULL DEFAULT '',
  design_system_id uuid, created_by uuid REFERENCES app.users,
  archived_at timestamptz, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE app.files (
  id uuid PRIMARY KEY, org_id uuid NOT NULL, project_id uuid NOT NULL REFERENCES app.projects ON DELETE CASCADE,
  kind text NOT NULL CHECK (kind IN ('data','template','reference','image')),
  display_name text NOT NULL, content_type text NOT NULL, size_bytes bigint NOT NULL, sha256 text NOT NULL,
  blob_key text NOT NULL,
  status text NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded','processing','ready','rejected')),
  profile jsonb,                                 -- list[TableProfile] for data files
  error text, created_by uuid, created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX ON app.files (org_id, project_id);

CREATE TABLE app.design_systems (
  id uuid PRIMARY KEY, org_id uuid REFERENCES app.organizations ON DELETE CASCADE,   -- null = built-in family
  name text NOT NULL, source text NOT NULL CHECK (source IN ('family','template')),
  spec jsonb NOT NULL,                           -- DesignSystem
  version int NOT NULL DEFAULT 1, status text NOT NULL DEFAULT 'ready', created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE app.briefs (
  id uuid PRIMARY KEY, org_id uuid NOT NULL, project_id uuid NOT NULL REFERENCES app.projects ON DELETE CASCADE,
  spec jsonb NOT NULL,                           -- Brief
  created_by uuid, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE app.runs (
  id uuid PRIMARY KEY, org_id uuid NOT NULL, project_id uuid NOT NULL, brief_id uuid NOT NULL REFERENCES app.briefs,
  status text NOT NULL DEFAULT 'queued', stage text, graph_version text NOT NULL,
  options jsonb NOT NULL DEFAULT '{}',           -- auto_approve, ask_clarifications, family override, model profile
  pending_input jsonb,                           -- interrupt payload while waiting_input
  resume_payload jsonb,                          -- user response, consumed by the next run.resume job
  cancel_requested boolean NOT NULL DEFAULT false,
  idempotency_key text, error_code text, error_message text,
  kb_version text,                               -- knowledge base release used (28, section 5)
  model_versions jsonb NOT NULL DEFAULT '{}',    -- df-lm, adapters, laya, clm heads, laya-vision checkpoints used
  started_at timestamptz, finished_at timestamptz, created_by uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (org_id, idempotency_key));
CREATE INDEX ON app.runs (org_id, status);

CREATE TABLE app.run_events (
  run_id uuid NOT NULL REFERENCES app.runs ON DELETE CASCADE, seq int NOT NULL,
  type text NOT NULL, stage text, message text NOT NULL, data jsonb NOT NULL DEFAULT '{}',
  at timestamptz NOT NULL DEFAULT now(), PRIMARY KEY (run_id, seq));

CREATE TABLE app.deck_versions (
  id uuid PRIMARY KEY, org_id uuid NOT NULL, run_id uuid NOT NULL REFERENCES app.runs ON DELETE CASCADE,
  version int NOT NULL, plan jsonb NOT NULL,     -- resolved Plan
  exhibit_data jsonb NOT NULL, facts jsonb NOT NULL, design_system_id uuid, design_system_version int,
  renderer_version text NOT NULL, qa jsonb,      -- QAReport
  created_at timestamptz NOT NULL DEFAULT now(), UNIQUE (run_id, version));

CREATE TABLE app.slides (
  id uuid PRIMARY KEY, deck_version_id uuid NOT NULL REFERENCES app.deck_versions ON DELETE CASCADE,
  position int NOT NULL, slide_key text NOT NULL,   -- Slide.id from the plan
  spec_hash text NOT NULL, preview_blob_key text, UNIQUE (deck_version_id, position));

CREATE TABLE app.artifacts (
  id uuid PRIMARY KEY, org_id uuid NOT NULL, run_id uuid NOT NULL REFERENCES app.runs ON DELETE CASCADE,
  deck_version_id uuid REFERENCES app.deck_versions ON DELETE CASCADE,
  kind text NOT NULL CHECK (kind IN ('pptx','pdf','png','plan_report','qa_report','facts')),
  blob_key text NOT NULL, size_bytes bigint NOT NULL, sha256 text NOT NULL, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE app.defects (
  id uuid PRIMARY KEY, deck_version_id uuid NOT NULL REFERENCES app.deck_versions ON DELETE CASCADE,
  code text NOT NULL, severity text NOT NULL, slide_key text, tier smallint NOT NULL, evidence text NOT NULL,
  element text, suggested_repair text, confidence real NOT NULL, status text NOT NULL DEFAULT 'open');

CREATE TABLE app.feedback (
  id uuid PRIMARY KEY, org_id uuid NOT NULL, run_id uuid REFERENCES app.runs ON DELETE CASCADE,
  slide_key text, user_id uuid, rating smallint CHECK (rating BETWEEN -1 AND 1),
  comment text, action text,                     -- 'regenerate','edit_title','approve','reject'
  before jsonb, after jsonb, created_at timestamptz NOT NULL DEFAULT now());

-- Learning and accounting
CREATE TABLE app.decision_log (
  id uuid PRIMARY KEY, org_id uuid NOT NULL, run_id uuid, node text NOT NULL,
  decision_id text NOT NULL, question_version int NOT NULL, engine text NOT NULL,
  checkpoint text,                               -- Laya checkpoint id or LLM model id
  state_text text NOT NULL,                      -- exactly what the engine saw (redacted per org settings)
  answer jsonb NOT NULL, probabilities jsonb, confidence real, abstained boolean NOT NULL,
  fallback_used text, shadow jsonb,              -- answer of the shadow engine when shadow mode is on
  outcome_label jsonb,                           -- filled later: gold or teacher label, user correction
  latency_ms int NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX ON app.decision_log (decision_id, created_at);

CREATE TABLE app.llm_calls (
  id uuid PRIMARY KEY, org_id uuid NOT NULL, run_id uuid, node text, role text NOT NULL,
  pool text NOT NULL, model text NOT NULL, adapter text, agent_id text, prompt_id text NOT NULL, prompt_version int NOT NULL,
  prompt_hash text NOT NULL, input_tokens int, output_tokens int, cache_read_tokens int, cache_write_tokens int,
  cost_micro_usd bigint, latency_ms int,         -- cost is internal, from config/pricing.yaml (07, section 7)
  cache_hit boolean NOT NULL DEFAULT false,
  status text NOT NULL,                          -- ok, schema_error, pool_error, refusal, timeout, budget_exhausted
  error text, created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX ON app.llm_calls (org_id, created_at);

CREATE TABLE app.tool_calls (
  id uuid PRIMARY KEY, org_id uuid NOT NULL, run_id uuid, node text, tool text NOT NULL, tool_version int NOT NULL,
  args_hash text NOT NULL, status text NOT NULL, latency_ms int, cache_hit boolean NOT NULL DEFAULT false,
  result_blob_key text, error text, created_at timestamptz NOT NULL DEFAULT now());

CREATE TABLE app.usage_ledger (
  id bigserial PRIMARY KEY, org_id uuid NOT NULL, user_id uuid, run_id uuid,
  metric text NOT NULL,                          -- runs, llm_input_tokens, llm_output_tokens, renders, storage_bytes
  quantity bigint NOT NULL, period date NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX ON app.usage_ledger (org_id, period, metric);

CREATE TABLE app.audit_log (
  id bigserial PRIMARY KEY, org_id uuid, actor_user_id uuid, actor_api_key_id uuid,
  action text NOT NULL, target_type text, target_id text, ip inet, details jsonb NOT NULL DEFAULT '{}',
  at timestamptz NOT NULL DEFAULT now());

CREATE TABLE app.model_registry (
  id uuid PRIMARY KEY, kind text NOT NULL CHECK (kind IN ('laya','llm_profile')),
  name text NOT NULL, version text NOT NULL, uri text NOT NULL,   -- HF id, local path, or config ref
  metrics jsonb NOT NULL DEFAULT '{}', status text NOT NULL CHECK (status IN ('candidate','shadow','active','retired')),
  created_at timestamptz NOT NULL DEFAULT now(), UNIQUE (kind, name, version));

CREATE TABLE app.decision_policies (
  decision_id text NOT NULL, question_version int NOT NULL, checkpoint text NOT NULL,
  mode text NOT NULL CHECK (mode IN ('llm_only','shadow','laya_first','laya_only')),
  thresholds jsonb NOT NULL,                     -- {"<option count bucket>": min_confidence}
  metrics jsonb NOT NULL DEFAULT '{}', updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (decision_id, question_version, checkpoint));

-- Queue
CREATE TABLE app.jobs (
  id uuid PRIMARY KEY, kind text NOT NULL, org_id uuid NOT NULL, payload jsonb NOT NULL,
  priority smallint NOT NULL DEFAULT 100,        -- lower runs first
  status text NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','leased','done','failed','dead')),
  attempts int NOT NULL DEFAULT 0, max_attempts int NOT NULL DEFAULT 3,
  run_after timestamptz NOT NULL DEFAULT now(), leased_by text, lease_expires_at timestamptz,
  last_error text, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
CREATE INDEX jobs_ready ON app.jobs (priority, run_after) WHERE status = 'queued';
CREATE INDEX jobs_leased ON app.jobs (lease_expires_at) WHERE status = 'leased';

-- Knowledge base (vectors). Namespaces and card schema are defined in 28. PostgreSQL only. Lite mode keeps vectors in kb_items.vector_json and searches with numpy.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE app.kb_items (
  id uuid PRIMARY KEY, org_id uuid,              -- null = shared knowledge (framework library, exemplars)
  namespace text NOT NULL,                       -- frameworks, recipes, viz, exhibits, design, storyline, archetypes, industries, exemplars, tool_cards, org_terms, icons
  key text NOT NULL, text text NOT NULL, meta jsonb NOT NULL DEFAULT '{}',
  embedding vector(384),                         -- bge-small dimension
  embed_model text NOT NULL, UNIQUE (namespace, org_id, key));
CREATE INDEX ON app.kb_items USING hnsw (embedding vector_cosine_ops);
```

LangGraph tables: created by `AsyncPostgresSaver.setup()` and `AsyncPostgresStore.setup()` in schema `lg` (connection string with `options=-csearch_path=lg`). The migration T-1.2 creates the schema. Lite mode: `AsyncSqliteSaver` in a separate file `{DF_DATA_DIR}/checkpoints.db`.

Tables added by later phases (agent traces, agent messages, revisions, comments, variants, shares, daily usage), monthly partitioning of the telemetry streams and the index plan are in `23` (sections 3 and 4) and `27` (section 9, `agent_messages`).

Optional Row-Level Security (server, T-12.5): enable RLS on tenant tables with policy `org_id = current_setting('app.org_id')::uuid`. The repository layer sets `SET LOCAL app.org_id` per transaction. Repositories also filter by `org_id` explicitly, so RLS is defence in depth.

## 4. Blob layout

Keys are POSIX paths. No user-supplied text ever appears in a key.

| Content | Key |
|---|---|
| Uploaded file | `orgs/{org_id}/projects/{project_id}/files/{file_id}/original` |
| Cleaned table snapshot | `orgs/{org_id}/projects/{project_id}/files/{file_id}/tables/{table_index}.parquet` |
| Template base presentation | `orgs/{org_id}/design/{design_system_id}/v{version}/template.pptx` |
| Deck | `orgs/{org_id}/runs/{run_id}/v{version}/deck.pptx` |
| PDF | `orgs/{org_id}/runs/{run_id}/v{version}/deck.pdf` |
| Slide preview | `orgs/{org_id}/runs/{run_id}/v{version}/preview/{position:02d}.png` |
| Reports | `orgs/{org_id}/runs/{run_id}/v{version}/{plan_report.md, qa_report.json, facts.json}` |
| Large tool result | `orgs/{org_id}/runs/{run_id}/tools/{tool_call_id}.json` |
| Research page text | `orgs/{org_id}/runs/{run_id}/research/{sha256}.txt` |
| Shared asset cache | `assets/{sha256[:2]}/{sha256}.{ext}` with sidecar `{sha256}.json` (licence, source, prompt) |

## 5. Retention and deletion

| Data | Default retention | Setting |
|---|---|---|
| Runs, decks, artifacts | 365 days | `organizations.settings.retention_days` |
| Run events | 90 days | same setting, capped at 90 |
| decision_log `state_text` | 180 days, then redacted to hash | `settings.decision_log_retention_days` |
| llm_calls | 400 days (billing) | fixed |
| Uploaded files | Until project deleted | |

Deleting a project deletes its blobs through a `project.purge` job. Deleting an org runs `org.purge` (all rows and blobs). Both are audited.
