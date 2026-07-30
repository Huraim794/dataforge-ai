# Performance Guide

## Architecture for Performance

DataForge AI is built on an asynchronous foundation throughout the stack:

- **FastAPI** with async route handlers and ASGI (uvicorn with multiple workers) provides non-blocking request processing.
- **SQLAlchemy 2.0 Async** with `asyncpg` driver enables non-blocking database access. The engine is created once at startup with a shared connection pool.
- **httpx.AsyncClient** is used for all outbound HTTP calls (proxy checking, LLM API calls), with connection pooling and keep-alive.
- **redis.asyncio** provides non-blocking Redis operations for queue, caching, and pub/sub.
- **Playwright** browser automation runs in async mode with a shared browser pool, avoiding per-request browser launches.
- All long-running components (browser pool, proxy manager, queue consumer) use `asyncio.create_task` for concurrent background operations.

## Database Optimization

### Connection Pool Settings

The async engine (in `backend/app/core/database.py`) is configured with:

```python
engine = create_async_engine(
    database_url,
    echo=debug,
    pool_size=20,          # Persistent connections in pool
    max_overflow=10,       # Extra connections beyond pool_size under load
    pool_pre_ping=True,    # Verify connection before use (prevents stale connections)
    pool_recycle=3600,     # Recycle connections after 1 hour
)
```

