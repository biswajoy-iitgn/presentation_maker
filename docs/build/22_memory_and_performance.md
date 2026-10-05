# 22. Memory management and performance

Goal: run DeckForge-LM, the vision model, Laya, embeddings, the renderer and the app together without out-of-memory failures, at high speed, on a GPU server and on laptops.

Model sizes and architecture numbers below come from the published Qwen3 configs (`num_hidden_layers`, `num_key_value_heads`, `head_dim`). T-14.1 recomputes every number from the actual `config.json` of the chosen base and the measured vLLM startup logs, and updates this document.

## 1. What uses memory

| Consumer | Where | Size driver |
|---|---|---|
| LLM weights | GPU (server), RAM or unified memory (laptop) | parameters x bytes per parameter |
| KV cache | same | tokens in flight x KV bytes per token |
| LoRA adapter slots | GPU | `max_loras` x adapter size at `max_lora_rank` |
| Activations, CUDA graphs, sampler buffers | GPU | batch size, `max_num_batched_tokens` |
| Vision model | GPU | weights + KV for image tokens |
| Laya | GPU or CPU | 421M parameters (about 0.85 GB bf16, 1.7 GB fp32, 0.45 GB ONNX int8) |
| Embeddings (fastembed bge-small) | CPU | about 0.15 GB |
| Workers | CPU RAM | Python runtime, graph state, pandas tables, PPTX compile peaks |
| LibreOffice instances | CPU RAM | 250 to 500 MB each |
| PostgreSQL, Valkey | CPU RAM | configured (`shared_buffers`, `maxmemory`) |
| Training jobs | GPU | weights, optimiser state, activations, rollout engine |

## 2. Formulas

```text
weights_bytes      = parameters x bytes_per_parameter         (bf16 2, fp8 1, int4 about 0.55 incl. scales)
kv_bytes_per_token = 2 x num_layers x num_kv_heads x head_dim x bytes_per_element   (bf16 2, fp8 1, q8_0 about 1.06)
kv_capacity_tokens = (gpu_mem x gpu_memory_utilization - weights - lora_slots - overhead) / kv_bytes_per_token_per_gpu
concurrent_seqs    = kv_capacity_tokens / average_tokens_per_active_sequence
lora_adapter_bytes = rank x sum over layers and target matrices of (in_features + out_features) x bytes
lora_slots_bytes   = max_loras x lora_adapter_bytes(at max_lora_rank)
```

With tensor parallelism `TP`, weights, KV heads and LoRA slots are split across the `TP` GPUs, so per-GPU numbers divide by `TP`. `overhead` (activations, CUDA graphs, sampler) is planned at 4 GB per GPU and corrected from vLLM logs.

## 3. Reference numbers (Qwen3 dense family)

| Model | Layers | KV heads | Head dim | Params | bf16 weights | FP8 weights | 4-bit weights | KV per token bf16 | KV per token FP8 | LoRA r16 (all linear) |
|---|---|---|---|---|---|---|---|---|---|---|
| 8B | 36 | 8 | 128 | 8.2B | 16.4 GB | about 8.8 GB | about 5.0 GB (GGUF Q4_K_M) | 144 KiB | 72 KiB | about 87 MB |
| 14B | 40 | 8 | 128 | 14.8B | 29.6 GB | about 15.5 GB | about 9.5 GB (AWQ) | 160 KiB | 80 KiB | about 135 MB |
| 32B | 64 | 8 | 128 | 32.8B | 65.6 GB | about 34 GB | about 19 GB (AWQ) | 256 KiB | 128 KiB | about 268 MB |

Worked example, 32B: `2 x 64 x 8 x 128 x 1 byte = 131,072 bytes = 128 KiB` per token with FP8 KV. A 10,000-token active sequence holds 1.25 GiB of KV.

LoRA example, 32B rank 16 over `q, k, v, o, gate, up, down`: per layer `(5120+8192) + (5120+1024) x 2 + (8192+5120) + (5120+25600) x 3 = 131,072`, times 64 layers times rank 16 = 134M parameters = about 268 MB in bf16.

## 4. Server reference: 4 x 80 GB

### 4.1 Daytime allocation

