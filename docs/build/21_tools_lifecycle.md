# 21. Tools: how they are made, trained and refined

`08` defines the tool contract, registry, executor and Laya tool selection. This document covers the full lifecycle of a tool: design, build, make it usable by the model, train the model and the router to use it, measure it, and improve it.

## 1. Tool categories

| Category | What is inside | Examples | Trained? |
|---|---|---|---|
| Deterministic | Plain code | `query_table`, `growth_rates`, `bridge_decompose`, `fit_text`, `compile_pptx`, `lint_deck` | No. Tested and versioned |
| Learned | A model inside the tool | `classify_column` (Laya head), `select_exhibit` (rule scores plus a learned tie-break and corpus priors), `icon_search` (embeddings plus Laya pick), `rank_images` (relevance and aesthetic scorer), `guard_text` (Laya guard) | Yes, the inner model (section 5.4) |
| External | Calls outside the install | `web_search`, `fetch_url`, `image_search` | No. Wrapped with sandbox recordings for training |
| Layout tools | Deterministic geometry edits that return a `LayoutPatch` | `relayout`, `nudge_labels`, `fix_contrast`, `snap_grid` | No. Their use by `repair_specialist` is trained (`20`, section 10) |

There is no "agent as a tool" category. Work by another agent is always a new `TASK` from the orchestrator (`27`), so ownership, budgets and traces stay intact (`20`, section 4).

Around every tool, two things are trained: **DeckForge-LM's ability to call it** (when, with which arguments) and **Laya's router** (which group of tools a step needs).

## 2. Making a tool

### 2.1 Design rules

| Rule | Why |
|---|---|
| One job per tool. If the description needs "and", consider two tools | The model chooses better among clear, single-purpose tools |
| Name is `verb_object` in snake_case (`query_table`, `fetch_url`) | Names are part of what the model reads |
| Arguments use enums and defaults wherever the space is closed (`agg: Literal["sum", "mean", ...]`) | Constrained decoding and fewer invalid calls |
| At most 6 top-level arguments. Group the rest into a typed object | Long signatures raise argument errors |
| Output is small and structured. Large data goes to a blob with a summary and a handle | Keeps contexts short |
| Errors teach: `invalid_args` returns which field, why, and a valid example | The model fixes its call on the next step |
| Idempotent and side-effect class declared honestly | Retries and caching depend on it |
| Every tool supports **sandbox mode** (section 4) | Training and evals must not hit the live web or customer systems |
| Description at most 300 characters: what it does, when to use it, when not to | Laya and the model read it |

### 2.2 Build checklist (extends `08` section 8)

1. Input and output Pydantic models with field descriptions (they become the JSON schema the model sees).
2. `ToolSpec` with name, version, group, description, side effect, timeouts, retries, cache TTL, roles, features.
3. Implementation `async def tool_fn(args, ctx) -> Output` with sandbox branch when it touches anything external.
4. Tool card in `deckforge/tools/cards.yaml`: three example tasks where it is the right tool, two where it is not (with the right alternative).
5. Unit tests: happy path, invalid args message, timeout, cache key stability, sandbox output determinism.
6. Benchmark tasks: at least 20 tasks in `evals/tools/<group>/` (section 6.2).
7. Training hooks: the tool appears in at least one task generator (section 5.1).
8. Register in the agents' cards that may use it.

### 2.3 Template

```python
# deckforge/tools/impl/calc.py
class GrowthRatesInput(BaseModel):
    table_id: str = Field(description="Id of a stored table from the data profile")
    value_column: str = Field(description="Numeric column to measure growth on")
    period_column: str = Field(description="Time column (years, quarters, months)")
    kind: Literal["cagr", "yoy", "total"] = Field(default="cagr", description="Growth measure")

class GrowthRatesOutput(BaseModel):
    kind: str
    start_period: str
    end_period: str
    value_pct: float
    series: list[tuple[str, float]] = Field(description="Per-period growth, at most 40 points")

GROWTH_RATES = ToolSpec(
    name="growth_rates", version=1, group="calc",
    description="Compute CAGR, year-on-year or total growth of one numeric column over time from a stored table. "
                "Use for growth statements in titles. Not for shares or margins (use share_of_total).",
    input_model=GrowthRatesInput, output_model=GrowthRatesOutput, side_effect=SideEffect.read,
    timeout_s=10, cache_ttl_s=86400)

@tool(GROWTH_RATES)
async def growth_rates(args: GrowthRatesInput, ctx: ToolContext) -> GrowthRatesOutput:
    df = await ctx.tables.load(args.table_id)            # validated columns, raises ToolArgError with a teaching message
    ...
```

## 3. Making tools visible to the model

`deckforge/tools/schema_export.py` turns each `ToolSpec` into the function-calling JSON schema used in three places, so the model sees the same definition in training and in production:

