# Security

## Authentication

The platform supports two authentication methods:

**JWT Bearer Tokens** — Primary auth for interactive sessions. Access tokens last 30 minutes; refresh tokens last 7 days. Rotation is enforced: each `/auth/refresh` call issues a new refresh token along with a new access token.

**API Keys** — Programmatic auth for automated workflows. Keys are prefixed with `df_` and generated via `secrets.token_urlsafe(32)` (48 raw bytes → 64 URL-safe characters). The full key is returned once at creation; only the SHA-256 hash and first 8 characters (prefix) are stored in the database.

### Credential Flow

```
Client                  API Server
  │                        │
  │── POST /auth/login ───→│  Validate email + password (bcrypt verify)
  │←── { access_token,    ─│  Create JWT (sub=user_id, role, type=access, exp=30m)
  │     refresh_token }    │  Create JWT (sub=user_id, type=refresh, exp=7d)
  │                        │
  │── GET /resource ──────→│  Extract Bearer token or X-API-Key
  │   Authorization: Bearer│  Verify JWT signature + expiry
  │                        │  OR hash(key) → lookup in api_keys table
  │←── response ──────────│
```

---

## Authorization

### Role-Based Access Control

Global roles (stored on `users.role`):

| Role | Hierarchy | Description |
|------|-----------|-------------|
| `admin` | 100 | Full system access, user management, proxy check-all |
| `user` | 50 | Standard access, can create/manage own resources |
| `viewer` | 10 | Read-only access |

The `require_role` dependency (`core/deps.py:107`) compares numeric rank:

```python
roles = {"admin": 100, "user": 50, "viewer": 10}
if roles.get(user_role, 0) < roles.get(required_role, 0):
    raise HTTPException(403)
```

### Project-Level Access

Projects use a membership model (`project_members` table):

| Role | Level | Permissions |
|------|-------|-------------|
| `owner` | 100 | Full control, can delete project |
| `admin` | 80 | Update project, delete targets/jobs/proxies/schedules |
| `member` | 50 | Create and manage resources within project |

The `verify_project_access` decorator checks both membership and minimum role level. Endpoints that modify data require `member` or `admin`; deletion requires `admin` or `owner`.

---

## Token Management

**Access Token Payload:**
```json
{
  "sub": "user-uuid",
  "role": "user",
  "projects": ["project-id-1", "project-id-2"],
  "iat": 1700000000,
  "exp": 1700001800,
  "iss": "dataforge-ai",
  "type": "access"
}
```

- Issued by `HS256` symmetric signing using `SECRET_KEY`
- Refresh tokens are single-use (rotation on each refresh call)
- Token validation in `core/security.py` checks: signature, expiration, token type, issuer
- No blacklist: access tokens are short-lived (30 min). For immediate revocation, set `redis` key `revoked_token:<jti>` — not yet implemented but the architecture supports it.

---

## API Key Hashing

API keys are hashed with SHA-256 before storage:

```python
def hash_api_key(api_key: str) -> str:
    return sha256(api_key.encode()).hexdigest()
```

- The raw key is returned only at creation time
- The `key_prefix` column stores the first 8 characters (e.g., `df_abc12`) for UI identification
- Authentication lookup: hash the incoming key → query `api_keys` where `key_hash == hash`
- A 64-character URL-safe key with SHA-256 hashing provides 256-bit security against preimage attacks

---

## Input Validation

All request bodies use Pydantic v2 models with type coercion, string length constraints, numeric ranges, and optional/mandatory fields. Invalid input returns a structured 422 response before any business logic runs.

Database queries use SQLAlchemy ORM exclusively. No raw SQL is constructed from user input, preventing SQL injection. Query parameters like `project_id`, `status`, and `country` pass through enum validation (`ProxyStatus`, `JobStatus`) or type coercion before reaching the database.

---

## CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Default allowed origins: `http://localhost:5173` (Vite dev server), `http://localhost:3000` (alternative). Configure via `ALLOWED_ORIGINS` environment variable as a comma-separated list. In production, restrict to your actual frontend domain.

---

## Rate Limiting

A Redis-based sliding window rate limiter protects against abuse.

**Login endpoint:** 10 requests per 1-second window (burst limit 20, per `rate_limit_burst_size`).

**General API:** 20 requests per 1-second window (burst limit 40).

The limiter identifies clients by (in priority order):

1. `X-API-Key` header (first 16 characters)
2. Bearer token (first 20 characters)
3. Client IP address

Implementation (`core/rate_limiter.py`):

```python
key = f"ratelimit:{client_key}"
await redis.zremrangebyscore(key, "-inf", window_start)
count = await redis.zcard(key)
if count >= burst_size:
    raise HTTPException(429)
await redis.zadd(key, {str(now): now})
await redis.expire(key, window_seconds * 2)
```

The sorted set tracks per-client request timestamps. Old entries are pruned on each check. A fallback `except Exception: pass` ensures rate limiting failures don't block legitimate requests.

---

## Security Headers (Nginx)

```nginx
add_header Strict-Transport-Security "max-age=63072000" always;
add_header X-Content-Type-Options nosniff;
add_header X-Frame-Options DENY;
add_header X-XSS-Protection "1; mode=block";
add_header Referrer-Policy strict-origin-when-cross-origin;
```

- **HSTS**: 2-year enforcement, covers all subdomains
- **X-Content-Type-Options**: Prevents MIME-type sniffing
- **X-Frame-Options**: Clickjacking protection
- **X-XSS-Protection**: Legacy XSS filter (modern browsers use CSP)
- **Referrer-Policy**: Referrer header sent only on same-origin
- **server_tokens off**: Hides nginx version in error pages and headers

---

## Password Policy

- Minimum password length: 8 characters (enforced by Pydantic `Field(min_length=8)`)
- Hashing: bcrypt via `passlib` with `CryptContext(schemes=["bcrypt"], deprecated="auto")`
- No plaintext storage: `hash_password()` is called before persisting
- Passwords are verified with `verify_password()` using `passlib.context.verify`, which handles salt extraction and comparison

---

## Secret Management

Secrets are never hardcoded. The platform reads from environment variables via `pydantic-settings`:

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
```

- `SECRET_KEY`: Validated at startup — raises `ValueError` if empty in production
- `LLM_API_KEY`: Optional per-provider; inferred from environment
- `CAPTCHA_SERVICE_API_KEY`: Optional; loaded at runtime
- `SENTRY_DSN`: Optional; enables error reporting when set

In production, consider using Docker secrets or a vault service instead of `.env` files. The current setup expects secrets in the environment at container runtime.
