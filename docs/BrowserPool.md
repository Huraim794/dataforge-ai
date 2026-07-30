# Browser Pool

## Purpose and Design Rationale

The `BrowserPool` manages a pool of reusable Playwright browser contexts to avoid the overhead of launching a new browser process for every scrape. It maintains a configurable number of warm browser instances, performs periodic health checks, and automatically recycles instances that exceed usage limits or become unhealthy.

The pool uses two locks to control concurrency: a fast `_lock` for brief acquisitions and a `_create_lock` to prevent overshooting the pool maximum when creating new instances under load.

## BrowserInstance

The `BrowserInstance` dataclass wraps a Playwright `Browser` and `BrowserContext` along with metadata:

| Field | Type | Description |
|---|---|---|
| `browser` | `Browser` | Playwright browser instance |
| `browser_type` | `str` | Type of browser (e.g. "chromium") |
| `context` | `BrowserContext` | Isolated browser context with session state |
| `created_at` | `float` | Unix timestamp of creation |
| `last_used_at` | `float` | Unix timestamp of last use |
| `use_count` | `int` | Number of times acquired |
| `is_healthy` | `bool` | Health status flag |
| `proxy_url` | `Optional[str]` | Proxy URL associated with this instance |
| `user_agent` | `Optional[str]` | Custom user agent |

## BrowserContext Lifecycle

### 1. Warm-up (`start`)

On startup `BrowserPool.start()` launches Playwright and creates the minimum number of browser instances to fill the pool:

```python
await self._warm_pool()
```

### 2. Acquire (`acquire`)

When a scrape requires a browser:

1. **Fast path** — scan the pool under a brief lock for a healthy instance that hasn't exceeded `_max_uses` and matches the requested proxy.
2. **Creation path** — if no instance found, acquire the `_create_lock`, double-check the pool, and create a new instance if under `_max_size`.
3. **Wait path** — if the pool is full, block for up to 30 seconds waiting for an instance to be released.

```python
instance = await browser_pool.acquire(proxy=proxy_config)
instance.use_count += 1
```

### 3. Use

The caller performs page navigation, content extraction, and any other operations. The instance remains exclusively held.

### 4. Release (`release`)

After use the caller returns the instance:

```python
await browser_pool.release(instance, healthy=result["success"])
```

If the instance is unhealthy or has exceeded `_max_uses`, the underlying browser and context are closed and the instance is removed from the pool.

## Anti-Bot Evasion

The `AntiBotDetector` provides evasion techniques injected into every page via `add_init_script`:

### User-Agent Rotation

A random user agent is selected from a pool of modern Chrome, Firefox, and Safari strings (Windows, macOS, Linux).

### Viewport Randomization

Random viewport dimensions from common screen resolutions (1920×1080, 1366×768, 1536×864, 1440×900, 1280×720, 2560×1440).

### Locale & Timezone

Browser contexts are configured with random locale (`en-US`, `en-GB`, `en-CA`, `en-AU`, `en-IN`) and timezone (e.g. `America/New_York`, `Europe/London`, `Asia/Tokyo`).

### WebDriver Override

The evasion script overrides `navigator.webdriver` to return `false` and patches `navigator.plugins`, `navigator.languages`, `window.chrome`, and `navigator.permissions.query`:

```javascript
Object.defineProperty(navigator, 'webdriver', { get: () => false });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { runtime: {} };
```

### Human-like Delays

A random delay between 1–3 seconds is applied before navigation to simulate human behavior.

## CAPTCHA Handling

### Detection

The `CAPTCHAHandler.detect_captcha` method scans the page for known CAPTCHA widgets by CSS selector:

| CAPTCHA Type | Selector |
|---|---|
| reCAPTCHA v2 | `.g-recaptcha` with `data-sitekey` |
| reCAPTCHA v3 | `[data-callback]` with `data-sitekey` |
| hCaptcha | `.h-captcha` with `data-sitekey` |
| Cloudflare Turnstile | `.cf-turnstile` with `data-sitekey` |

The `AntiBotDetector.check_page` method additionally scans page content for regex patterns matching `recaptcha`, `hcaptcha`, `turnstile`, `challenge-platform`, challenge iframes, and Cloudflare identifiers.

### Solving

When `captcha_auto_solve` is enabled and an API key is configured, the system submits CAPTCHAs to the 2Captcha service (`api.2captcha.com`).

- **reCAPTCHA v2 / hCaptcha / Turnstile**: submitted via `/in.php` with method `userrecaptcha` / `hcaptcha` / `turnstile`. Polls `/res.php` every 5 seconds for up to 30 polls. On success, the token is injected into the page via `g-recaptcha-response`.
- **reCAPTCHA v3**: detected but not solved (invisible, no user action required).
- **Image CAPTCHAs**: captured via screenshot or fetch, submitted as base64 via method `base64`.

Detection and solving results are tracked via `captcha_detected` and `captcha_solved` Prometheus counters.

## Configuration Reference

All browser-related settings are in `Settings` (`app/core/config.py`):

| Setting | Default | Description |
|---|---|---|
| `browser_pool_min` | `2` | Minimum browser instances to keep warm |
| `browser_pool_max` | `10` | Maximum browser instances in pool |
| `browser_pool_idle_timeout_seconds` | `300` | Idle timeout before recycling |
| `browser_pool_health_check_seconds` | `30` | Interval between health checks |
| `browser_pool_max_uses_per_context` | `50` | Max uses before context is recycled |
| `browser_headless` | `True` | Run browsers in headless mode |
| `browser_viewport_width` | `1920` | Default viewport width |
| `browser_viewport_height` | `1080` | Default viewport height |
| `browser_launch_args` | `["--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]` | Chromium launch arguments |
| `default_timeout_ms` | `30000` | Default navigation timeout |
| `captcha_service_api_key` | `None` | 2Captcha API key |
| `captcha_service_url` | `https://api.2captcha.com` | 2Captcha endpoint |
| `captcha_auto_solve` | `False` | Enable automatic CAPTCHA solving |
| `captcha_timeout_seconds` | `120` | CAPTCHA solve timeout |

## Performance Considerations

- **Pool sizing**: `browser_pool_min` should match the expected concurrent scrape volume. Each browser instance consumes ~200–400 MB of RAM. On a typical server with 8 GB RAM, keep the pool under 10–15 instances.
- **Context reuse**: Each `BrowserInstance` is recycled after `browser_pool_max_uses_per_context` (default 50) to prevent memory leaks from accumulated page state.
- **Health checks**: Run every 30 seconds by default. Each check opens and closes a page on `about:blank` — tune the interval higher for larger pools to avoid overhead.
- **Headless mode**: Always `True` in production. Disabling headless increases resource consumption and is only useful for visual debugging.
- **Launch args**: `--disable-dev-shm-usage` prevents `/dev/shm` crashes in Docker; `--disable-gpu` avoids GPU rendering issues on servers.
