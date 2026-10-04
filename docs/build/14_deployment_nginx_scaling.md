# 14. Deployment, nginx and scaling

## 1. Lite install (one user, macOS, Windows, Linux)

Prerequisites: Python is not required beforehand, `uv` installs it. Optional: Ollama (local models), LibreOffice (previews).

| Step | macOS | Windows (PowerShell) | Linux |
|---|---|---|---|
| Install uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` | same as macOS |
| Install DeckForge | `uv tool install "deckforge[lite]"` | same | same |
| Optional local LLM | Install Ollama, `ollama pull <model from config/models.yaml laptop profile>` | same | same |
| Optional previews | `brew install --cask libreoffice` | `winget install TheDocumentFoundation.LibreOffice` | `sudo apt install libreoffice-impress` |
| Optional Laya | `uv tool install "deckforge[lite,laya]"` (pulls torch, about 2 GB) or `deckforge[lite,laya-onnx]` on CPU-only machines | same | same |
| First start | `deckforge init` (creates data dir, secrets, admin account, prints login link) then `deckforge serve` | same | same |

`deckforge serve` in lite mode starts one process: uvicorn with the API and the SPA on `127.0.0.1:8765`, plus the in-process worker (asyncio tasks, `DF_WORKER_SLOTS=2`). `deckforge doctor` checks Python, write access, Ollama reachability, LibreOffice discovery, Laya availability and prints what is enabled.

For non-technical users, P12 adds platform installers built with PyInstaller (`deckforge-<version>-macos.dmg`, `-windows.msi`, `-linux.AppImage`) that embed Python and open the browser on start (decision request DR to be raised in T-12.6 for code signing certificates).

## 2. Server install (Docker Compose)

Reference: one CPU host and one GPU host on a private network. A single host with a GPU also works (all services on one machine).

### 2.1 Files

```text
deploy/compose/
├── docker-compose.yml
├── .env.server.example          # copy to .env and fill secrets
├── secrets/                     # created by `deckforge secrets init`: jwt, secrets_key, laya_key, litellm_master_key, postgres_password
deploy/nginx/
├── nginx.conf
├── conf.d/deckforge.conf
└── snippets/security_headers.conf, proxy_headers.conf
deploy/litellm/config.yaml
```

### 2.2 `docker-compose.yml`

```yaml
name: deckforge

x-app-env: &app-env
  DF_MODE: server
  DF_DATABASE_URL: postgresql+psycopg://deckforge:${POSTGRES_PASSWORD}@postgres:5432/deckforge
  DF_REDIS_URL: redis://valkey:6379/0
  DF_BLOB_BACKEND: fs
  DF_BLOB_ROOT: /data/blobs
  DF_LAYA_MODE: http
  DF_LAYA_URL: http://laya:8200
  DF_RENDERER_URL: http://renderer:8100
  DF_LLM_GATEWAY_URL: http://litellm:4000/v1
  DF_JWT_SECRET_FILE: /run/secrets/jwt
  DF_SECRETS_KEY_FILE: /run/secrets/secrets_key
  DF_LAYA_API_KEY_FILE: /run/secrets/laya_key
  DF_LLM_GATEWAY_KEY_FILE: /run/secrets/litellm_key

x-app: &app
  image: ghcr.io/deckforge/deckforge:${DF_VERSION}
  env_file: .env
  environment: *app-env
  volumes:
    - blobs:/data/blobs
  secrets: [jwt, secrets_key, laya_key, litellm_key]
  restart: unless-stopped
  depends_on:
    postgres: {condition: service_healthy}
    valkey: {condition: service_healthy}
    migrate: {condition: service_completed_successfully}

