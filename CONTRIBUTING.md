# Contributing to DataForge AI

Thank you for your interest in contributing to DataForge AI. This document provides guidelines and instructions for contributing effectively.

## Code of Conduct

This project is governed by a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+
- Docker and Docker Compose (optional, for containerized development)

### Setting Up a Development Environment

1. **Clone the repository:**

   ```bash
   git clone https://github.com/dataforge-ai/dataforge.git
   cd dataforge
   ```

2. **Backend setup:**

   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Unix
   pip install -e ".[dev]"
   ```

3. **Frontend setup:**

   ```bash
   cd frontend
   npm install
   ```

4. **Environment configuration:**

   ```bash
   copy infra\.env.example .env  # Windows
   cp infra/.env.example .env    # Unix
   ```

   Edit `.env` with your local settings. The defaults work with the Docker Compose infrastructure.

5. **Start infrastructure services:**

   ```bash
   cd infra
   docker compose up -d postgres redis
   ```

6. **Run the backend:**

   ```bash
   cd backend
   uvicorn dataforge.backend.app.main:app --reload --port 8000
   ```

7. **Run the frontend:**

   ```bash
   cd frontend
   npm run dev
   ```

## Development Workflow

### Branching

- `main` — stable, release-ready code. Direct pushes are blocked.
- `develop` — integration branch for feature work.
- `feat/*` — feature branches branched from `develop`.
- `fix/*` — bug fix branches.
- `docs/*` — documentation-only changes.

### Commit Messages

Write commit messages using conventional commits format:

```
<type>(<scope>): <short summary>

[optional body]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`.

Example: `feat(extraction): add Mistral AI provider support`

### Pull Request Process

1. Create a feature/fix branch from `develop`.
2. Make your changes, keeping commits focused and atomic.
3. Ensure all tests pass and linting is clean.
4. Open a PR against `develop` with a clear description of the change.
5. Request review from at least one maintainer.
6. Address review feedback. Squash commits if requested.
7. Once approved, a maintainer will merge your PR.

## Coding Standards

### Python

- Target Python 3.12+.
- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines.
- Use type annotations for all function signatures and public APIs.
- Use async/await for I/O-bound operations. Avoid blocking calls in async paths.
- Prefer Pydantic models for data validation and serialization.
- Use SQLAlchemy 2.0 style queries (async) for database operations.
- Format code with `ruff format`. Lint with `ruff check`.
- Organize imports: standard library, third-party, local. Use absolute imports.

### TypeScript

- Target ES2022+.
- Use strict TypeScript configuration. Avoid `any` where possible.
- Use React functional components with hooks.
- Style components with TailwindCSS utility classes.
- Use the existing API client in `src/services/api.ts` for all backend calls.
- Run `npm run lint` before committing.

## Testing Requirements

- Write tests for all new features and bug fixes.
- Backend tests use pytest with async support (pytest-asyncio).
- Frontend tests use Vitest + React Testing Library.
- Test coverage should not decrease on PRs.
- Run the full test suite before submitting a PR:

  ```bash
  # Backend
  cd backend && pytest

  # Frontend
  cd frontend && npm test
  ```

## Documentation Requirements

- All public API endpoints must have OpenAPI-compatible docstrings.
- New configuration options must be documented in `.env.example` with comments.
- Python functions and classes need docstrings describing purpose, parameters, and return values.
- Frontend components should include brief JSDoc comments for props.
- Significant architectural changes require an entry in the project documentation under `docs/`.

## PR Review Process

All PRs go through the following review stages:

1. **Automated checks**: CI runs linting, type checking, and tests. All must pass.
2. **Code review**: At least one maintainer reviews the code for correctness, style, and adherence to standards.
3. **Functional review**: For significant features, the reviewer may request a demo or run the changes locally.
4. **Documentation review**: Changes affecting public APIs or configuration must include or update relevant documentation.

### What Reviewers Look For

- Correctness and completeness of the implementation.
- Test coverage for the changed code paths.
- Code organization and adherence to project conventions.
- Performance implications (especially in async and I/O paths).
- Security considerations (input validation, authentication, rate limiting).
- Error handling and logging adequacy.

---

Thank you for contributing. Every contribution, no matter how small, helps make this project better.
