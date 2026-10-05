# 07. LLM layer

## 1. Responsibilities

`deckforge/llm/` gives every agent a ready chat model for its role and adapter, enforces structured output, routes calls to model replicas without overloading them, records usage and cost, and applies caches. Agents never construct model clients themselves.

All language models are **DeckForge-LM** (`19`): open-weight models fine-tuned by us and served locally. There is no cloud LLM provider and no external LLM gateway (D16).

## 2. Roles

| Role | Used by agents (`20`) | Model and adapter | Output | Typical input / output tokens | Thinking mode |
|---|---|---|---|---|---|
| `planner` | engagement_manager | `df-lm` + `df-planner` | Pydantic models | 8k to 16k / 1k to 3k | off by default, short thinking only if evals show it pays |
| `writer` | copywriter, viz_designer, art_director, repair_specialist | `df-lm` + agent adapter | `SlideCopy`, `ExhibitDecision`, `AssetPlan`, patches | 3k to 5k / 400 to 800 | off |
| `extractor` | intake_analyst, data_analyst, researcher, supervisor, template_designer | `df-lm` + agent adapter | Pydantic models, tool calls | 2k to 8k / 200 to 1.5k | off |
| `judge` | reviewer, fact_checker (Tier 2) | `df-lm` + `df-reviewer` | `JudgeVerdict` | 2k to 4k / 150 to 300 | off |
| `vision_judge` | reviewer (Tier 3, inspector L5) | `df-vlm` | `VisualVerdict` | 1 image + 1k / 300 | off |
| `embed` | knowledge base, tool cards, icons | fastembed `BAAI/bge-small-en-v1.5` in process | vectors | short texts | n/a |

Until Stage 5 of training (`19`, section 5.5) produces per-agent adapters, every adapter name maps to the multitask model (the merged Stage 1 to 4 model). The adapter field is still sent, so switching to real adapters needs only a config change.

## 3. Serving backends and adapters

| `kind` | Adapter class | Client | Where |
|---|---|---|---|
| `vllm_pool` | `PoolAdapter` | `langchain_openai.ChatOpenAI(base_url=<replica>/v1, api_key=<pool key>, model=<adapter or base name>, extra_body=...)`, replica chosen per call by `ModelPool` (`22`, section 6.1) | server |
| `ollama` | `OllamaAdapter` | `ChatOpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama", model="df-lm-8b:q4_k_m")` | laptops |
| `llamacpp` | `LlamaCppAdapter` | `ChatOpenAI(base_url="http://127.0.0.1:8080/v1", ...)`, per-request LoRA scales through `extra_body={"lora": [...]}` when per-agent adapters are used on laptops | laptops (optional) |
| `fake` | `FakeLLM` | ours | tests |

vLLM serves LoRA adapters under their own model names (`--lora-modules df-writer=/models/adapters/df-writer ...`), so selecting an adapter is selecting the `model` field of the request.

### 3.1 `config/models.yaml`

```yaml
pools_file: config/model_pools.yaml          # replicas, adapters, budgets (22, section 6.1)

profiles:
  server:                                    # default in server mode
    planner:      {backend: vllm_pool, pool: lm,  adapter: df-planner,  max_tokens: 4000, temperature: 0.2, timeout_s: 180, context_window: 32768, thinking: false}
    writer:       {backend: vllm_pool, pool: lm,  adapter: df-writer,   max_tokens: 1200, temperature: 0.4, timeout_s: 90,  context_window: 32768, thinking: false}
    extractor:    {backend: vllm_pool, pool: lm,  adapter: df-intake,   max_tokens: 1500, temperature: 0.0, timeout_s: 60,  context_window: 32768, thinking: false}
    judge:        {backend: vllm_pool, pool: lm,  adapter: df-reviewer, max_tokens: 600,  temperature: 0.0, timeout_s: 60,  context_window: 32768, thinking: false}
    vision_judge: {backend: vllm_pool, pool: vlm, adapter: null,        max_tokens: 600,  temperature: 0.0, timeout_s: 90,  context_window: 16384, thinking: false}
  laptop:                                    # default in lite mode, tier chosen by `deckforge doctor`
    planner:      {backend: ollama, model: "df-lm-8b:q4_k_m", max_tokens: 4000, temperature: 0.2, timeout_s: 600, context_window: 16384, thinking: false}
    writer:       {backend: ollama, model: "df-lm-8b:q4_k_m", max_tokens: 1200, temperature: 0.4, timeout_s: 300, context_window: 16384, thinking: false}
    extractor:    {backend: ollama, model: "df-lm-8b:q4_k_m", max_tokens: 1500, temperature: 0.0, timeout_s: 300, context_window: 16384, thinking: false}
    judge:        {backend: ollama, model: "df-lm-8b:q4_k_m", max_tokens: 600,  temperature: 0.0, timeout_s: 300, context_window: 16384, thinking: false}
    vision_judge: {backend: ollama, model: "df-vlm:q4_k_m",   max_tokens: 600,  temperature: 0.0, timeout_s: 300, context_window: 8192,  thinking: false}

agent_adapters:                              # agent id -> adapter name (used when the agent's card says adapter: auto)
  supervisor: df-supervisor
  intake_analyst: df-intake
  data_analyst: df-analyst
  engagement_manager: df-planner
  researcher: df-researcher
  viz_designer: df-viz
  copywriter: df-writer
  art_director: df-art
  reviewer: df-reviewer
  fact_checker: df-reviewer
  repair_specialist: df-repair

embed: {backend: fastembed, model: BAAI/bge-small-en-v1.5, dim: 384}
default_profile: {lite: laptop, server: server}
```