1. **Runtime**: LangChain `StructuredTool` bound to the chat model for ReAct agents.
2. **Training data**: the `tools` list in chat-format examples (`19`, section 4.7), rendered by the base model's chat template.
3. **RL environments**: the methods of the environment class (section 5.2) carry the same names, type hints and Google-style docstrings, because TRL builds tool schemas from them.

A unit test asserts the three representations produce the same names, argument names and types. Changing a tool's schema bumps its `version`, and the training data builder regenerates examples for the new version.

## 4. Sandbox mode

`ToolContext.mode` is `live` or `sandbox`.

| Tool kind | Sandbox behaviour |
|---|---|
| Deterministic | Same as live (no change needed) |
| Data tools | Operate on fixture tables from C2 briefs (`19`, section 4.4) |
| `web_search`, `fetch_url` | Served from a frozen **web snapshot**: `training/web_snapshot/` holds search results and page texts collected once (with licences recorded) for the research tasks. Queries are matched by normalised text, misses return an empty result |
| `image_search`, `generate_image` | Return fixture images and metadata |
| Layout tools | Run against the real renderer geometry in unit tests (they are pure functions of the slide spec) |
| Write tools | Write into an in-memory blob store |

Sandbox mode is what makes reinforcement learning on tool use safe, fast and reproducible.

## 5. Training around tools

### 5.1 Tool-use SFT data

Generated by `training/generators/tool_tasks.py`:

1. **Task generation**: for each tool group, templates produce tasks from C2 briefs ("Find the CAGR of revenue for FY22 to FY25", "Which plants are above the peer median on conversion cost", "Find a cited 2025 market size for Indian auto components"). Each task stores the expected outcome check (numbers from code truth, or a required citation).
2. **Trajectory generation**: the open teacher (or DeckForge-LM itself in later cycles) solves each task with the tools in sandbox mode through the same ReAct agent code. 4 attempts per task.
3. **Acceptance**: a trajectory is kept when the outcome check passes, no call returned `invalid_args` more than once, and the number of calls is within 1.5x the minimum observed for that task.
4. **Negative examples**: tasks answerable from context, where the accepted trajectory calls no tool. About 15% of tool examples, so the model learns when not to call.
5. **Argument repair examples**: trajectories where a first call returned `invalid_args` and the next call fixed it. These teach recovery.
6. Output: chat-format examples with `tools`, `tool_calls` and `tool` messages, mixed into Stage 1 SFT (`19`, section 5.1, Researcher and Data Analyst shares).

### 5.2 Tool-use reinforcement learning

Multi-turn GRPO with TRL's `environment_factory`:

```python
# training/rl/envs.py
class ResearchEnv:
    """Methods are the tools the model may call. TRL builds tool schemas from names, type hints and docstrings."""

    def __init__(self):
        self.ctx = sandbox_tool_context()           # ToolExecutor in sandbox mode, fixture tables, web snapshot
        self.task = None
        self.calls = 0

    def reset(self, **task) -> str | None:
        self.task, self.calls = task, 0
        return None                                  # or extra instructions appended to the user message

    def web_search(self, query: str, recency_days: int = 730) -> str:
        """Search the web.

        Args:
            query: What to search for, in plain words.
            recency_days: Only results newer than this many days.

        Returns:
            JSON list of results with title, url, snippet and published date.
        """
        self.calls += 1
        return run_tool(self.ctx, "web_search", {"query": query, "recency_days": recency_days})

    # fetch_url, extract_facts, cite, query_table ... same pattern

    def get_reward(self) -> float:
        return research_reward(self.task, self.ctx.findings, self.calls)   # 19, section 5.3 researcher row
```

Config: `GRPOConfig(num_generations=8, max_tool_calling_iterations=8, use_vllm=True, ...)` with `GRPOTrainer(model=..., environment_factory=ResearchEnv, train_dataset=research_tasks, peft_config=lora)`. The same pattern is used for `RepairEnv` (layout tools on one slide, scored by inspector L1 to L3 on the re-rendered slide) and `DataEnv` (data and calc tools).

### 5.3 Router training (Laya)

`D_TOOL_NEED` and `D_TOOL_GROUP` heads are trained from:
- outcome labels written by `ToolOutcomeLabeler` (`08`, section 5.5) in production and in sandbox runs,
- the accepted trajectories of section 5.1 (every step gives one labelled example: the state before the call, the group of the tool that was called, or `answer` when none was).

Training, calibration and promotion follow `09` section 8.

### 5.4 Learned tools

