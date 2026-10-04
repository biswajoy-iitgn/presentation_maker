# 11. Caching

## 1. Layers

| # | Layer | What is cached | Store (server / lite) | Key | TTL | Invalidated by |
|---|---|---|---|---|---|---|
| 1 | HTTP static | SPA assets (hashed file names), fonts | nginx / FastAPI `StaticFiles` | URL | 1 year, `immutable` | new build (new hashes). `index.html` is `no-cache` |
| 2 | API conditional GET | Artifacts, previews, design-system previews | ETag = sha256 of blob | URL + ETag | client-side | blob content change |
| 3 | LLM response (exact) | Parsed structured output of deterministic calls | Valkey + optional `llm_cache` table / SQLite cache table | see 2.1 | 7 days | prompt version, model id, schema hash, params |
| 4 | Provider prefix cache | KV cache of stable prompt prefixes | vLLM GPU memory, Anthropic server cache | automatic prefix match | vLLM: LRU in GPU memory. Anthropic: 5 min or 1 h | any byte change in the prefix |
| 5 | Laya decision | `Decision` for an exact state text | Valkey / SQLite | see 2.2 | 30 days | question version, checkpoint |
| 6 | Embeddings | Vectors for texts | `kb_items` for corpora, Valkey for ad-hoc texts / SQLite | `emb:{model}:{sha256(text)}` | 90 days (ad-hoc) | embedding model change |
| 7 | Tool results | `ToolResult.data` for cacheable tools | Valkey / SQLite | see 2.3 | per `ToolSpec.cache_ttl_s` | tool version |
| 8 | Assets | Icons, flags, maps, Natural Earth GeoJSON, stock photos, generated images | Blob store `assets/` (content addressed) + in-process LRU | sha256 of source URL + params, then content sha | permanent (licence sidecar) | never (new params give a new key) |
| 9 | Previews | PNGs of a deck version | Blob store | `deck_hash` = sha256(pptx bytes) | life of the deck version | new deck version |
| 10 | LangGraph node cache | Output of pure deterministic nodes (`bind_data`, table profiling, template ingestion steps) | `RedisCache` / `SqliteCache` | `CachePolicy.key_func` over the node inputs | 24 h | input change |

## 2. Key construction

All keys are built in `deckforge/cache/keys.py`. Canonical JSON: `orjson.dumps(obj, option=orjson.OPT_SORT_KEYS)`. Hash: sha256 hex (first 32 chars are enough for keys, full hash stored in the value for verification).

### 2.1 LLM response cache

```text
llm:{org_scope}:{provider}:{model}:{prompt_id}:v{prompt_version}:{schema_hash}:{params_hash}:{sha256(rendered_messages)}
```

- `org_scope` = org id. Never shared across orgs, because rendered messages contain customer data.
- Only for calls with temperature 0 (or Anthropic roles with effort `low` used for extraction and judging) and `cacheable: true` in the prompt front matter. Generation prompts (`write_copy`, `storyline`) are cacheable only within the same run (the key adds the run id), so re-running a node after a crash does not pay twice, but two runs do not get identical copy.
- A run option `fresh: true` bypasses layer 3 for that run.

### 2.2 Laya decision cache

```text
dec:{decision_id}:v{question_version}:{checkpoint}:{rotation_flag}:{sha256(state_text + canonical(options))}
```

Shared across orgs is safe only for decisions whose state contains no customer data (`D_ICON_PICK` uses concept labels). The YAML field `cache_scope: org | shared` decides, default `org`.

### 2.3 Tool cache

```text
tool:{name}:v{version}:{org_scope}:{sha256(canonical(args))}
```

`org_scope` is `shared` only for tools on the shared-safe list (`08`, section 4).

## 3. Stampede protection

Expensive computations (template ingestion, research fetches, preview renders) take a lock before computing:

```python
async with cache.lock(f"lock:{key}", ttl_s=120) as acquired:
    if not acquired:
        return await cache.wait_for(key, timeout_s=120)      # another worker computes, poll every 0.5 s
    value = await compute()
    await cache.set(key, value, ttl_s)
```

Valkey: `SET lock:key token NX PX 120000`, released with a Lua compare-and-delete. Lite: `asyncio.Lock` per key in a weak dict.

## 4. Valkey configuration

| Logical DB | Use | Eviction |
|---|---|---|
| 0 | Cache layers 3, 5, 6, 7, 10 | `allkeys-lru`, `maxmemory` 4 GB on the reference node |
| 1 | Rate-limit buckets, locks | must not evict: run as a separate Valkey instance or keep DB 0 policy aware (`volatile-lru` with TTLs on all cache keys). Default: one instance, `volatile-lru`, every cache key has a TTL, buckets have TTLs too |
| 2 | Pub/sub channels `run:{id}` | not stored |

Persistence: RDB snapshots off for the cache (it is rebuildable). If rate limits must survive restarts, enable AOF on the separate instance.

## 5. Tenancy and safety rules

1. Every cache key that can contain customer content includes the org id.
2. Cache values for LLM and tool results are stored with the org id inside the value too. On read, a mismatch is treated as a miss and logged as an error.
3. Org deletion runs `SCAN MATCH *:{org_id}:*` and deletes keys (and the SQLite equivalent in lite).
4. No semantic (similarity-based) cache for generation. A near-match answer for a different client's brief is a correctness and confidentiality risk.

## 6. Metrics

`deckforge_cache_requests_total{layer, result="hit|miss|error"}`, `deckforge_cache_bytes{layer}`. Dashboards show hit rate per layer (`16`). Expected steady-state: layer 4 (vLLM prefix) above 60% of prompt tokens, layer 5 above 30% (repeated icon and column decisions), layer 3 low (by design).
