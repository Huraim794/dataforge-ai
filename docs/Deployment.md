# Deployment

## System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Disk | 20 GB SSD | 50+ GB SSD |
| Network | 100 Mbps | 1 Gbps |

The browser pool (Playwright Chromium) is the primary resource consumer. Each browser context uses approximately 200-400 MB RAM. At peak, `max_concurrent_browsers` (default: 10) contexts may run simultaneously.

---

## Docker Deployment

### Prerequisites

- Docker Engine 24+
- Docker Compose v2.20+ (included with Docker Desktop)

### Quick Start

```bash
cd infra
cp .env.example .env
# Edit .env with your LLM_API_KEY and SECRET_KEY
docker compose up -d
```

This starts:

| Service | Container | Port |
|---------|-----------|------|
| PostgreSQL 16 | `dataforge-postgres-1` | 5432 |
| Redis 7 | `dataforge-redis-1` | 6379 |
| FastAPI | `dataforge-api-1` | 8000 |
| Worker (×2) | `dataforge-worker-1` | — |
| Nginx | `dataforge-nginx-1` | 80, 443 |

### Service Health Checks

Postgres and Redis have Docker health checks. The API and worker wait for both to be healthy before starting.

---

## Production Deployment

```bash
cd infra
cp .env.example .env
# Set production values (see Environment Variables table)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

The production override (`docker-compose.prod.yml`) adds:

- Environment variables externalized via `.env` (secrets never hardcoded)
- `ENVIRONMENT=production` (stricter validation, secret key requirement)
- Worker replicas configurable via `WORKER_REPLICAS` env var (default: 3)
- Persistent data volumes at configurable `VOLUME_PREFIX` path
- SSL certificate mount (`./nginx/ssl/`)
- `restart: always` policy on all services

---

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Runtime environment | `development` | No |
| `DEBUG` | Enable debug mode | `false` | No |
| `LOG_LEVEL` | Logging verbosity | `INFO` | No |
| `SECRET_KEY` | JWT signing secret | `dataforge-...` (dev) | **Yes** (prod) |
| `DATABASE_URL` | Async Postgres DSN | `postgresql+asyncpg://...` | No |
| `DATABASE_SYNC_URL` | Sync Postgres DSN (migrations) | `postgresql://...` | No |
| `POSTGRES_DB` | Database name | `dataforge` | No |
| `POSTGRES_USER` | Database user | `dataforge` | No |
| `POSTGRES_PASSWORD` | Database password | `dataforge` | **Yes** (prod) |
| `REDIS_URL` | Redis connection (db 0) | `redis://localhost:6379/0` | No |
| `REDIS_QUEUE_URL` | Redis for job queues (db 1) | `redis://localhost:6379/1` | No |
| `REDIS_CACHE_URL` | Redis for rate limiting (db 2) | `redis://localhost:6379/2` | No |
| `API_HOST` | Bind address | `0.0.0.0` | No |
| `API_PORT` | Port | `8000` | No |
| `ALLOWED_ORIGINS` | CORS origins (comma-separated) | `http://localhost:3000,http://localhost:5173` | No |
| `LLM_PROVIDER` | AI provider | `openai` | No |
| `LLM_API_KEY` | Provider API key | — | **Yes** |
| `LLM_MODEL` | Model name | `gpt-4o` | No |
| `LLM_TEMPERATURE` | LLM temperature | `0.1` | No |
| `LLM_MAX_TOKENS` | Max response tokens | `4096` | No |
| `CAPTCHA_SERVICE_API_KEY` | 2Captcha key | — | No |
| `CAPTCHA_AUTO_SOLVE` | Enable auto captcha solving | `false` | No |
| `SENTRY_DSN` | Sentry project DSN | — | No |
| `PROMETHEUS_ENABLED` | Enable /metrics endpoint | `true` | No |
| `STORAGE_BACKEND` | Storage backend | `local` | No |
| `STORAGE_LOCAL_PATH` | Local storage path | `./data/storage` | No |
| `BROWSER_HEADLESS` | Run Playwright headless | `true` | No |
| `MAX_CONCURRENT_BROWSERS` | Max simultaneous scrapes | `10` | No |
| `PROXY_POOL_SIZE` | Max proxies in pool | `50` | No |
| `WORKER_REPLICAS` | Worker container count (prod) | `3` | No |
| `VOLUME_PREFIX` | Data volume directory prefix (prod) | `./data` | No |