| GPU | Service | Model | Key flags | Memory plan per GPU | Capacity (estimate) |
|---|---|---|---|---|---|
| 0 + 1 | `vllm-lm-a` | `df-lm-32b` merged multitask, FP8, plus agent adapters | `--tensor-parallel-size 2 --gpu-memory-utilization 0.90 --kv-cache-dtype fp8 --max-model-len 32768 --max-num-seqs 64 --max-num-batched-tokens 16384 --enable-prefix-caching --enable-lora --max-loras 8 --max-lora-rank 16 --max-cpu-loras 16` | 72 GB budget: weights 17, LoRA slots 1.1, overhead 4, KV about 50 | KV about 760k tokens across the pair, about 64 concurrent sequences of 10k tokens |
| 2 | `vllm-lm-b` | same model, second replica | `--tensor-parallel-size 1 --gpu-memory-utilization 0.90 --kv-cache-dtype fp8 --max-model-len 32768 --max-num-seqs 24 --enable-prefix-caching --enable-lora --max-loras 8 --max-lora-rank 16 --enable-sleep-mode` | 72 GB budget: weights 34, LoRA slots 2.1, overhead 4, KV about 32 | KV about 250k tokens, about 24 concurrent sequences |
| 3 | `vllm-vlm` | `df-vlm` FP8 | `--gpu-memory-utilization 0.45 --kv-cache-dtype fp8 --max-model-len 16384 --max-num-seqs 16 --limit-mm-per-prompt '{"image": 1}'` | 36 GB budget: weights about 9, overhead 3, KV about 24 | ample for 1 image per request |
| 3 | `clm-encoder` | Qwen3-8B base, bf16, pooling runner | `--runner pooling --max-model-len 2048 --gpu-memory-utilization 0.25` | 20 GB budget: weights 16.4, overhead 2.5, activations about 1 | about 400 candidate texts per second at 300 tokens (estimate, measure in T-14.4) |
| 3 | `clm` | CLM heads (about 20M parameters each) | `--device cuda --action-cache 512MiB` | about 1.5 GB (CUDA context, heads, cache) | ranking 100 candidates in under 200 ms once embeddings are cached |
| 3 | `laya` | `df-laya` + base | `LAYA_DEVICE=cuda`, `LAYA_MAX_LOADED=2`, `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True` | about 4 GB | thousands of decisions per second batched |
| 3 | `laya-vision` | `df-laya-vision` (our weights, `25` sections 4 and 8) | `LV_DEVICE=cuda` | about 6 GB | about 50 slide images per second batched (estimate) |
| 3 | headroom | | | about 12 GB free | absorbs allocator fragmentation and Laya batch peaks |

The encoder stays bf16 because CLM heads were trained on bf16 base embeddings. Quantising it shifts the embedding space and the heads would need re-training (`24` section 5). Text-to-image is not co-located on GPU 3 any more. If an org enables image generation, it runs on GPU 2 inside the night window (pre-generated icon and illustration sets) or on a fifth GPU.

Rules:
- The sum of `gpu-memory-utilization` of all vLLM instances on a GPU plus the measured peak of non-vLLM processes (Laya, Laya-Vision, CLM heads) must stay below 0.95. GPU 3 today: 0.45 + 0.25 + 11.5 / 80 = 0.84.
- Start order on GPU 3: `laya`, `laya-vision`, `clm-encoder`, `clm`, then `vllm-vlm` (each vLLM instance checks free memory at startup, so the small non-vLLM processes go first). The compose `depends_on` chain encodes this order.
- `--max-model-len 32768` bounds the KV a single request can take. No role needs more (`10`, section 3).
- `--max-num-seqs` is set below the computed concurrency so vLLM never preempts under normal load. The admission controller (section 6) keeps it there.

### 4.2 Night or low-load allocation (training and data generation)

| GPU | Day | Night |
|---|---|---|
| 0 + 1 | `vllm-lm-a` | `vllm-lm-a` (still serving) |
| 2 | `vllm-lm-b` | asleep (`POST /sleep?level=1` offloads weights to CPU RAM, needs about 34 GB free RAM), GPU used for a training job or teacher batch generation |
| 3 | VLM, CLM, Laya, Laya-Vision | same services, plus small head jobs (Laya heads, CLM heads) in the headroom, batch size capped so peak stays under 10 GB |

Waking: the GPU scheduler (`deckforge gpu-schedule`, T-14.5) checkpoints the training job, stops it, and calls `POST /wake_up` when the run queue backs up or at the start of the working day. vLLM exposes `/sleep`, `/wake_up` and `/is_sleeping` only when `VLLM_SERVER_DEV_MODE=1`, so that replica runs on the internal network only. If a customer does not allow dev mode, the scheduler stops and starts the container instead (slower, a few minutes to load).

Who trains what: DeckForge releases of `df-lm` are trained on vendor GPUs. Customer servers only run small local jobs when `allow_training` is on (Laya heads, small agent adapters), inside the night window.

### 4.3 Other server sizes