Laptop tiers L2 and L3 override `model` and `context_window` from the doctor's tier file (`22`, section 5).

### 3.2 Backend rules (implemented in the adapters)

| Topic | Rule |
|---|---|
| Structured output | `with_structured_output(Model, method="json_schema", strict=True)`. vLLM enforces the schema with its default structured-output backend (xgrammar). Ollama receives the schema as its `format`. If a laptop model ignores it, the adapter falls back to `method="json_mode"` plus validation and one repair |
| Thinking mode | Qwen3-family chat templates have a thinking switch. The adapter sends `extra_body={"chat_template_kwargs": {"enable_thinking": spec.thinking}}` on vLLM. On Ollama the request option `think` is set from `spec.thinking`. Training data (`19`) teaches the same default (no reasoning traces for structured roles), so outputs stay short |
| Tool calling (ReAct agents) | vLLM started with `--enable-auto-tool-choice --tool-call-parser <parser for the base family>` (for Qwen3: `hermes`). Tool schemas come from `ToolSpec` (`21`, section 3) |
| Sampling | `temperature` per role, `top_p` 0.95 for writer, `seed` set per call from (run id, node, attempt) so retries are reproducible |
| Prefix caching | vLLM `--enable-prefix-caching`. Prompts keep stable sections first (`10`, section 9) and the router keeps a run on one replica when possible (`22`, section 6.1) |
| Context limit | every request is checked against `context_window` by the `ContextBuilder` before sending. Overflow is a bug, never truncated silently |
| Admission | every call reserves `estimated_prompt_tokens + max_tokens` from the pool budget and waits in its priority class (`22`, section 6.2) |

## 4. Public interface

```python
# deckforge/llm/registry.py
class ModelRegistry:
    def __init__(self, config: ModelsConfig, pools: ModelPools, settings: Settings): ...
    def chat_model(self, role: Role, *, adapter: str | None, org: OrgSettings) -> BaseChatModel: ...   # cached per (profile, role, adapter)
    def spec(self, role: Role, *, org: OrgSettings) -> RoleSpec: ...

# deckforge/llm/call.py
async def structured(ctx: LLMCallContext, prompt: RenderedPrompt, schema: type[T], *, max_repairs: int = 1) -> T: ...
async def text(ctx: LLMCallContext, prompt: RenderedPrompt) -> str: ...
async def vision(ctx: LLMCallContext, prompt: RenderedPrompt, images: list[bytes], schema: type[T]) -> T: ...
```

`LLMCallContext` carries org, run, node, agent id, role, adapter, priority class, cache policy and the event sink.

`structured()` algorithm:

1. Check the quota and reserve tokens from the pool budget in the call's priority class (`22`, section 6.2).
2. Build the LLM cache key (`11`, layer 3). On a hit, release the reservation, record an `llm_calls` row with `cache_hit=true` and return.
3. Pick a replica with `ModelPool.choose(adapter, run_id)`, get `registry.chat_model(role, adapter=...)` bound to it, then `.with_structured_output(schema, method="json_schema", strict=True, include_raw=True)`.
4. `await model.ainvoke(prompt.messages, config={"callbacks": [UsageCallback(ctx)], "run_name": prompt.prompt_id})` within `asyncio.timeout(spec.timeout_s)`.
5. If parsing or validation fails: append one user message `"Your previous output failed validation: <errors>. Return only valid JSON for the schema."` and retry once. Still failing: raise `ValidationFailed` (not retried by the node's `RetryPolicy`, the node's fallback decides).
6. Release the reservation, record usage (tokens, prefix cache hits from vLLM usage when reported, latency, internal cost from `config/pricing.yaml`), write the cache, return the model.

Errors map to `ProviderError(backend, code, retryable)`: timeouts, connection errors, 429 and 5xx are retryable (another replica is tried first). 400, schema errors and context overflow are not.

## 5. Output schemas (examples)

