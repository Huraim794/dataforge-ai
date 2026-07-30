# Security Policy

## Security Measures Implemented

DataForge AI incorporates the following security measures:

### Authentication & Authorization

- **JWT-based authentication**: Access tokens (configurable expiry, default 30 min) and refresh tokens (configurable expiry, default 7 days) signed with HS256 using a configurable secret key.
- **Password hashing**: All passwords are hashed with bcrypt via the `passlib` library before storage. Plaintext passwords are never persisted.
- **API key hashing**: API keys are SHA-256 hashed before storage. The raw key is displayed only once at creation time and cannot be retrieved later.
- **Role-based access control (RBAC)**: Three-tier role system (admin, user, viewer) enforced at the endpoint level via FastAPI dependency injection.
- **Project-level access control**: Project membership with owner, admin, and member roles. All project-scoped resources verify user membership before access.

### Network & Transport

- **CORS middleware**: Cross-Origin Resource Sharing restricted to a configurable allowlist of origins.
- **Reverse proxy**: Production deployments behind Nginx reverse proxy for TLS termination and additional security hardening.

### Rate Limiting

- **Sliding window rate limiter**: Redis-backed rate limiting on authentication endpoints (login) and general API endpoints.
- **Per-client identification**: Rate limiting scoped to API keys, bearer tokens, or IP addresses, applied in priority order.

### Data Protection

- **Secret key validation**: Production deployments enforce a minimum-length secret key via validation at startup.
- **Connection pooling**: Database connection pools with configurable limits to prevent resource exhaustion.
- **Environment-based configuration**: Sensitive values injected via environment variables, never hard-coded.

### Monitoring & Incident Response

- **Structured logging**: All security-relevant events (authentication, authorization failures, rate limit hits) logged with structured context.
- **Error tracking**: Sentry integration for real-time error monitoring and alerting.
- **Prometheus metrics**: Operational metrics exposed for monitoring dashboards and anomaly detection.

## Reporting Vulnerabilities

We take the security of DataForge AI seriously. If you discover a security vulnerability, please follow these steps:

1. **Do not** disclose the vulnerability publicly (e.g., via a GitHub issue or discussion).
2. **Do not** exploit the vulnerability or demonstrate it in a way that impacts other users.
3. **Send a report** to security@dataforge.ai with the following details:
   - A description of the vulnerability and the potential impact.
   - Steps to reproduce the issue, including any relevant configuration.
   - Your suggested fix or mitigation, if applicable.
   - Your contact information for follow-up.

You can expect:

- **Acknowledgment** of your report within 48 hours.
- **An initial assessment** within 5 business days, including a severity classification and expected timeline for a fix.
- **Regular updates** on the progress toward a resolution.
- **Credit** in our security acknowledgments if you are the first reporter of a confirmed vulnerability (unless you request otherwise).

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

Only the latest minor release of the current major version receives security updates.

## Security Update Policy

- **Critical vulnerabilities**: A patch release will be issued within 48 hours of confirmation.
- **High severity vulnerabilities**: A patch release will be issued within 7 days.
- **Medium/low severity vulnerabilities**: Addressed in the next scheduled minor release.
- Security patches are backported to the latest minor release only.

When a security fix is released, we publish a security advisory on GitHub describing the vulnerability, affected versions, and mitigation steps. We recommend all users upgrade as soon as possible following a security advisory.

---

**Note**: If you are deploying DataForge AI in production, you must:

1. Set a strong `SECRET_KEY` (generate with `openssl rand -hex 32`).
2. Enable TLS via the Nginx reverse proxy.
3. Configure `ALLOWED_ORIGINS` to your specific frontend domain(s).
4. Set `ENVIRONMENT=production` to enforce security validations.
5. Restrict database and Redis access to the application tier only.