| Tool | Inner model | Training data | Metric | Gate |
|---|---|---|---|---|
| `classify_column` | Laya `D_COLUMN_ROLE` | C2 synthetic tables with known types, user corrections | accuracy on accepted items | `09` section 9.2 routing gate |
| `select_exhibit` | Rule scores (`viz/select.py`) + corpus priors table + Laya `D_EXHIBIT_TIEBREAK` | Corpus inversion counts of (message type, data shape, audience) to exhibit, look-and-feel and Tier 3 outcomes | agreement with corpus choice in top 2, `J_CHART_FIT` | top-2 agreement at least 0.85 |
| `icon_search` | fastembed embeddings over the Lucide index + Laya `D_ICON_PICK` | Tier 3 icon-fit verdicts, corpus icon usage | top-1 acceptance by Tier 3 | at least 0.80 |
| `rank_images` | relevance (CLIP-style text-image similarity) and aesthetic scorer from TRD 7.9, on GPU | corpus imagery as positives, rejected candidates as negatives | pairwise accuracy | at least 0.75 |
| `guard_text` | Laya `D_GUARD_INJECTION` | public injection datasets with permissive licences, synthetic injections | recall at false-positive rate | `09` section 9.2 guard gate |

`corpus_priors.json` (generated by `training/sources/corpus.py`) holds counts per (message type, data shape bucket, audience) to exhibit id. `select_exhibit` adds `0.05 x log-odds` of the prior to the rule score, clipped to plus or minus 0.1, so data can shift close calls without overriding hard rejections (dual axes, radar, pies of many parts).

## 6. Measuring tools

### 6.1 Contract tests

Every tool: unit tests (section 2.2 step 5) plus the schema parity test (section 3).

### 6.2 Tool benchmark

`evals/tools/<group>/tasks.jsonl`, each task: user request, available tools, the expected tool or set of acceptable tools, argument constraints (for example `table_id` must equal X, `kind` must be `cagr`), outcome check.

| Metric | Definition |
|---|---|
| Selection accuracy | first tool call is an acceptable tool |
| Abstention correctness | no tool called when the task is answerable from context |
| Argument validity | first call passes input validation |
| Argument correctness | arguments meet the task's constraints |
| Task success | outcome check passes within the step limit |
| Calls per success | mean tool calls for successful tasks |
| Latency | p50 and p95 per task |

`deckforge eval --suite tools` runs the benchmark with the current DeckForge-LM, Laya router and tool descriptions. Results are compared per tool with the previous release.

### 6.3 Production telemetry (from `tool_calls` and `decision_log`)

Per tool per week: calls, `invalid_args` rate, error rate, timeout rate, p95 latency, cache hit rate, "shortlisted but not used" rate (Laya put it in the shortlist and the model did not call it), "needed but missing" count (a later step called a tool that the router had excluded), confusion pairs (tool A called, then immediately tool B with the same intent).

## 7. Refining tools

### 7.1 Triggers

| Signal | Threshold | Action |
|---|---|---|
| `invalid_args` rate | above 5% | Simplify arguments (enums, defaults), improve the error message, add argument repair examples to training |
| Error or timeout rate | above 2% | Fix the implementation or dependency, adjust timeouts, add circuit breaker tuning |
| Confusion pair rate | above 10% between two tools | Rewrite both descriptions to state when each applies, or merge the tools |
| Shortlisted but not used | above 40% | Description over-claims, or the router's group is too broad: refine the description or move the tool to another group |
| Needed but missing | above 3% of steps | Retrain the router, or put the tool in `always_include` for that agent |
| Never called in 30 days | 0 calls | Review for removal |
| Benchmark drop | any tool more than 2 points | Block release until fixed |

### 7.2 Description optimisation loop (automatic, T-7.11)

1. Collect failure examples for the tool from telemetry and the benchmark (wrong tool chosen, tool missed, bad arguments).
2. The open teacher writes 8 candidate descriptions (at most 300 characters each) given the current description, the tool schema, the card examples and the failures.
3. Run the tool benchmark for the group once per candidate (DeckForge-LM plus Laya router, sandbox mode).
4. Accept the best candidate only if selection accuracy improves by at least 2 points and no other tool in the group drops by more than 1 point.
5. Record the change in `deckforge/tools/CHANGELOG.md` with before and after metrics. Bump the tool `version`. Regenerate affected training examples in the next cycle.

### 7.3 Versioning and deprecation

- Schema or behaviour change: bump `version`. Old versions stay callable for one release so in-flight runs and old trajectories remain valid.
- Deprecation: mark `deprecated_after` in the spec, remove from agent cards, keep the implementation until the date, then delete with its benchmark tasks moved to an archive.
- Training data carries the tool version. Builders drop examples for removed versions.

### 7.4 Ownership and review

Each tool lists an owner ticket and appears on the "Tools" dashboard (calls, error rates, benchmark trend). A monthly tool review (automated report in `evals/reports/tools/<month>.md`) lists triggered refinements and their outcomes.
