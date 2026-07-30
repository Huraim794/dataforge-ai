# Troubleshooting Guide

## Common Issues and Solutions

### Database Connection Failures

**Symptoms**: `could not connect to server`, `Connection refused`, jobs stuck in `PENDING` state.

**Causes and solutions**:
- PostgreSQL is not running. Verify with `pg_isready` or check service status.
- Connection string is wrong. The default is `postgresql+asyncpg://dataforge:dataforge@localhost:5432/dataforge`. Check `DATABASE_URL` in your `.env` file.
- Pool exhausted. Default pool size is 20 with overflow of 10. Reduce concurrent jobs or increase `database_pool_size`.
- Connection timeout. Ensure PostgreSQL allows connections from the application host (check `pg_hba.conf`).

**Verification**:
```python
from dataforge.backend.app.core.database import check_database_health
await check_database_health()  # returns True/False
```

### Redis Connection Issues

**Symptoms**: `Error 111 connecting to localhost:6379`, queue jobs not being processed.

**Causes and solutions**:
- Redis server is not running. Start with `redis-server` or check system service.
- Wrong Redis URL. Check `REDIS_URL`, `REDIS_QUEUE_URL`, `REDIS_CACHE_URL` in `.env`. The defaults use databases 0, 1, and 2.
- Timeout. Socket timeout is 5 seconds; ensure network connectivity.
- Authentication required. Append `?password=...` to the Redis URL if ACL/requirepass is configured.

**Verification**:
```python
from dataforge.backend.app.core.redis import check_redis_health
await check_redis_health()  # returns True/False
```

### Browser Launch Failures

**Symptoms**: `Browser launch timed out after 30s`, `Playwright not started`.

**Causes and solutions**:
- Playwright browsers not installed. Run `playwright install chromium` in the backend environment.
- Insufficient memory. Each browser instance uses ~200–400 MB. Reduce `browser_pool_max` or add RAM.
- Missing system dependencies. On Linux, run `playwright install-deps chromium`.
- Docker sandbox issues. The default launch args include `--disable-setuid-sandbox` and `--disable-dev-shm-usage` specifically for containerized environments.
- Headless mode disabled in production (`browser_headless: false`) may fail without a display server.

### Proxy Pool Empty

**Symptoms**: `No usable proxies available` in logs, all scrapes fail with proxy-related errors.

**Causes and solutions**:
- No proxies added to the database. Add proxies via the API or directly to the `proxies` table.
- All proxies marked `INACTIVE` or `BANNED`. The health checker runs every `proxy_check_interval_seconds` (300s) and reassigns `ACTIVE` status if proxies recover. Check `proxy_max_failures` (default 3) — consecutive failures deactivate proxies quickly.
- All proxies have `score <= 0.3`. Scores are reduced by failures; reset scores if needed.
- `proxy_check_url` is unreachable. The default `https://httpbin.org/ip` may be blocked in some regions. Set a different check URL.

### LLM API Errors

**Symptoms**: `AI extraction failed: 401 Unauthorized`, `429 Too Many Requests`, `Insufficient quota`.

**Causes and solutions**:
- Missing or invalid API key. Set `LLM_API_KEY` in `.env`.
- Rate limited. Reduce `queue_max_concurrent_jobs` or increase `llm_max_tokens` timeout (default 120s).
- Quota exhausted. Check your OpenAI/Anthropic/Google Cloud billing dashboard.
- Unsupported model. Ensure `llm_model` matches one of the configured models for the provider.
- Content too long. Content is truncated at 100,000 characters before submission.

### CAPTCHA Solving Failures

**Symptoms**: `CAPTCHA detected` but no token returned, `CAPTCHA solve timeout`.

**Causes and solutions**:
- `captcha_auto_solve` is `False` (default). Enable it and provide `captcha_service_api_key`.
- 2Captcha API key is invalid or has insufficient balance.
- Site key detection failed. The CAPTCHA widget may use a non-standard selector or be inside an iframe.
- Solve timeout. Default polling is 30 attempts × 5 seconds = 150 seconds. Increase `captcha_timeout_seconds`.
- CAPTCHA type is reCAPTCHA v3 (invisible) — detected but not solved, which is expected.

### Queue Backlog

**Symptoms**: High queue depth (`dataforge_queue_depth` Prometheus metric), jobs stuck for minutes.