| Hardware | LM | VLM and Laya | Notes |
|---|---|---|---|
| 2 x 80 GB | `df-lm-32b` FP8 TP=1 on GPU 0 (util 0.90) | GPU 1: VLM (0.45), Laya, headroom | about 24 concurrent sequences |
| 1 x 80 GB | `df-lm-32b` FP8 (util 0.70) | same GPU: VLM 8B at util 0.18, Laya | about 12 concurrent sequences, or use `df-lm-14b` for more concurrency |
| 1 x 48 GB (L40S, RTX 6000 Ada) | `df-lm-14b` FP8 (util 0.70) | VLM 8B AWQ at 0.18, Laya | about 20 concurrent sequences |
| 1 x 24 GB | `df-lm-14b` AWQ 4-bit (util 0.80) | Laya on CPU, VLM off (Tier 3 skipped) | small teams |
| Ampere GPUs (A100) | FP8 runs as weight-only (Marlin kernels), or use AWQ | | FP8 KV still saves memory |

## 5. Laptop tiers

`deckforge doctor` detects RAM (psutil), Apple Silicon unified memory, and NVIDIA VRAM (`nvidia-smi --query-gpu=memory.total --format=csv,noheader`) and writes the tier into the lite config.

| Tier | Hardware | LM | Context | Ollama settings | Laya | VLM (Tier 3) | Worker slots | Deck time (estimate) |
|---|---|---|---|---|---|---|---|---|
| L1 | 16 GB RAM (Windows or Linux CPU, Apple M-series 16 GB) | `df-lm-8b` Q4_K_M (about 5 GB) | 16k | `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_CONTEXT_LENGTH=16384`, `OLLAMA_KV_CACHE_TYPE=q8_0`, `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_MAX_LOADED_MODELS=1` | ONNX int8 on CPU | off | 1 | 20 to 40 min |
| L2 | 32 GB RAM, Apple 32 GB, or NVIDIA 8 to 12 GB | `df-lm-8b` Q5_K_M or Q8_0 | 24k | parallel 2, same KV and flash settings | ONNX int8 or torch | `df-vlm` Q4 on Apple 32 GB, run once at the end of the run | 1 | 10 to 20 min |
| L3 | Apple 64 GB+, or NVIDIA 24 GB | `df-lm-14b` Q5_K_M (about 10.5 GB) | 32k | parallel 4 | torch (MPS or CUDA) | `df-vlm` Q4 | 2 | 6 to 12 min |
| below L1 | under 16 GB | not supported for local generation | | | | | | use a server install |

L1 memory budget: OS and browser 4 GB, LM 5 GB, KV for one 16k sequence about 1.3 GB, Laya ONNX 0.5 GB, app and worker 1.2 GB, LibreOffice during previews 0.6 GB. Total about 12.6 GB.

Laptop rules:
- One merged multitask model (no adapter switching): llama.cpp does not batch requests with different LoRA settings, and switching models in Ollama reloads weights.
- Ollama allocates KV for `num_parallel x context`, so parallelism and context are set together per tier.
- Tier 3 vision checks run once at the end of a run for all slides, so the VLM loads once (`OLLAMA_MAX_LOADED_MODELS=1` swaps models).
- `OLLAMA_KEEP_ALIVE=30m` keeps the LM loaded between runs.

## 6. Admission control (how we avoid out-of-memory)

vLLM manages KV blocks and preempts requests when KV runs out, which slows everything down. DeckForge keeps load below that point.

### 6.1 Model pools and router

`config/model_pools.yaml` replaces an external gateway:

```yaml
pools:
  lm:
    base: df-lm-32b-v1.0
    replicas:
      - {name: lm-a, url: http://vllm-lm-a:8000/v1, metrics: http://vllm-lm-a:8000/metrics}
      - {name: lm-b, url: http://vllm-lm-b:8000/v1, metrics: http://vllm-lm-b:8000/metrics, sleepable: true}
    adapters: [df-supervisor, df-intake, df-analyst, df-planner, df-researcher, df-viz, df-writer, df-art, df-reviewer, df-repair]
    budget_fraction: 0.80          # of measured KV capacity, the rest absorbs estimation error
  vlm:
    base: df-vlm-v1.0
    replicas: [{name: vlm, url: http://vllm-vlm:8000/v1, metrics: http://vllm-vlm:8000/metrics}]
lite:
  lm:  {url: http://127.0.0.1:11434/v1, model: "df-lm-8b:q4_k_m"}
  vlm: {url: http://127.0.0.1:11434/v1, model: "df-vlm:q4_k_m"}
```

