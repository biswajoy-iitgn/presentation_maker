# 07. LLM layer

## 1. Responsibilities

`deckforge/llm/` gives every node a ready `BaseChatModel` for a role, enforces structured output, records usage and cost, applies caches and limits, and hides provider differences. Nodes never construct model clients themselves.

## 2. Roles

| Role | Used by | Output | Typical input / output tokens | Concurrency limit per worker |
|---|---|---|---|---|
| `planner` | frame_problem, issue_tree, pick_frameworks, storyline, revise_* | Pydantic models | 8k to 16k / 1k to 3k | 4 |
| `writer` | write_copy, repair (copy) | `SlideCopy` | 3k to 5k / 400 to 800 | 8 |
| `extractor` | normalise_brief, clarify questions, research extraction, template naming | Pydantic models | 2k to 8k / 200 to 1k | 8 |
| `judge` | Tier 2 judges, teacher labelling | `JudgeVerdict` | 2k to 4k / 150 to 300 | 8 |
| `vision_judge` | Tier 3 judges on rendered PNGs | `VisualVerdict` | 1 image + 1k / 300 | 2 |
| `embed` | kb search, icon search, tool cards | vectors | short texts | n/a (in-process) |

## 3. Providers and adapters

| `kind` | Adapter | Client | When |
|---|---|---|---|
| `openai_compatible` | `OpenAICompatAdapter` | `langchain_openai.ChatOpenAI(base_url=..., api_key=..., model=...)` | vLLM, Ollama (`/v1`), LiteLLM gateway |
| `anthropic` | `AnthropicAdapter` | `langchain_anthropic.ChatAnthropic` (official `anthropic` SDK underneath) | Cloud profile, opt-in per org. Optionally pointed at the LiteLLM Anthropic pass-through route via `anthropic_api_url` for central key management |
| `fake` | `FakeLLM` | ours | Tests |

### 3.1 `config/models.yaml`

```yaml
providers:
  vllm:
    kind: openai_compatible
    base_url: ${DF_LLM_GATEWAY_URL:-http://litellm:4000/v1}
    api_key_env: DF_LLM_GATEWAY_KEY
  ollama:
    kind: openai_compatible
    base_url: http://localhost:11434/v1
    api_key: ollama
  anthropic:
    kind: anthropic
    api_key_env: ANTHROPIC_API_KEY

profiles:
  onprem:                                   # default for server mode
    planner:      {provider: vllm, model: planner-main, max_tokens: 4000, temperature: 0.2, timeout_s: 180, context_window: 65536}
    writer:       {provider: vllm, model: planner-main, max_tokens: 1200, temperature: 0.4, timeout_s: 90,  context_window: 65536}
    extractor:    {provider: vllm, model: planner-main, max_tokens: 1500, temperature: 0.0, timeout_s: 60,  context_window: 65536}
    judge:        {provider: vllm, model: planner-main, max_tokens: 600,  temperature: 0.0, timeout_s: 60,  context_window: 65536}
    vision_judge: {provider: vllm, model: vision-main,  max_tokens: 600,  temperature: 0.0, timeout_s: 90,  context_window: 32768}
  laptop:                                   # default for lite mode
    planner:      {provider: ollama, model: "<chosen local model>", max_tokens: 4000, temperature: 0.2, timeout_s: 600, context_window: 32768}
    writer:       {provider: ollama, model: "<chosen local model>", max_tokens: 1200, temperature: 0.4, timeout_s: 300, context_window: 32768}
    extractor:    {provider: ollama, model: "<chosen local model>", max_tokens: 1500, temperature: 0.0, timeout_s: 300, context_window: 32768}
    judge:        {provider: ollama, model: "<chosen local model>", max_tokens: 600,  temperature: 0.0, timeout_s: 300, context_window: 32768}
    vision_judge: {provider: ollama, model: "<chosen local vision model>", max_tokens: 600, temperature: 0.0, timeout_s: 300, context_window: 16384}
  cloud_claude:                             # opt-in: DF_ALLOW_CLOUD_LLM=true and org setting allow_cloud_llm
    planner:      {provider: anthropic, model: claude-opus-5-5, max_tokens: 16000, effort: high,   timeout_s: 300, context_window: 1000000}
    writer:       {provider: anthropic, model: claude-opus-5-5, max_tokens: 4000,  effort: medium, timeout_s: 120, context_window: 1000000}
    extractor:    {provider: anthropic, model: claude-opus-5-5, max_tokens: 4000,  effort: low,    timeout_s: 120, context_window: 1000000}
    judge:        {provider: anthropic, model: claude-opus-5-5, max_tokens: 2000,  effort: low,    timeout_s: 120, context_window: 1000000}
    vision_judge: {provider: anthropic, model: claude-opus-5-5, max_tokens: 2000,  effort: medium, timeout_s: 120, context_window: 1000000}

embed: {provider: fastembed, model: BAAI/bge-small-en-v1.5, dim: 384}
default_profile: {lite: laptop, server: onprem}
```

`planner-main` and `vision-main` are served-model aliases configured in vLLM (`--served-model-name`) or in LiteLLM's `model_list`, so swapping the underlying model needs no app change.