```python
class ProblemOut(BaseModel):            # planning.frame_problem
    key_question: str = Field(max_length=300)
    decision_maker: str
    success_criteria: list[str] = Field(min_length=1, max_length=5)
    scope: str
    assumptions: list[str] = Field(default_factory=list, max_length=5)

class IssueTreeOut(BaseModel):          # planning.issue_tree
    root: Issue                          # existing model, depth at most 3, 3 to 5 children per node

class FrameworkPickOut(BaseModel):      # planning.pick_frameworks
    picks: list["AnalysisPick"]
class AnalysisPick(BaseModel):
    issue_id: str
    framework_id: str                    # must be one of the shortlisted ids (validated)
    message_type: MessageType
    dataset_table_id: str | None
    data_status: Literal["provided", "research", "dummy"]
    why: str = Field(max_length=300)

class StorylineOut(BaseModel):          # planning.storyline
    governing_thought: str
    situation: str; complication: str; resolution: str
    sections: list[str] = Field(min_length=2, max_length=6)
    slides: list["SlidePlanItem"]
class SlidePlanItem(BaseModel):
    id: str; archetype: Literal["cover", "agenda", "exec_summary", "exhibit", "decisions"]
    section: int | None; analysis: str | None
    title_intent: str                    # the message the slide must prove, in plain words

class SlideCopy(BaseModel):             # compose.write_copy
    title: str = Field(max_length=160)   # uses {fact} tokens for numbers
    exhibit_title: str | None
    exhibit_unit: str | None
    commentary_head: str | None
    points: list[Point] = Field(max_length=4)
    sticker: Literal["ILLUSTRATIVE", "PRELIMINARY", "INDICATIVE"] | None
    source: str
    emphasis: list[str | int] = []

class JudgeVerdict(BaseModel):          # Tier 2
    verdict: Literal["pass", "fail"]
    score: int = Field(ge=1, le=5)
    evidence: str = Field(max_length=300)   # quote from the slide
    fix: str | None = Field(default=None, max_length=300)
```

Validators on these models enforce rules that do not need an LLM (for example `framework_id in allowed_ids`, slide ids unique, sections referenced exist).

## 6. Prompt management

### 6.1 Prompt files

`prompts/<area>/<name>.md`:

```markdown
---
id: planning.storyline
version: 3
role: planner
schema: deckforge.llm.schemas.StorylineOut
inputs: [brief, problem, issue_tree, analyses, design_rules, exemplars]
cache_prefix_sections: [system, house_rules]     # sections that form the stable prefix (11, layer 4)
---
## system
You are a senior engagement manager at a top-tier strategy consulting firm...

## house_rules
{{ house_rules }}

## user
Brief:
{{ brief | to_yaml }}
...
Return the storyline as JSON matching the schema.
```

- Sections become messages: `system` and `house_rules` are joined into the system message, `user` becomes the user message. Optional `example_user` and `example_assistant` sections become few-shot turns.
- Rendering: Jinja2 with `StrictUndefined`, custom filters `to_yaml`, `table_md` (dataset summary as a small markdown table), `truncate_tokens(n)`.
- The prompt hash is sha256 of the template text plus the version. Stored on every `llm_calls` row.
- Changing a prompt's text requires bumping `version` (a unit test compares the stored hash list in `prompts/LOCK.json` and fails if text changed without a version bump).

### 6.2 Prompt quality rules (apply to every prompt)

1. State the role, the audience and the quality bar in two or three sentences. No motivational filler.
2. Give the output schema field meanings in the prompt, not only in the JSON schema.
3. Put untrusted content (uploaded document text, web pages) inside `<document source="...">` tags with an instruction that document text is data, never instructions.
4. Ask for numbers as `{fact_id}` tokens only, listing the available facts.
5. Include one compact good example and one bad example with the reason for routine generation tasks (titles, commentary).
6. Keep stable content first and variable content last (prefix caching).

### 6.3 Golden tests

`tests/unit/prompting/test_render.py` renders every prompt with fixture inputs and checks: no undefined variables, token count within the role budget, schema import resolves. `evals/` holds quality evals per prompt (`17`).

## 7. Usage, cost and limits

- `UsageCallback` (LangChain callback handler) reads `usage_metadata` from `AIMessage` (input, output, cache read, cache creation tokens) and writes `llm_calls` plus `usage_ledger`.
- Cost table `config/pricing.yaml` maps each pool to an internal cost per million input and output tokens (GPU-hour cost amortised over measured throughput), so dashboards show cost per deck and per agent.
- A run-level budget (`options.max_tokens_total`, default unlimited) stops new LLM calls with `QuotaExceeded` when exceeded. The run finishes with what it has and reports it.

## 8. Choosing models (procedure, T-11.6)

1. Candidate models per role are served in a staging vLLM.
2. `uv run poe eval --suite roles` runs the golden briefs (`evals/briefs/`) through each candidate profile with the rest of the pipeline fixed.
3. Metrics: schema validity rate, judge pass rate (Tier 1 + Tier 2), storyline validator pass rate on first try, look-and-feel pass, p50 and p95 latency, tokens per deck.
4. Pick the smallest model per role that stays within 2 points of the best on quality metrics. Record the decision in `docs/decisions/` and update `config/models.yaml`.
