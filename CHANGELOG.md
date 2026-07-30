# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-15

### Added

- **Authentication & User Management**: JWT-based authentication with access and refresh tokens. Bcrypt password hashing. API key authentication with SHA-256 hashed key storage. Role-based access control (admin, user, viewer). User registration, login, and profile management.
- **Project System**: Multi-project workspaces with member roles (owner, admin, member). Per-project resource isolation for targets, jobs, schedules, and proxies.
- **Target Configuration**: CRUD for scrape targets with configurable JavaScript execution, wait selectors, custom headers/cookies, viewport, user agent, screenshots, PDF capture, and extraction schemas.
- **Scraping Engine**: Headless browser-based scraping via Playwright. Configurable browser pool with health checks, idle timeout, and reuse limits. Anti-bot evasion scripts and randomized timing. CAPTCHA detection and auto-solving via 2Captcha integration. Configurable retry with exponential backoff and proxy rotation.
- **Proxy Management**: Dynamic proxy pool with automatic health checking, latency measurement, and scoring. Weighted round-robin rotation. Automatic deactivation of failing proxies after configurable failure thresholds.
- **AI-Powered Extraction**: LLM-based extraction supporting OpenAI (GPT-4o, GPT-4, GPT-3.5), Google Gemini (Pro, 1.5 Pro, 1.5 Flash), Anthropic Claude (Opus, Sonnet, Haiku), and DeepSeek (Chat, Coder). Structured extraction with JSON schemas, custom prompt templates, and field definitions. Specialized extractors for contacts, tables, and content classification. Confidence scoring based on schema field coverage.
- **Job Queue System**: Priority-based job queue (critical, high, default, low, retry, dead letter) backed by Redis. Automatic retry with exponential backoff. Delayed/scheduled job enqueueing. Dead letter queue for failed jobs.
- **Job Scheduling**: APScheduler integration with 13 predefined intervals (every minute through monthly) and custom cron expressions. Per-schedule max run limits with auto-deactivation. Notification configuration for failure alerts.
- **Worker Infrastructure**: Background worker loop with concurrent processing. Full job lifecycle tracking with run records. Metrics collection for all job stages.
- **Monitoring & Observability**: Prometheus metrics endpoint exposing job/scrape/extraction/proxy/queue/browser pool/CAPTCHA metrics. Structured JSON logging. Sentry error tracking integration. CPU and memory usage monitoring via psutil.
- **Rate Limiting**: Redis-based sliding window rate limiter. Per-API-key, per-token, and per-IP rate limiting. Configurable requests-per-second and burst size.
- **Admin Dashboard**: React 18 + TypeScript frontend with TailwindCSS. Pages for dashboard overview, jobs (with detail view), proxies, schedules, targets, extractions, projects, and settings. Recharts-based visualizations. Lucide React icons.
- **API Infrastructure**: FastAPI application with CORS middleware, global error handlers, health check endpoint, and Prometheus metrics mount. PostgreSQL via SQLAlchemy async with connection pooling. Redis client for queue, caching, and rate limiting.
- **Containerization**: Docker Compose setup with PostgreSQL 16, Redis 7, API server, worker (configurable replicas), and Nginx reverse proxy. Health checks on all services.

### Changed

- N/A (initial release)

### Fixed

- N/A (initial release)

### Security

- Passwords hashed with bcrypt before storage.
- API keys hashed with SHA-256 before storage; raw key shown only once at creation.
- JWT tokens signed with configurable secret key; production deployment enforces strong secret validation.
- CORS restricted to configured allowed origins.
- Rate limiting applied to authentication endpoints (login) and general API usage.
- Role-based access control enforced at endpoint level via dependency injection.
- Project-level access verification on all project-scoped resources.

### Previous versions

See git history for earlier development iterations.

[1.0.0]: https://github.com/dataforge-ai/dataforge/releases/tag/v1.0.0