### 3.2 Provider-specific rules (must be implemented in the adapters)

| Provider | Rule |
|---|---|
| vLLM | Structured output via `response_format={"type": "json_schema", ...}` (`with_structured_output(Model, method="json_schema", strict=True)`). Server started with `--enable-prefix-caching`. Tool calling needs `--enable-auto-tool-choice` and the model's `--tool-call-parser` (only the research agent uses tools) |
| Ollama | `with_structured_output(Model, method="json_schema")` maps to Ollama's `format` JSON schema through the OpenAI-compatible endpoint. If a model ignores it, the adapter falls back to `method="json_mode"` plus validation |
| LiteLLM | Pass-through of the above. Each org gets a virtual key with budget and rpm/tpm limits (`14`, section 2.3) |
| Anthropic (`claude-opus-5-5`) | Use `with_structured_output(Model, method="json_schema")`. Never the default `function_calling` method: it forces `tool_choice`, which `claude-opus-5-5` rejects with HTTP 400. Do not send `temperature`, `top_p` or `top_k` (rejected on this model). Do not send a `thinking` config (thinking is always on, adaptive). Control depth with `output_config={"effort": "low" \| "medium" \| "high" \| "xhigh" \| "max"}`. The default effort on this model is `medium`, so set it explicitly per role. Handle `stop_reason == "refusal"` (map to `ProviderError(code="refusal", retryable=False)`). Enable the server-side fallback beta (`betas=["server-side-fallback-2026-07-01"]` with request field `fallbacks: "default"`) and verify in T-3.4 that `langchain-anthropic` forwards the field (`model_kwargs`). If it does not, `AnthropicAdapter` calls the `anthropic` SDK directly for that request. No assistant prefill (rejected) |
| Anthropic prompt caching | Prefix order is tools, then system, then messages. At most 4 `cache_control` breakpoints. Default TTL 5 minutes, `{"type": "ephemeral", "ttl": "1h"}` for the per-run stable prefix. Prefixes below the model's minimum cacheable length (512 to 4096 tokens depending on model) silently do not cache. Verify with `usage.cache_read_input_tokens` in `llm_calls` |

## 4. Public interface

```python
# deckforge/llm/registry.py
class ModelRegistry:
    def __init__(self, config: ModelsConfig, settings: Settings, credentials: CredentialStore): ...
    def chat_model(self, role: Role, *, org: OrgSettings) -> BaseChatModel: ...      # cached per (profile, role)
    def spec(self, role: Role, *, org: OrgSettings) -> RoleSpec: ...                  # max_tokens, context_window...

# deckforge/llm/call.py
async def structured(
    ctx: LLMCallContext,              # org_id, run_id, node, role, cache policy, event sink
    prompt: RenderedPrompt,           # from prompting (section 6): messages + prompt_id + version + hash
    schema: type[T],                  # Pydantic model
    *,
    max_repairs: int = 1,
) -> T: ...

async def text(ctx: LLMCallContext, prompt: RenderedPrompt) -> str: ...
async def vision(ctx: LLMCallContext, prompt: RenderedPrompt, images: list[bytes], schema: type[T]) -> T: ...
```

`structured()` algorithm:

1. Check the quota and the per-role semaphore.
2. Build the LLM cache key (`11`, layer 3). On hit, record an `llm_calls` row with `cache_hit=true` and return.
3. `model = registry.chat_model(role).with_structured_output(schema, method=<per provider>, include_raw=True)`.
4. `await model.ainvoke(prompt.messages, config={"callbacks": [UsageCallback(ctx)], "run_name": prompt.prompt_id})` with `asyncio.timeout(spec.timeout_s)`.
5. If `parsed` is `None` or validation fails: append one user message `"Your previous output failed validation: <errors>. Return only valid JSON for the schema."` and retry once (`max_repairs`). Still failing: raise `ValidationFailed` (the node's `RetryPolicy` does not retry this error type, the node's fallback logic decides).
6. Record usage (tokens, cache tokens, latency, cost from `config/pricing.yaml`), write the cache, return the model.

Errors are mapped to `ProviderError(provider, code, retryable)`: timeouts, 429 and 5xx are retryable. 400, auth errors, refusals and context overflow are not.

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
- Cost table `config/pricing.yaml` maps `provider/model` to micro-dollars per million tokens for input, output, cache read, cache write. On-prem models have a configurable internal cost (GPU-hour amortised) so dashboards compare like for like.
- A run-level budget (`options.max_cost_micro_usd`, default unlimited on-prem) stops new LLM calls with `QuotaExceeded` when exceeded. The run finishes with what it has and reports it.

## 8. Choosing models (procedure, T-11.6)

1. Candidate models per role are served in a staging vLLM.
2. `uv run poe eval --suite roles` runs the golden briefs (`evals/briefs/`) through each candidate profile with the rest of the pipeline fixed.
3. Metrics: schema validity rate, judge pass rate (Tier 1 + Tier 2), storyline validator pass rate on first try, look-and-feel pass, p50 and p95 latency, tokens per deck.
4. Pick the smallest model per role that stays within 2 points of the best on quality metrics. Record the decision in `docs/decisions/` and update `config/models.yaml`.