- `pool_size=20`: 20 persistent connections ready to serve requests. Suitable for up to ~20 concurrent workers. For higher worker counts, increase to `2 * api_workers`.
- `max_overflow=10`: Allows up to 30 total connections (20 + 10) under burst load. Connections above `pool_size` are closed when returned.
- `pool_pre_ping=True`: Issues `SELECT 1` before handing out a connection. Adds ~1ms latency per acquisition but prevents errors from dropped connections.
- `pool_recycle=3600`: Forces connection recycling after 1 hour to avoid server-side timeouts (e.g., PostgreSQL's `idle_in_transaction_session_timeout`).

### Query Patterns

- **Sessions are short-lived**: The `async_session_factory` is used as a context manager (`async with async_session_factory() as session`), creating sessions per operation rather than holding them open.
- **Direct `execute` + `update`**: Status transitions (e.g., `JobStatus.RUNNING`, `RunStatus.COMPLETED`) use `session.execute(update(...))` for efficient single-statement updates without loading full ORM objects.
- **Batch operations**: Proxy health checks batch update proxy status in a single commit after concurrent checking.
- **Selective loading**: Queries use `select()` with filters (e.g., `select(Proxy).where(Proxy.status == ProxyStatus.ACTIVE)`) rather than loading all rows.

### N+1 Prevention

The codebase avoids common N+1 patterns:

- Proxy pool loading fetches all active proxies in a single query and materializes them into dictionaries for in-memory access.
- Job processing uses direct `update` statements rather than load-modify-save cycles.
- Run and Job status updates use `update()` on primary key, which is a single round-trip.

**Note**: The `_process_job` method in `tasks.py` opens separate sessions for each status update (run creation, job update, run update, result save). This is intentional for granular error handling — each step can fail independently — but under high throughput, these could be batched into fewer sessions.

## Browser Pool Optimization

### Configuration

| Setting | Default | Description |
|---|---|---|
| `browser_pool_min` | 2 | Minimum browsers kept warm on startup and after health checks |
| `browser_pool_max` | 10 | Maximum concurrent browser instances |
| `browser_pool_idle_timeout_seconds` | 300 | Idle browser cleanup timeout (currently monitored but not actively evicted) |
| `browser_pool_health_check_seconds` | 30 | Interval between health check cycles |
| `browser_pool_max_uses_per_context` | 50 | Browser context recycled after this many uses |

### Pool Behavior

- **Warm pool on start**: `_warm_pool()` launches `browser_pool_min` browsers immediately on startup, avoiding cold-start latency for initial requests.
- **Context recycling**: Each `BrowserInstance` tracks `use_count`. After `max_uses_per_context` (50) uses, the instance is destroyed and replaced on release.
- **Acquire strategy**:
  1. Fast path: Under `_lock`, cycle through instances to find a healthy one with remaining uses (matching proxy if specified).
  2. Create path: Under `_create_lock` (double-checked locking), create a new instance if pool is not full.
  3. Wait path: If pool is saturated, poll every 500ms up to 30s for an available instance.
- **Health check loop**: Every 30s, each instance is verified by navigating to `about:blank`. Unhealthy instances are removed and replaced to maintain `browser_pool_min`.
- **Release with backpressure**: Instances are destroyed immediately if unhealthy or at max uses, otherwise returned to the pool for reuse.

### Recommendations

- **Scrape-heavy workloads**: Increase `browser_pool_max` to 20–30 and `browser_pool_health_check_seconds` to 15 for faster failure detection. Monitor memory usage — each Chromium instance uses ~100–200 MB.
- **Memory-constrained environments**: Reduce `browser_pool_max` to 5 and increase `browser_pool_idle_timeout_seconds` to 600.
- **High-reliability needs**: Set `browser_pool_min` equal to `browser_pool_max` to avoid launch latency during load spikes (at the cost of constant resource usage).

## Queue Performance

### Priority Levels

The queue system (in `backend/app/worker/queue.py`) uses separate Redis lists per priority:

| Queue | Redis Key | Purpose |
|---|---|---|
| `critical` | `queue:critical` | Urgent jobs (blocking user actions) |
| `high` | `queue:high` | Important extraction jobs |
| `default` | `queue:default` | Standard scrape jobs |
| `low` | `queue:low` | Bulk/batch processing |
| `retry` | `queue:retry` | Jobs awaiting retry |
| `scheduled` | `queue:scheduled` | Delayed/future jobs (Redis sorted set) |
| `dead_letter` | `queue:dead_letter` | Failed jobs exceeding max retries |

Dequeue order: `critical` > `high` > `default` > `low` > `retry`. Scheduled jobs (stored in a Redis sorted set by timestamp) are checked first on each dequeue.

### Retry Backoff

```python
delay = queue_retry_delay_seconds * (queue_retry_backoff_multiplier ** (retry_count - 1))
```

Default: `60 * (2.0 ** (retry - 1))` → retry 1: 60s, retry 2: 120s, retry 3: 240s.

Maximum retries is configured via `queue_max_retries` (default: 3). After exhausting retries, the job is sent to the dead-letter queue via `_send_to_dead_letter`.

### Performance Characteristics

- **Enqueue**: O(1) Redis `LPUSH` (or `ZADD` for scheduled jobs). Sub-millisecond for typical payloads.
- **Dequeue**: O(N) where N = number of priority queues checked (5). Uses `BRPOP` with 1s timeout per queue.
- **Bottleneck**: Sequential priority scanning. Under very high throughput (>1000 jobs/s), the single-threaded dequeue could become a bottleneck. Consider using Redis Lua scripts for atomic multi-queue blocking pop.

## Proxy Performance

### Pool Architecture

The `ProxyManager` maintains an in-memory pool of proxy dictionaries, refreshed from the database:

- **Loading**: On startup and periodic refresh, active proxies are loaded via `select(Proxy).where(Proxy.status == ProxyStatus.ACTIVE)`.
- **Pool lock**: `_pool_lock` protects the in-memory list during concurrent reads and writes.
- **Reload deduplication**: `_reload_lock` prevents concurrent reload operations.

### Health Checks

The `ProxyChecker` runs batch health checks every `proxy_check_interval_seconds` (default: 300s):

- **Concurrent checking**: Uses `asyncio.Semaphore(concurrency=20)` to limit simultaneous checks.
- **Check mechanism**: Makes a GET request to `proxy_check_url` (default: `https://httpbin.org/ip`) through each proxy.
- **Alive detection**: Response status 200 + JSON parsing = alive. Latency is measured and stored.
- **Failure accumulation**: Each failed check increments `consecutive_failures`. When `consecutive_failures >= proxy_max_failures` (default: 3), status is set to `INACTIVE`.
- **Deduplication**: In-flight checks are tracked in `_checking` dict to prevent duplicate concurrent checks of the same proxy.

### Scoring and Selection

The `ProxyRotator` provides three selection algorithms:

1. **Round-robin** (`get_next`): Sequential rotation with shuffle every 60s. Simple distribution.
2. **Weighted random** (`get_weighted`): Selection probability proportional to `weight` field. Higher weight = more requests.
3. **Country-based** (`get_by_country`): Filters pool by country code and returns a random match.

The `ProxyManager.get_proxy()` uses `get_weighted()` by default, falling back to `random.choice()` if no rotator is available.

### Recommendations

- **Large proxy pools (>100)**: Increase `proxy_check_interval_seconds` to 600 to reduce database load during health checks.
- **Low-latency requirements**: Set `proxy_check_timeout_seconds` to 5 for faster failure detection.
- **Aggressive rotation**: Decrease `proxy_max_failures` to 2, `proxy_ban_threshold` to 3.
- **The checker uses `verify=False`** on SSL — acceptable for proxy verification but should be reviewed for security requirements.

## Caching Strategy

DataForge AI uses a dedicated Redis database (db 2) for caching, separate from the queue (db 1) and default (db 0).

### Cache Layer Configuration

In `backend/app/core/redis.py`:

```python
_cache_client = await aioredis.from_url(
    str(settings.redis_cache_url),   # redis://localhost:6379/2
    socket_timeout=5,
    socket_connect_timeout=5,
    retry_on_timeout=True,
    health_check_interval=30,
)
```

- **Separate Redis DB**: Cache is isolated from queue data to prevent cache evictions from affecting job processing.
- **Timeouts**: 5s socket timeout prevents cascading failures when Redis is slow.
- **Health checks**: Automatic health checks every 30s detect stale connections.
- **Retry on timeout**: Transient network issues are retried automatically.

### Current Cache Usage

The cache client is available via `get_cache_redis()` and ready for use-cases such as:

- Page content caching (avoid re-scraping identical URLs within a TTL window)
- LLM response caching (deduplicate extraction results for identical inputs)
- Proxy check result caching (reduce redundant health checks)
- Session/cache for API rate limiting

## Prometheus Metrics for Performance Monitoring

Exposed at the `/metrics` endpoint (enabled via `prometheus_enabled: true`).

### Key Metrics to Watch

| Metric | Type | What It Reveals |
|---|---|---|
| `dataforge_job_duration_seconds` | Histogram | Job latency distribution. Watch p95/p99 for slow jobs. Buckets: 1s–3600s. |
| `dataforge_jobs_active` | Gauge | Current concurrent jobs. If saturated, increase worker count or queue capacity. |
| `dataforge_scrape_duration_seconds` | Histogram | Per-page scrape latency. Buckets: 0.5s–120s. Spikes indicate proxy/browser issues. |
| `dataforge_browser_pool_size{status="healthy"}` | Gauge | Healthy vs total browsers. Gap indicates browser crashes or health check failures. |
| `dataforge_browser_launches_total` | Counter | Browser launch frequency. High rate suggests pool churn; increase `max_uses_per_context`. |
| `dataforge_proxy_active` | Gauge | Usable proxies. A downward trend indicates proxies burning out faster than checks. |
| `dataforge_proxy_requests_total` | Counter | Request success/failure ratio. High failure rate indicates proxy quality issues. |
| `dataforge_queue_depth` | Gauge | Backlog per queue. Growing depth indicates workers can't keep up. |
| `dataforge_queue_processed_total` | Counter | Dead-letter rate signals jobs failing permanently — investigate job config or proxy health. |
| `dataforge_cpu_usage_percent` | Gauge | System CPU. High CPU + low throughput suggests bottleneck in page processing. |
| `dataforge_memory_usage_bytes` | Gauge | Memory growth over time — potential memory leak in browser contexts. |
| `dataforge_active_workers` | Gauge | Should match expected worker count. Fewer workers than expected indicates crashes. |
| `dataforge_extraction_tokens_total` | Counter | LLM token consumption. Correlate with cost and extraction quality. |

### Recommended Alerts

- `dataforge_queue_depth{queue="critical"}` > 100 for > 5 minutes
- `dataforge_browser_pool_size{status="healthy"}` < `browser_pool_min` for > 1 minute
- `dataforge_proxy_requests_total{status="failed"}` / `dataforge_proxy_requests_total{status="success"}` > 0.5 over 5 minutes
- `dataforge_jobs_active` == `queue_max_concurrent_jobs` for > 2 minutes

## Benchmarking Guidelines

### How to Test

```bash
# Synthetic load test with locust
pip install locust
locust -f tests/load/locustfile.py --headless -u 50 -r 10 --run-time 5m

# Individual component benchmarks
python -m tests.benchmark.queue --messages 10000 --workers 10
python -m tests.benchmark.proxy --pool-size 50 --checks 500
python -m tests.benchmark.browser --concurrent 5 --pages 50
```

### What to Measure

| Component | Metric | Target |
|---|---|---|
| Queue throughput | Jobs enqueued/dequeued per second | > 1000/s |
| Proxy health check | Checks per second (batch) | > 50/s with concurrency=20 |
| Browser launch | Time to first usable browser | < 5s (cold), < 1s (warm) |
| Page scrape | End-to-end latency p50/p95/p99 | < 3s / < 10s / < 30s |
| Database pool | Connection acquisition time | < 5ms |
| API response | Request latency (non-scrape) | < 100ms p95 |

### Test Environment Requirements

- Isolate benchmark from production traffic.
- Use dedicated Postgres and Redis instances (not shared).
- Record system metrics (CPU, memory, network) alongside application metrics.
- Run minimum 3 iterations of each benchmark to account for variance.
- Test with realistic page sizes (100KB–2MB HTML).
- Include proxy latency variance in scrape benchmarks.

## Bottleneck Identification

### Database

- **Multiple session invocations in `_process_job`**: Each job opens 5+ separate database sessions (run creation, job update, run update, result save, final update). Under load, this multiplies connection pool contention. **Fix**: Combine related operations into fewer sessions or use a unit-of-work pattern.
- **Sequential proxy updates**: Each proxy failure/success opens a separate session with `select` + `commit`. At high request volume, batch these updates.
- **`pool_pre_ping` overhead**: Adds ~1ms per connection checkout. Acceptable for latency-insensitive batch jobs but may be removed for latency-critical paths.

### Browser Pool

- **Synchronous `_warm_pool` during startup**: Browser launch is sequential in the warming loop. For large `browser_pool_min`, launch browsers concurrently with `asyncio.gather`.
- **No active idle eviction**: `_check_health` only checks health, not idle time. Idle browsers consume memory until they naturally hit `max_uses_per_context`. Add an idle-eviction sweep.

### Queue

- **Sequential `BRPOP` with 1s timeout per priority level**: Dequeue could stall up to 5 seconds in worst case if all queues are empty. Use a single `BLPOP` with multiple keys, or a Lua script for atomic priority pop.
- **No batching**: Each job is dequeued and processed individually. For bulk operations, consider batch dequeue.

### Proxy

- **In-memory pool staleness**: Pool is refreshed on health checks (every 300s) and explicit reload. Between checks, proxy state in memory may diverge from database. Reduce check interval for faster convergence.
- **No circuit breaker for checker endpoint**: If `proxy_check_url` is slow, all checks block. Add a timeout or fallback check URL.

## Configuration Tuning Guide

### Database

```yaml
database_pool_size: 20          # Recommendation: 2-4x worker count (default: 20)
database_max_overflow: 10       # Recommendation: 50% of pool_size (default: 10)
# pool_recycle: 3600            # Fixed at 3600s. Lower to 600s if connections are short-lived.
```

### Browser Pool

```yaml
browser_pool_min: 2             # Recommendation: 2-5 (default: 2)
browser_pool_max: 10            # Recommendation: 5-30 depending on RAM (default: 10)
                                # Formula: available_GB * 5 (each browser ~200MB)
browser_pool_idle_timeout_seconds: 300  # Recommendation: 60-600 (default: 300)
                                         # Lower = faster cleanup, higher = less churn
browser_pool_health_check_seconds: 30    # Recommendation: 15-60 (default: 30)
browser_pool_max_uses_per_context: 50    # Recommendation: 20-100 (default: 50)
                                         # Lower = more reliable, higher = less overhead
```

### Queue

```yaml
queue_max_retries: 3            # Recommendation: 3-5 (default: 3)
queue_retry_delay_seconds: 60   # Recommendation: 30-120 (default: 60)
queue_retry_backoff_multiplier: 2.0  # Recommendation: 1.5-3.0 (default: 2.0)
queue_max_concurrent_jobs: 20   # Recommendation: equal to browser_pool_max (default: 20)
queue_result_ttl: 86400         # Recommendation: 3600-604800 (default: 86400 = 24h)
queue_default_priority: 5       # Recommendation: 1-10, lower = higher priority
```

### Proxy

```yaml
proxy_pool_size: 50             # Recommendation: 20-200 (default: 50)
proxy_check_interval_seconds: 300  # Recommendation: 60-600 (default: 300)
proxy_check_timeout_seconds: 10    # Recommendation: 5-15 (default: 10)
proxy_max_failures: 3           # Recommendation: 2-5 (default: 3)
proxy_ban_threshold: 5          # Recommendation: 3-10 (default: 5)
```

### Rate Limiting

```yaml
rate_limit_requests_per_second: 10  # Recommendation: 5-50 (default: 10)
rate_limit_burst_size: 20          # Recommendation: 2x requests_per_second (default: 20)
```

### General

```yaml
api_workers: 4                  # Recommendation: 2-8 (default: 4)
                                # Formula: 2 * CPU cores for I/O-bound workloads
debug: false                    # Must be false in production
log_level: INFO                 # Use WARN in high-throughput production to reduce I/O
```
