# 16. Observability

## 1. Logs

- `structlog` configured in `deckforge/observability/logging.py`. JSON lines in server mode (`DF_LOG_JSON=true`), coloured console in lite mode.
- Context bound per request and per job: `request_id`, `org_id`, `user_id`, `run_id`, `job_id`, `node`, `worker_id`.
- Levels: DEBUG (local only), INFO (state changes: run started, stage completed, job leased), WARNING (fallbacks, retries, Laya abstentions above normal), ERROR (failed nodes, failed jobs), CRITICAL (startup failures).
- Never logged at INFO or above: prompts, model outputs, uploaded content, tokens and keys (redaction processor, `15` section 2).
- nginx access logs in JSON with the same `req_id`.

## 2. Traces

OpenTelemetry SDK, OTLP exporter to `DF_OTEL_ENDPOINT` (collector in the observability profile, forwarding to the customer's backend such as Tempo, Jaeger or an APM).

| Span source | How |
|---|---|
| HTTP requests | `opentelemetry-instrumentation-fastapi` |
| Outbound HTTP (Laya, renderer, search, fetch) | `opentelemetry-instrumentation-httpx` |
| Database | `opentelemetry-instrumentation-sqlalchemy` |
| Jobs | manual span `job.<kind>` around each handler, linked to the API request that enqueued it through `traceparent` stored in the job payload |
| Graph nodes | LangChain callback handler `OtelGraphCallback` creating spans per node and per LLM call with attributes: `gen_ai.system`, `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `deckforge.prompt_id`, `deckforge.role` (OpenTelemetry GenAI semantic conventions). No prompt text in span attributes |
| Laya decisions | span `decision.<id>` with `answer`, `confidence`, `abstained`, `engine` |

Optional Langfuse: when `DF_LANGFUSE_*` is set, the Langfuse LangChain callback is added to graph runs (self-hosted Langfuse only, never their cloud for customer data).

## 3. Metrics

Prometheus client, exposed on port 9100 (`/metrics`) by api, worker, renderer. Names:

| Metric | Type | Labels |
|---|---|---|
| `http_request_duration_seconds` | histogram | method, route, status |
| `deckforge_runs_total` | counter | status |
| `deckforge_run_duration_seconds` | histogram | outcome |
| `deckforge_stage_duration_seconds` | histogram | stage |
| `deckforge_jobs_ready` | gauge | kind |
| `deckforge_job_wait_seconds` | histogram | kind |
| `deckforge_llm_requests_total` | counter | role, pool, adapter, status |
| `deckforge_llm_tokens_total` | counter | role, model, kind (input, output, cache_read, cache_write) |
| `deckforge_llm_latency_seconds` | histogram | role, model |
| `deckforge_llm_cost_micro_usd_total` | counter | role, model (internal cost from `config/pricing.yaml`) |
| `deckforge_pool_budget_wait_seconds` | histogram | pool, priority |
| `deckforge_pool_degradation_step` | gauge | pool (0 = normal, steps from `22` section 6) |
| `deckforge_agent_tasks_total` | counter | agent, kind, outcome (result, reject, need, escalate, cancelled) |
| `deckforge_qa_findings_routed_total` | counter | owner, strategy, outcome (fixed, persisting, regression) |
| `deckforge_clm_rank_latency_seconds` | histogram | ranker |
| `deckforge_decisions_total` | counter | decision_id, engine, outcome (accepted, abstained, fallback) |
| `deckforge_decision_latency_seconds` | histogram | decision_id, engine |
| `deckforge_tool_calls_total` | counter | tool, status |
| `deckforge_cache_requests_total` | counter | layer, result |
| `deckforge_render_seconds` | histogram | step (compile, pdf, png) |
| `deckforge_qa_defects_total` | counter | code, severity, tier |
| `deckforge_qa_score` | histogram | |

Organisation ids are not metric labels (cardinality). Per-org usage comes from `usage_ledger`.

## 4. Dashboards (provisioned in `deploy/observability/grafana/`)

1. **Service health**: request rate, error rate, p95 latency per route, queue depth, worker slot usage, renderer busy ratio.
2. **Runs**: runs per hour by outcome, stage durations, p50 and p95 deck time, repair rounds, QA score distribution, top defect codes.
3. **Model pools**: tokens and cost per role and adapter, latency, error and refusal rates, prefix cache hit rate, KV usage, running and waiting requests per replica, adapter swaps, budget waits, degradation step, GPU memory and utilisation (DCGM exporter, `22` section 10).
6. **Agents**: tasks per agent and outcome, reject and need rates, repair findings by owner and strategy, fixed vs persisting vs regression (`20` section 12, `27`).
4. **Laya**: decisions per second by id, abstention and fallback rates, latency, audit-sample agreement, answer distribution drift.
5. **Cache**: hit rate per layer, Valkey memory and evictions.

## 5. Alerts (Prometheus rules in `deploy/observability/alerts.yml`)

| Alert | Condition | Severity |
|---|---|---|
| ApiErrorRate | 5xx above 2% for 5 min | page |
| QueueBacklog | `deckforge_jobs_ready{kind="run.execute"}` above 2 x worker slots for 10 min | warn |
| RunFailureRate | failed runs above 10% over 1 h | page |
| ModelPoolErrors | model pool error rate above 5% for 5 min | page |
| ModelPoolSaturated | degradation step 2 or higher for 10 min, or vLLM waiting requests above 0 for 5 min | warn |
| GpuMemoryHigh | DCGM GPU memory above 95% for 5 min | warn |
| ClmUnavailable | `rank()` fallbacks above 50% for 5 min | warn |
| LayaUnavailable | Laya decisions with `outcome=fallback` and reason unavailable above 50% for 5 min | warn |
| LayaDrift | weekly label share shift above 15 points for a decision | info |
| RendererSaturated | renderer busy above 90% for 10 min | warn |
| DiskSpace | blob or database volume above 80% | warn |
| CertExpiry | TLS certificate expires within 14 days | warn |

## 6. Run-level trace for users

Separate from operations telemetry: every run stores its `run_events`, `decision_log`, `llm_calls` (metadata) and the plan report. The UI's Reasoning tab shows the product-level trace (what was decided, by which engine, with what confidence). This is the customer-facing audit trail.