---

## SSL/TLS Configuration

Nginx terminates TLS. In production, place certificates at `infra/nginx/ssl/cert.pem` and `infra/nginx/ssl/key.pem`.

The nginx config enforces:

- TLS 1.2 and 1.3 only
- Strong cipher suites (`HIGH:!aNULL:!MD5`)
- HSTS for 2 years (`Strict-Transport-Security: max-age=63072000`)
- Server tokens disabled

To use Let's Encrypt:

```bash
docker run --rm -v infra/nginx/ssl:/etc/letsencrypt -p 80:80 certbot/certbot \
  certonly --standalone -d yourdomain.com
```

Then reference the generated certificates in `nginx/api.conf`.

---

## Scaling Considerations

### Worker Replicas

The worker processes jobs from Redis queues. Scale horizontally:

```bash
docker compose up -d --scale worker=5
```

Each worker runs its own browser pool (pre-warmed contexts). Workers share nothing except the database and Redis. Idempotent job processing means duplicate jobs are handled gracefully.

### Browser Pool Sizing

| Setting | Description | Suggested |
|---------|-------------|-----------|
| `browser_pool_min` | Pre-warmed contexts per worker | `2` |
| `browser_pool_max` | Maximum contexts per worker | `10` |
| `browser_pool_max_uses_per_context` | Context recycle threshold | `50` |

For heavy scraping workloads, increase `browser_pool_max` and ensure sufficient RAM (400 MB per context). Monitor `browser_pool_size` Prometheus metric.

### Database Connection Pool

| Setting | Default | Suggested |
|---------|---------|-----------|
| `database_pool_size` | 20 | Worker replicas × 5 |
| `database_max_overflow` | 10 | 5 per replica |

### Redis Memory

Redis uses separate databases:

- db 0: General cache (configuration, user sessions)
- db 1: Job queues (list-based priority queues)
- db 2: Rate limiter (sorted sets with TTL)

Monitor Redis memory and set `maxmemory` in `redis.conf`. The `queue_result_ttl` (default: 86400s) controls how long job results remain in the database.

---

## Database Migrations

Alembic migrations live in `backend/migrations/`. Apply migrations inside the API container:

```bash
# Run migrations
docker compose exec api alembic upgrade head

# Create a new migration
docker compose exec api alembic revision --autogenerate -m "description"

# Rollback one step
docker compose exec api alembic downgrade -1
```

Migrations run automatically only if you configure them in the startup script. By default, `Base.metadata.create_all` runs at startup (sufficient for development).

---

## Monitoring Setup

### Prometheus Metrics

The API exposes Prometheus metrics at `/metrics` (port 8000) and at `/api/v1/monitoring/metrics`. Metrics include:

- `dataforge_jobs_total` — Job counts by status
- `dataforge_job_duration_seconds` — Job duration histogram
- `dataforge_browser_pool_size` — Pool size (healthy/total)
- `dataforge_browser_launches_total` — Browser launches by type
- `dataforge_proxy_requests_total` — Proxy request success/failure
- `dataforge_proxy_active` — Active proxy count
- `dataforge_extraction_tokens_total` — Token usage by provider
- `dataforge_extraction_cost_usd` — Cost by provider

Configure a Prometheus server to scrape the API endpoint:

```yaml
scrape_configs:
  - job_name: 'dataforge'
    static_configs:
      - targets: ['api:8000']
```

### Sentry Error Tracking

Set `SENTRY_DSN` to enable automatic error reporting. The `sentry-sdk` library captures unhandled exceptions, performance traces, and log messages from the structured logger.