`deckforge/llm/pool.py` (`ModelPool`):
1. At startup and every 5 s, reads each replica's Prometheus metrics: `vllm:kv_cache_usage_perc`, `vllm:num_requests_running`, `vllm:num_requests_waiting`, and the cache config (number of GPU blocks x block size gives KV capacity in tokens).
2. Routes each request to the replica with the lowest `kv_cache_usage_perc + 0.1 x num_requests_waiting`, preferring replicas that served the same adapter in the last 60 s (adapter affinity avoids loading adapters from CPU) and the same run (prefix cache affinity).
3. Skips replicas that are asleep, unhealthy (3 failed health checks) or above 92% KV usage.

### 6.2 Token budget semaphore

Every LLM call reserves `estimated_prompt_tokens + max_tokens` from its pool's budget (`budget_fraction x total KV capacity in tokens`) before it is sent, and releases it when the call ends.

- Server: Valkey Lua script (`deckforge/llm/budget.lua`) with `INCRBY`, a capacity check and a per-reservation key with a TTL of `timeout_s + 30` (a crashed worker cannot leak budget).
- Lite: an in-process `asyncio.Condition`.
- A call that cannot reserve waits in a priority queue.

Priority classes (reserved shares of the budget):

| Class | Examples | Reserved share | Waits behind |
|---|---|---|---|
| interactive | W2 revisions, clarification questions | 20% | nobody |
| generation | W1 planning and composition | 50% | interactive |
| qa | Tier 2 and Tier 3 judges, repairs | 20% | interactive, generation |
| background | evals, teacher generation, data builders | 10% (can borrow idle budget) | everyone |

### 6.3 Adaptive concurrency

Per replica, a concurrency limit starts at its `--max-num-seqs`:
- If `num_requests_waiting > 0` for 5 s, or KV usage above 95%: multiply the limit by 0.8.
- If KV usage below 70% and nothing waiting for 10 s: add 1, up to `--max-num-seqs`.

### 6.4 Degradation ladder (applied in order when a pool stays saturated for 60 s)

1. Pause `background` jobs and defer Tier 3 to the end of runs.
2. Shrink `ContextBuilder` budgets by 25% (exemplars dropped first).
3. Cap `max_tokens` per role to the observed p95 output length plus 10%.
4. Route `extractor` and `judge` calls to a smaller pool if one exists.
5. Stop leasing new `run.execute` jobs (runs stay queued, the API shows position and ETA).

Every step emits a metric and a warning event. Steps are undone in reverse order when load drops.

## 7. CPU memory and process hygiene

| Component | Rule |
|---|---|
| Worker process | Container limit 4 GB (server). Base about 0.5 GB |
| PPTX compile and pandas-heavy calcs | Run in a `ProcessPoolExecutor(max_workers=2, mp_context=spawn, max_tasks_per_child=50)` per worker process, so memory peaks are isolated and leaks are recycled |
| Tables | Load only needed columns from parquet with pyarrow, use pyarrow-backed and categorical dtypes, cap rows per query (`query_table` limit), never put tables in graph state |
| Images | Stream blobs, close Pillow images, never keep image bytes in state |
| LibreOffice | `DF_RENDERER_INSTANCES` sized so instances x 500 MB fits the renderer container limit |
| Laya on CPU | ONNX int8, `LAYA_THREADS` at physical cores |
| PostgreSQL | `shared_buffers` 25% of its container memory, `work_mem` 32 MB |
| Valkey | `maxmemory` set, `volatile-lru` |
| Lite on 16 GB | `DF_WORKER_SLOTS=1`, previews sequential, Tier 3 off |

If a container is killed for memory, its job lease expires, another worker re-leases the job and the run resumes from its last checkpoint (`06`, section 6). The event `run.error` with `retryable=true` is shown, then the run continues.

## 8. Speed

Ranked by expected effect for DeckForge's workload (many medium prompts with shared prefixes, short structured outputs):