services:
  nginx:
    image: ghcr.io/deckforge/deckforge-nginx:${DF_VERSION}   # nginx:stable + built SPA + config
    ports: ["80:80", "443:443"]
    volumes: [./certs:/etc/nginx/certs:ro]
    depends_on: [api]
    restart: unless-stopped

  migrate:
    image: ghcr.io/deckforge/deckforge:${DF_VERSION}
    env_file: .env
    environment:
      DF_MODE: server
      DF_DATABASE_URL: postgresql+psycopg://deckforge:${POSTGRES_PASSWORD}@postgres:5432/deckforge
    command: ["deckforge", "migrate"]
    depends_on:
      postgres: {condition: service_healthy}
    restart: "no"

  api:
    <<: *app
    command: ["deckforge", "serve", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
    deploy: {replicas: 2, resources: {limits: {cpus: "2", memory: 2g}}}
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/readyz')"]
      interval: 10s
      timeout: 3s
      retries: 6

  worker:
    <<: *app
    command: ["deckforge", "worker"]
    environment:
      <<: *app-env                 # a plain `environment:` here would replace the whole anchored map
      DF_WORKER_SLOTS: "4"
    deploy: {replicas: 6, resources: {limits: {cpus: "2", memory: 4g}}}

  renderer:
    image: ghcr.io/deckforge/deckforge-renderer:${DF_VERSION}
    environment: {DF_RENDERER_INSTANCES: "6"}
    deploy: {resources: {limits: {cpus: "6", memory: 6g}}}
    tmpfs: [/tmp]
    restart: unless-stopped

  laya:
    image: ghcr.io/deckforge/deckforge-laya:${DF_VERSION}
    profiles: ["laya"]
    environment:
      LAYA_DEVICE: ${LAYA_DEVICE:-cpu}
      LAYA_THREADS: "8"
      LAYA_PRELOAD: "1"
      LAYA_MAX_LOADED: "3"
      LAYA_MODELS: ${LAYA_MODELS:-/models/df-laya-active,convaiinnovations/laya}
      HF_HUB_OFFLINE: "1"
      HF_HUB_CACHE: /models/hf
    secrets: [laya_key]          # entrypoint exports LAYA_API_KEY from /run/secrets/laya_key
    volumes: [laya_models:/models:ro]
    restart: unless-stopped

  litellm:
    image: ghcr.io/berriai/litellm:${LITELLM_TAG}
    profiles: ["llm"]
    entrypoint: ["sh", "-c", "export LITELLM_MASTER_KEY=$$(cat /run/secrets/litellm_key) && exec litellm --config /app/config.yaml --port 4000"]
    volumes: [../litellm/config.yaml:/app/config.yaml:ro]
    environment:
      DATABASE_URL: postgresql://deckforge:${POSTGRES_PASSWORD}@postgres:5432/litellm
    secrets: [litellm_key]
    restart: unless-stopped

  vllm:
    image: vllm/vllm-openai:${VLLM_TAG}
    profiles: ["gpu"]
    command: ["--model", "${PLANNER_MODEL_PATH}", "--served-model-name", "planner-main",
              "--enable-prefix-caching", "--max-model-len", "65536", "--tensor-parallel-size", "${TP:-4}",
              "--gpu-memory-utilization", "0.88"]
    volumes: [models:/models:ro]
    deploy: {resources: {reservations: {devices: [{driver: nvidia, count: all, capabilities: [gpu]}]}}}
    restart: unless-stopped

  postgres:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_USER: deckforge
      POSTGRES_DB: deckforge
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets: [postgres_password]
    command: ["postgres", "-c", "max_connections=300", "-c", "shared_buffers=4GB", "-c", "effective_cache_size=12GB",
              "-c", "work_mem=32MB", "-c", "wal_level=replica"]
    volumes: [pgdata:/var/lib/postgresql/data]
    healthcheck: {test: ["CMD-SHELL", "pg_isready -U deckforge"], interval: 5s, timeout: 3s, retries: 10}
    restart: unless-stopped

  valkey:
    image: valkey/valkey:8
    command: ["valkey-server", "--maxmemory", "4gb", "--maxmemory-policy", "volatile-lru", "--save", ""]
    healthcheck: {test: ["CMD", "valkey-cli", "ping"], interval: 5s, timeout: 3s, retries: 10}
    restart: unless-stopped

  searxng:
    image: searxng/searxng:${SEARXNG_TAG}
    profiles: ["search"]
    volumes: [./searxng:/etc/searxng]
    restart: unless-stopped

  otel-collector:
    image: otel/opentelemetry-collector-contrib:${OTEL_TAG}
    profiles: ["observability"]
    volumes: [../observability/otel-collector.yaml:/etc/otelcol-contrib/config.yaml:ro]
  prometheus:
    image: prom/prometheus:${PROM_TAG}
    profiles: ["observability"]
    volumes: [../observability/prometheus.yml:/etc/prometheus/prometheus.yml:ro]
  grafana:
    image: grafana/grafana:${GRAFANA_TAG}
    profiles: ["observability"]
    volumes: [../observability/grafana:/etc/grafana/provisioning:ro]

volumes: {pgdata: {}, blobs: {}, models: {}, laya_models: {}}

secrets:
  jwt: {file: ./secrets/jwt}
  secrets_key: {file: ./secrets/secrets_key}
  laya_key: {file: ./secrets/laya_key}
  litellm_key: {file: ./secrets/litellm_master_key}
  postgres_password: {file: ./secrets/postgres_password}
```

The app reads `*_FILE` variants of secret settings (`DF_JWT_SECRET_FILE=/run/secrets/jwt` and so on): `Settings` loads the file content when the `_FILE` variable is set (T-0.5). The `litellm` database is created by the migrate step (`CREATE DATABASE litellm` if missing). `deckforge secrets init` writes the secret files and the matching `POSTGRES_PASSWORD` line into `.env` (Compose interpolates it into connection strings).

Start: `docker compose --profile laya --profile llm --profile gpu up -d` on a single GPU host, or split services across hosts with the same file and `DOCKER_HOST` per host (or move to Kubernetes, section 7).

### 2.3 LiteLLM config (`deploy/litellm/config.yaml`)

```yaml
model_list:
  - model_name: planner-main
    litellm_params: {model: openai/planner-main, api_base: http://vllm:8000/v1, api_key: "none"}
  - model_name: vision-main
    litellm_params: {model: openai/vision-main, api_base: http://vllm-vision:8000/v1, api_key: "none"}
litellm_settings:
  drop_params: false
  num_retries: 2
  request_timeout: 300
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL
router_settings:
  routing_strategy: least-busy
```

DeckForge creates one LiteLLM virtual key per org (`POST /key/generate` with `max_budget`, `rpm_limit`, `tpm_limit`, `metadata.org_id`) when the org is created, stores it encrypted in `provider_credentials`, and uses it for that org's calls. Anthropic traffic does not go through the OpenAI-format route (`07`, A6). If central control of Anthropic keys is required, use LiteLLM's Anthropic pass-through endpoint with `ChatAnthropic(anthropic_api_url=...)`.

## 3. nginx

### 3.1 `deploy/nginx/nginx.conf`

```nginx
user nginx;
worker_processes auto;
worker_rlimit_nofile 65535;
events { worker_connections 8192; }

http {
  include       /etc/nginx/mime.types;
  default_type  application/octet-stream;
  server_tokens off;
  sendfile on;
  tcp_nopush on;
  keepalive_timeout 65;

  map $http_x_request_id $req_id { default $http_x_request_id; "" $request_id; }
  log_format json escape=json '{"time":"$time_iso8601","req_id":"$req_id","ip":"$remote_addr",'
                              '"method":"$request_method","uri":"$uri","status":$status,'
                              '"bytes":$body_bytes_sent,"rt":$request_time,"urt":"$upstream_response_time"}';
  access_log /var/log/nginx/access.log json;

  gzip on;
  gzip_min_length 1024;
  gzip_types text/css application/javascript application/json image/svg+xml text/plain;

  client_max_body_size 50m;              # must equal DF_MAX_UPLOAD_MB
  client_body_timeout 60s;

  limit_req_zone  $binary_remote_addr zone=api:20m   rate=20r/s;
  limit_req_zone  $binary_remote_addr zone=login:10m rate=5r/m;
  limit_conn_zone $binary_remote_addr zone=perip:10m;
  limit_req_status 429;
  limit_conn_status 429;

  upstream api_upstream {
    least_conn;
    server api:8000 max_fails=3 fail_timeout=10s;   # Docker DNS returns all replicas at startup
    keepalive 64;
  }

  include /etc/nginx/conf.d/*.conf;
}
```

### 3.2 `deploy/nginx/conf.d/deckforge.conf`

```nginx
server {
  listen 80;
  server_name _;
  location = /healthz { return 200 "ok"; }
  location / { return 301 https://$host$request_uri; }
}

server {
  listen 443 ssl;
  http2 on;
  server_name _;

  ssl_certificate     /etc/nginx/certs/fullchain.pem;
  ssl_certificate_key /etc/nginx/certs/privkey.pem;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_session_cache shared:SSL:20m;
  ssl_session_timeout 1d;

  include /etc/nginx/snippets/security_headers.conf;
  root /usr/share/nginx/html;

  # SPA
  location /assets/ {
    include /etc/nginx/snippets/security_headers.conf;   # add_header in a location drops inherited headers
    add_header Cache-Control "public, max-age=31536000, immutable";
    try_files $uri =404;
  }
  location = /index.html {
    include /etc/nginx/snippets/security_headers.conf;
    add_header Cache-Control "no-cache";
  }
  location / { try_files $uri /index.html; }

  # API
  location /api/ {
    limit_req  zone=api burst=40 nodelay;
    limit_conn perip 60;
    proxy_pass http://api_upstream;
    include /etc/nginx/snippets/proxy_headers.conf;
    proxy_read_timeout 60s;
  }

  location = /api/v1/auth/login {
    limit_req zone=login burst=5 nodelay;
    proxy_pass http://api_upstream;
    include /etc/nginx/snippets/proxy_headers.conf;
  }

  # Uploads: allow slow clients, keep request buffering on so the API sees complete bodies
  location ~ ^/api/v1/projects/[^/]+/files$ {
    limit_req zone=api burst=10 nodelay;
    proxy_pass http://api_upstream;
    include /etc/nginx/snippets/proxy_headers.conf;
    proxy_request_buffering on;
    proxy_read_timeout 120s;
  }

  # Server-sent events: no buffering, long timeout
  location ~ ^/api/v1/runs/[^/]+/events$ {
    proxy_pass http://api_upstream;
    include /etc/nginx/snippets/proxy_headers.conf;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 3600s;
    include /etc/nginx/snippets/security_headers.conf;
    add_header X-Accel-Buffering no;
  }

  location /metrics { deny all; }
}
```

`snippets/proxy_headers.conf`:

```nginx
proxy_http_version 1.1;
proxy_set_header Connection "";
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Request-ID $req_id;
```

`snippets/security_headers.conf`:

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
add_header Content-Security-Policy "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" always;
```

`http2 on;` needs nginx 1.25.1 or later (the official `nginx:stable` image qualifies). On an older distribution nginx, write `listen 443 ssl http2;` instead. The configuration above passed `nginx -t` on 2026-10-04 with that one substitution on nginx 1.24.

Uvicorn behind nginx: run with `--proxy-headers --forwarded-allow-ips="*"` only on the internal network (the API is not published), so client IPs and scheme are correct.

TLS: customer certificate files mounted at `deploy/compose/certs/`. For internet-facing installs, an optional `certbot` profile renews Let's Encrypt certificates and reloads nginx.

After changing the number of API replicas: `docker compose exec nginx nginx -s reload` so nginx re-resolves the `api` name.

## 4. Scaling

| Bottleneck | Signal | Action |
|---|---|---|
| API CPU or latency | p95 `http_request_duration_seconds` above 300 ms, CPU above 70% | Add API replicas (stateless). Reload nginx |
| Queue wait | `deckforge_jobs_ready` above 2 x worker slots for 5 min, run start delay p95 above 60 s | Add worker replicas |
| LLM throughput | vLLM queue time, gateway 429s, per-role semaphore wait | Add GPU capacity (more vLLM replicas behind LiteLLM `least-busy`), reduce `DF_RUN_MAX_CONCURRENCY` temporarily |
| Renderer | renderer busy ratio above 80%, render time p95 above 30 s | Raise `DF_RENDERER_INSTANCES` or add renderer replicas (stateless, any number) |
| Laya | p95 decision latency above 200 ms | Move Laya to GPU, add replicas (stateless, read-only models) |
| PostgreSQL connections | above 70% of `max_connections` | Lower pool sizes, add PgBouncer in session mode (transaction mode breaks `LISTEN/NOTIFY` and prepared statements) |
| PostgreSQL CPU | above 70% sustained | Vertical scaling first. Read replica for analytics and usage dashboards |
| Valkey memory | evictions of hot cache keys | Raise `maxmemory`, or reduce TTLs of layer 6 and 7 |

Concurrency budget on the reference node (to validate in T-12.3): 2 API replicas x 4 uvicorn workers handle well over 100 active sessions (each SSE connection is one coroutine). 6 workers x 4 slots = 24 concurrent jobs, 20 for runs and 4 left for profiling and ingestion through `DF_WORKER_KINDS` on one dedicated worker.

## 5. High availability (optional tier)

- Two nginx instances behind the customer's load balancer or keepalived VIP.
- API and workers: at least 2 replicas each, spread across two hosts.
- PostgreSQL: primary with streaming replica and automated failover (Patroni) or the customer's managed PostgreSQL.
- Valkey: losing it degrades caching and live events (SSE falls back to polling `run_events`), runs continue. Sentinel optional.
- Blob store: S3-compatible with replication, or a replicated volume.

## 6. Air-gapped install

1. On a connected machine: `deckforge bundle --version X --models planner,vision,laya --out bundle/` exports Docker images (`docker save`), model weights (HF cache directories), the Python wheelhouse, Lucide icons and Natural Earth data.
2. Copy the bundle. On the target: `docker load`, copy models into the `models` and `laya_models` volumes, `docker compose up`.
3. Settings: `HF_HUB_OFFLINE=1`, `DF_SEARCH_BACKEND=none`, stock image sources disabled, `DF_EGRESS_PROXY` empty and outbound traffic blocked at the firewall.

## 7. Kubernetes (P12)

Helm chart `deploy/helm/deckforge` with: Deployments for api, worker, renderer, laya, nginx (or the cluster ingress controller with the same rules as section 3), StatefulSets only if the customer has no managed PostgreSQL and Valkey. HorizontalPodAutoscaler for api (CPU) and renderer (CPU). Worker autoscaling with KEDA's PostgreSQL scaler on `SELECT count(*) FROM app.jobs WHERE status='queued'`. GPU node pool for vLLM and Laya with node selectors and tolerations. Secrets from the cluster secret store.

## 8. Backups and restore

| Data | Method | Frequency | Retention |
|---|---|---|---|
| PostgreSQL | `pgBackRest` full weekly, differential daily, WAL archiving | continuous | 30 days |
| Blobs | filesystem snapshot or S3 replication/versioning | daily | 30 days |
| Secrets | offline copy by the customer admin | on change | |
| Models | re-downloadable or in the bundle | | |

Restore drill (T-12.7): restore to a fresh host, run `deckforge doctor`, open three recent decks, resume a run that was `waiting_input` at backup time.

## 9. Upgrades

1. Read release notes for migration and graph-version changes.
2. `docker compose pull`.
3. `docker compose up -d migrate` (Alembic upgrade, backward compatible within a minor version).
4. Roll API, then workers. Workers of the old version finish their jobs (graceful shutdown: stop leasing, wait up to 10 min for slots to drain, then exit).
5. Runs with an old `graph_version` that the new workers do not support stay queued for an old-version worker kept running with `DF_WORKER_KINDS=run.resume` until drained (`06`, section 9).