**Causes and solutions**:
- Not enough workers. Increase the number of `TaskProcessor` instances or worker processes.
- Workers are too slow. Check `dataforge_scrape_duration_seconds` histogram — slow scrapes bottleneck the queue.
- Retry storm. Exponential backoff starts at `queue_retry_delay_seconds` (60s) and doubles. A large batch of failing jobs can flood the retry queue. Check `queue:retry` length and inspect dead-letter queue (`queue:dead_letter`).
- Redis memory limit reached. Monitor Redis `maxmemory` and eviction policy.

### Worker Crashes

**Symptoms**: Worker processes exit unexpectedly, `dataforge_active_workers` drops to 0.

**Causes and solutions**:
- Unhandled exception in task processing. The `TaskProcessor._process_job` wraps the entire execution in a try/except that logs errors and requeues the job, but crashes in the event loop itself (e.g. segfaults from Playwright) are fatal.
- Out of memory. Browser instances are the largest memory consumer. Set a limit with `browser_pool_max` and restart workers with `--max-old-space-size` or equivalent.
- If using multiple workers, ensure they share the same Redis instance and database. Each worker gets a unique `_worker_id`.

### Memory Leaks

**Symptoms**: RAM usage grows over time, `dataforge_memory_usage_bytes` increases without bound.

**Causes and solutions**:
- Browser instances not released. Each `acquire()` must be paired with a `release()`. The `ScrapingEngine` uses `try/finally` to guarantee release, but if your code bypasses the engine, ensure proper cleanup.
- `browser_pool_max_uses_per_context` (default 50) is too high. Reduce to recycle contexts more frequently.
- Contexts accumulate cookies and localStorage. The browser pool does not clear storage between uses — consider reducing max uses or clearing storage on release.
- Python-side leaks. Use `tracemalloc` to track allocations. Enable `objgraph` or `gc` debugging in development.

## Debugging Tools

### Health Check Endpoints

Two health check functions verify infrastructure dependencies:

```python
await check_database_health()  # SELECT 1
await check_redis_health()     # PING
```

### Logging Configuration

Logs are written as JSON to stdout by default. The `JsonFormatter` includes:

```json
{
  "timestamp": "2025-01-15T10:30:00.123456+00:00",
  "level": "ERROR",
  "logger": "dataforge.app.scraping.engine",
  "message": "Scrape attempt 1 failed for https://example.com",
  "module": "engine",
  "function": "scrape",
  "line": 213,
  "correlation_id": "a1b2c3d4-...",
  "error": "Connection refused",
  "error_type": "ConnectionRefusedError",
  "attempt": 1,
  "url": "https://example.com"
}
```

Set `log_level` to `DEBUG` for verbose output. Optionally write to a file with `log_file` setting.

### Prometheus Metrics for Diagnosis

All metrics are available at the `/metrics` Prometheus endpoint (enabled by default with `prometheus_enabled: true`).

| Metric | Type | Use for |
|---|---|---|
| `dataforge_jobs_active` | Gauge | Current concurrency level |
| `dataforge_job_duration_seconds` | Histogram | Job latency distribution |
| `dataforge_scrape_duration_seconds` | Histogram | Per-scrape latency |
| `dataforge_browser_pool_size{status="healthy"}` | Gauge | Available browser instances |
| `dataforge_browser_pool_size{status="total"}` | Gauge | Total browser instances |
| `dataforge_proxy_active{status="active"}` | Gauge | Usable proxies count |
| `dataforge_queue_depth{queue="..."}` | Gauge | Backlog per queue |
| `dataforge_errors_total{type="..."}` | Counter | Error frequency by type |
| `dataforge_captcha_detected_total` | Counter | CAPTCHA encounter rate |
| `dataforge_captcha_solved_total` | Counter | CAPTCHA solve rate |
| `dataforge_cpu_usage_percent` | Gauge | System CPU |
| `dataforge_memory_usage_bytes` | Gauge | System memory |
| `dataforge_active_workers` | Gauge | Running worker count |

Diagnosis flow:
1. If jobs are failing, check `dataforge_errors_total` to identify the most common error type.
2. If scrapes are slow, inspect `dataforge_scrape_duration_seconds` and `dataforge_proxy_active`.
3. If workers are idle, check `dataforge_queue_depth` — empty queues mean no work; non-empty queues with idle workers indicate worker starvation.
4. If browsers crash, check `dataforge_browser_pool_size{status="healthy"}` dropping below `browser_pool_min`.
