# API Reference

**Base URL:** `http://localhost:8000/api/v1`

All endpoints are prefixed with `/api/v1`. Authentication uses either:
- Bearer JWT token (`Authorization: Bearer <token>`)
- API key (`X-API-Key: df_<key>`)

---

## Error Response Format

```json
{"error": "VALIDATION_ERROR", "message": "...", "details": {}}
```

| Status | Code | Description |
|--------|------|-------------|
| 400 | `VALIDATION_ERROR` | Invalid request |
| 401 | `AUTH_ERROR` | Invalid credentials |
| 403 | `FORBIDDEN` | Insufficient permissions |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | — | Duplicate resource |
| 429 | `RATE_LIMIT` | Rate limit exceeded |

---

## Authentication

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | None | Email + password login, returns `{access_token, refresh_token, expires_in}` |
| POST | `/auth/register` | None | Create account (`email`, `password` min 8 chars, `full_name`, `company`) |
| POST | `/auth/refresh` | None | Exchange refresh token for new access + refresh pair |
| GET | `/auth/me` | Bearer/API | Current user profile |
| POST | `/auth/api-keys` | Bearer | Create API key (`name` query param) |
| GET | `/auth/api-keys` | Bearer | List API keys for current user |
| DELETE | `/auth/api-keys/{id}` | Bearer | Delete API key |

---

## Users

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/users` | Admin | List all users |
| GET | `/users/me` | Bearer/API | Current user profile |
| PATCH | `/users/me` | Bearer/API | Update profile (`full_name`, `company`, `title`, `preferences`) |

---

## Projects

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/projects` | Bearer | Create project (`name`, `description`, `settings`). Creator becomes `owner`. |
| GET | `/projects` | Bearer/API | List projects where user is a member |
| GET | `/projects/{id}` | Project member | Project detail with member/target/job counts |
| PATCH | `/projects/{id}` | Project admin | Update project |
| DELETE | `/projects/{id}` | Project owner | Delete project |

Project roles: `owner` (100), `admin` (80), `member` (50).

---

## Targets

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/targets` | Project member | Create target (`project_id`, `name`, `url`, scraping config, extraction config) |
| GET | `/targets` | Project member | List targets (`project_id` required, `is_active` filter) |
| GET | `/targets/{id}` | Project member | Get target |
| PATCH | `/targets/{id}` | Project member | Update target |
| DELETE | `/targets/{id}` | Project admin | Delete target |

Target fields include: `project_id`, `url`, `target_type`, `javascript_enabled`, `wait_for_selector`, `wait_time_ms`, `timeout_ms`, `screenshot`, `headers`, `cookies`, `extraction_strategy`, `extraction_config`, `output_schema`, `schedule_interval`, `tags`.

---

## Jobs

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/jobs` | Project member | Create job (`url`, `project_id`, `priority` 1-20, scraping config) |
| GET | `/jobs` | Project member | List jobs (`project_id`, `status`, `page`, `page_size`). Paginated response with `{items, total, page, page_size, total_pages, has_next, has_prev}` |
| GET | `/jobs/{id}` | Project member | Job detail with runs, scrape results, extraction results |
| POST | `/jobs/{id}/cancel` | Project member | Cancel pending/running job |
| POST | `/jobs/{id}/retry` | Project member | Reset failed job to pending |
| DELETE | `/jobs/{id}` | Project admin | Delete job |
| GET | `/jobs/{id}/runs` | Project member | Execution attempts for job |
| GET | `/jobs/{id}/results` | Project member | Scrape + extraction results |

Job statuses: `pending`, `queued`, `running`, `completed`, `failed`, `retrying`, `cancelled`, `blocked`, `rate_limited`, `captcha_required`.

---

## Proxies

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/proxies` | Bearer | Add proxy (`host`, `port`, `protocol`, `project_id`, `country`, `weight`) |
| GET | `/proxies` | Bearer/API | List proxies (`project_id`, `status`, `country`, `page`, `page_size`) |
| GET | `/proxies/{id}` | Bearer/API | Get proxy |
| DELETE | `/proxies/{id}` | Project admin | Delete proxy |
| POST | `/proxies/{id}/check` | Project member | Test single proxy connectivity + latency |
| POST | `/proxies/check-all` | Admin | Batch check all proxies |

Protocols: `http`, `https`, `socks4`, `socks5`. Statuses: `active`, `inactive`, `banned`, `checking`, `rate_limited`, `error`.

---

## Schedules

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/schedules` | Project member | Create schedule (`project_id`, `url`, `interval`, `cron_expression`, config) |
| GET | `/schedules` | Project member | List schedules (`project_id` required, `is_active`, `page`, `page_size`) |
| GET | `/schedules/{id}` | Project member | Get schedule |
| PATCH | `/schedules/{id}` | Project member | Update schedule |
| DELETE | `/schedules/{id}` | Project admin | Delete schedule |
| POST | `/schedules/{id}/toggle` | Project member | Toggle active state |

Intervals: `every_minute`, `every_5_minutes`, `every_15_minutes`, `every_30_minutes`, `hourly`, `every_2_hours`, `every_4_hours`, `every_6_hours`, `every_12_hours`, `daily`, `weekly`, `biweekly`, `monthly`, `custom_cron`.

---

## Extractions

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/extractions/extract` | Bearer/API | AI extract from content (`content`, `schema`, `prompt_template`, `fields`, `model`) |
| POST | `/extractions/classify` | Bearer/API | Classify content into categories (`content`, `categories[]`) |
| POST | `/extractions/extract-contacts` | Bearer/API | Extract emails, phones, addresses |
| POST | `/extractions/extract-table` | Bearer/API | Extract tabular data (`content`, optional `table_selector`) |
| GET | `/extractions/results/{id}` | Bearer/API | Stored extraction result with full data, model, tokens, cost |

Extraction response fields: `success`, `data`, `error`, `processing_time_ms`, `model_used`, `tokens_used`, `confidence_score`.

---

## Monitoring

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/monitoring/health` | None | `{status, version, uptime, database, redis}` |
| GET | `/monitoring/metrics` | None | Prometheus text format |
| GET | `/monitoring/stats` | Bearer/API | `{total_jobs, active_jobs, completed_24h, failed_24h, success_rate, total_proxies, active_proxies}` |
| GET | `/monitoring/queue-status` | Bearer/API | Queue lengths: `{critical, high, default, low, retry, dead_letter, scheduled}` |

Prometheus metrics also available at `/metrics` (root app mount).

---

## Rate Limiting

| Scope | Limit | Window |
|-------|-------|--------|
| General API | 20 requests | 1 second sliding window |
| Login | 10 requests | 1 second sliding window |

Exceeded requests receive HTTP 429 with `RATE_LIMIT` error code. Limit key derivation: X-API-Key prefix > Bearer token prefix > client IP.