| # | Lever | How | Expected effect (to measure in T-14.3) |
|---|---|---|---|
| 1 | Prefix caching and prompt layout | `--enable-prefix-caching`, stable sections first (`10`, section 9), run and adapter affinity in the router | 50% to 80% of prompt tokens served from cache in composition calls |
| 2 | Parallel slide composition | `Send` fan-out with `max_concurrency` 6 per run, budget semaphore for the global limit | composition stage time close to the slowest slide, not the sum |
| 3 | Non-thinking mode for structured roles | Qwen3 chat template switch `enable_thinking: false` through `extra_body={"chat_template_kwargs": {...}}` for writer, extractor, judge. Short thinking allowed for planner only if evals show it pays. Training data teaches the same behaviour | removes hundreds to thousands of reasoning tokens per call |
| 4 | Laya instead of LLM for decisions | `09` | tens of ms instead of seconds per decision |
| 5 | FP8 weights and FP8 KV cache | `--kv-cache-dtype fp8`, FP8 checkpoints | about 2x KV capacity, faster decode on Hopper and Ada |
| 6 | Tight output budgets | compact schemas, `max_tokens` per role from observed p95 | fewer decode steps |
| 7 | Speculative decoding | start with n-gram prompt lookup: `--speculative-config '{"method": "ngram", "num_speculative_tokens": 4, "prompt_lookup_max": 4}'` (JSON outputs copy fact ids and labels from the prompt). Later, train an EAGLE-3 draft head for `df-lm` (method `eagle3`) if n-gram acceptance is low | 1.3x to 2x decode speed on copy-heavy outputs |
| 8 | Chunked prefill and batch token budget | V1 engine defaults, tune `--max-num-batched-tokens` between 8192 and 16384 | balances time to first token and throughput |
| 9 | Structured decoding | vLLM's default xgrammar backend, small schemas, no huge enums | low overhead on constrained decoding |
| 10 | Adapter residency | `--max-loras 8` (all hot agents resident), `--max-cpu-loras 16`, adapter affinity | no adapter load stalls |
| 11 | Caches | `11` | repeated work avoided |
| 12 | CUDA graphs | keep vLLM defaults, never `--enforce-eager` in production | lower per-step overhead |

Targets (reference server, to validate): time to first token p95 under 1.5 s for composition calls, decode at least 30 tokens per second per sequence at normal load, 15-slide deck p50 under 5 minutes.

## 9. Training memory

| Model | Method | GPUs | Sequence | Micro-batch | Memory notes |
|---|---|---|---|---|---|
| 8B | QLoRA (NF4) | 1 x 24 GB | 8k | 1, gradient accumulation | about 6 GB weights, gradient checkpointing, liger kernels |
| 8B | LoRA bf16 | 1 x 80 GB | 16k | 2 to 4 | 16.4 GB weights |
| 14B | LoRA bf16 | 1 x 80 GB | 8k | 1 to 2 | 29.6 GB weights |
| 14B | QLoRA | 1 x 48 GB | 8k | 1 | |
| 32B | QLoRA | 1 x 80 GB | 8k | 1 | about 19 GB weights in 4-bit |
| 32B | LoRA bf16 with FSDP full shard or ZeRO-3 | 4 x 80 GB | 8k | 1 per GPU | 65.6 GB weights sharded, CPU offload of optimiser not needed for LoRA |
| GRPO 8B or 14B | LoRA, vLLM colocate | 1 x 80 GB | prompt 4k + completion 1.5k | 8 generations | `vllm_gpu_memory_utilization=0.3`, vLLM sleeps during the backward pass |
| GRPO 32B | LoRA, vLLM server mode | 2 GPUs training (FSDP) + 2 GPUs vLLM | | 8 generations | needs the whole server, weekend window |
| Teacher generation | vLLM offline | 1 x 80 GB (gpt-oss-120b) | | | night window on GPU 2 |

Always: flash attention 2, gradient checkpointing, sequence packing with padding-free batches, `use_liger_kernel=True`, bf16, periodic checkpoints every 30 minutes so the GPU scheduler can stop a job.

## 10. Monitoring memory and speed

| Signal | Source | Alert |
|---|---|---|
| GPU memory and utilisation | NVIDIA DCGM exporter | GPU memory above 95% for 5 min |
| KV usage, running and waiting requests | vLLM `/metrics` | KV above 90% for 5 min, waiting above 0 for 2 min |
| Prefix cache hit rate | vLLM metrics | below 40% for an hour (prompt layout regression) |
| Budget semaphore waits | `deckforge_llm_budget_wait_seconds{pool, class}` | p95 above 10 s for interactive |
| Degradation ladder step | `deckforge_degradation_step{pool}` | step 3 or higher for 15 min |
| Container memory and OOM kills | cAdvisor or Docker stats | any OOM kill |
| Laptop | `deckforge doctor --watch` prints RAM, model, tokens per second | |

## 11. Benchmarks to run (T-14.3, T-14.4)

1. vLLM startup logs per service: record KV capacity in tokens and compare with section 4.
2. Load test with the fake run profile replaced by real models: 20 concurrent runs, measure KV usage, waiting, deck p50 and p95.
3. Speculative decoding on and off on the copywriter and planner prompts.
4. FP8 versus bf16 KV on golden-brief QA scores (must stay within 0.5 points).
5. Laptop tiers L1 to L3 on one macOS, one Windows and one Linux machine: deck time, peak RAM, tokens per second.
Results replace the estimates in this document and in `01` section 8.
