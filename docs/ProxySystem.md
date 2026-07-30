# Proxy System

## System Overview

The proxy system consists of three components that work together to manage, verify, and rotate proxies:

- **`ProxyManager`** — owns the in-memory proxy pool, loads proxies from the database, coordinates periodic health checks, and reports success/failure per-proxy.
- **`ProxyChecker`** — performs liveness and latency verification against a configurable check URL (default: `https://httpbin.org/ip`).
- **`ProxyRotator`** — implements selection algorithms (round-robin, random, weighted random, country-specific) over the active proxy pool.

## Proxy Model Fields

The `Proxy` SQLAlchemy model (`app/models/proxy.py`) stores all proxy state:

| Field | Type | Description |
|---|---|---|
| `host` | `str` | Proxy hostname or IP |
| `port` | `int` | Proxy port |
| `protocol` | `enum` | `http`, `https`, `socks4`, `socks5` |
| `username` | `Optional[str]` | Authentication username |
| `password` | `Optional[str]` | Authentication password |
| `status` | `enum` | `active`, `inactive`, `banned`, `checking`, `rate_limited`, `error` |
| `latency_ms` | `Optional[float]` | Last measured latency in milliseconds |
| `success_count` | `int` | Total successful requests |
| `failure_count` | `int` | Total failed requests |
| `consecutive_failures` | `int` | Consecutive failure counter |
| `ban_count` | `int` | Number of times banned |
| `total_requests` | `int` | Total requests made |
| `country` | `Optional[str]` | Geo-located country |
| `region` | `Optional[str]` | Geo-located region |
| `city` | `Optional[str]` | Geo-located city |
| `isp` | `Optional[str]` | ISP name |
| `anonymity_level` | `Optional[str]` | Anonymity level (e.g. "elite", "anonymous") |
| `weight` | `float` | Selection weight (default 1.0) |
| `score` | `float` | Composite health score (default 1.0) |
| `requests_per_minute` | `int` | Rate limit per minute (default 30) |
| `last_checked_at` | `datetime` | Last health check timestamp |
| `last_used_at` | `datetime` | Last usage timestamp |

The `url` property builds a connection string (e.g. `http://user:pass@host:port`). The `is_usable` property returns `True` only when all conditions are met: status is `ACTIVE`, consecutive failures < 3, ban count < 5, and score > 0.3.

## Proxy Pool Lifecycle

### Loading

On `ProxyManager.start()`, active proxies are loaded from the database:

```python
await self._load_proxies()
```

This queries all proxies with `status = ACTIVE` and builds an in-memory pool. A `ProxyRotator` is initialized if the pool is non-empty.

### Health Checks

A background task (`_periodic_check`) runs every `proxy_check_interval_seconds` (default 300). It queries both `ACTIVE` and `INACTIVE` proxies and submits them to the checker in batches with concurrency of 20:

```python
results = await self.checker.check_proxy_batch(batch, concurrency=20)
```

For each proxy:
- **Alive**: status set to `ACTIVE`, latency and country updated.
- **Dead**: `consecutive_failures` incremented. If it reaches `proxy_max_failures` (default 3), status becomes `INACTIVE`.

After check completion, the in-memory pool is reloaded via `_reload_pool()`.

### Scoring

Scores are stored on the model but adjusted via external logic. A proxy with `score <= 0.3` is excluded from selection.

## Selection Algorithm

`ProxyRotator.get_weighted()` implements a weighted random selection:

1. Build a list of weights from each proxy's `weight` field.
2. Compute the total weight sum.
3. Pick a random value in `[0, total)`.
4. Iterate through proxies, accumulating weight until the random value is reached.

```python
weights = [p.get("weight", 1.0) for p in self._proxies]
total = sum(weights)
r = random.uniform(0, total)
for proxy, weight in zip(self._proxies, weights):
    cumulative += weight
    if r <= cumulative:
        return proxy
```

Additional selection methods:
- `get_next()` — round-robin with periodic shuffle every 60 seconds.
- `get_random()` — uniform random choice.
- `get_by_country(country)` — random from proxies matching a country code.

## Failure Handling

### Consecutive Failures

When a scrape fails, `ProxyManager.report_failure(proxy_id)` is called:

```python
proxy.consecutive_failures += 1
if proxy.consecutive_failures >= settings.proxy_max_failures:
    proxy.status = ProxyStatus.INACTIVE
```

### Success Recovery

On successful scrape, `report_success(proxy_id)` resets `consecutive_failures` to 0 and reactivates an inactive proxy:

```python
proxy.success_count += 1
proxy.consecutive_failures = 0
if proxy.status == ProxyStatus.INACTIVE:
    proxy.status = ProxyStatus.ACTIVE
```

### Ban Tracking

The model tracks `ban_count` and `last_banned_at` but banning logic is external — a proxy with `ban_count >= 5` is excluded by `is_usable`.

## Proxy Checker

The `ProxyChecker` tests each proxy by making an HTTP GET to `proxy_check_url` (default `https://httpbin.org/ip`):

| Outcome | Result |
|---|---|
| HTTP 200 with valid JSON | `alive: true`, `latency_ms`, `ip`, `country` |
| HTTP 200 with non-JSON | `alive: true`, `latency_ms` |
| Connection error | `alive: false`, `error: "connection_failed"` |
| Timeout | `alive: false`, `error: "timeout"` |

Deduplication is enforced via an in-flight `_checking` dict to avoid concurrent checks for the same proxy.

## Configuration Reference

| Setting | Default | Description |
|---|---|---|
| `proxy_pool_size` | `50` | Maximum proxy pool size |
| `proxy_check_interval_seconds` | `300` | Health check frequency |
| `proxy_check_timeout_seconds` | `10` | Per-proxy timeout during check |
| `proxy_max_failures` | `3` | Consecutive failures before deactivation |
| `proxy_ban_threshold` | `5` | Ban count threshold |
| `proxy_check_url` | `https://httpbin.org/ip` | Endpoint for liveness verification |
