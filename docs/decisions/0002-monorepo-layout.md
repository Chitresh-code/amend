# 0002: Monorepo layout for api and web

Status: Accepted
Date: 2026-08-07

## Context

Amend was API-only until now, with the Python project at the repository root. A web frontend is coming: UI designs are being prepared and will follow shortly. The frontend's framework has not been chosen yet and should not be guessed by scaffolding a specific stack ahead of the designs that are meant to inform it.

## Decision

One repository, split flat at the top level: `api/`, `web/`, `docs/`, plus root-level files that describe or orchestrate both (`README.md`, `docker-compose.yml`, `.env.example`, `.github/workflows/`).

- **`api/`** is the entire former repository root content: `app/`, `tests/`, `pyproject.toml`, `uv.lock`, `Dockerfile`, and its own `README.md` for service-specific setup. It is a self-contained uv project; `cd api && uv sync` works with no dependency on anything outside that directory. Package renamed `amend` to `amend-api` to avoid the ambiguity of the whole monorepo and one of its services sharing a name.
- **`web/`** exists as a placeholder only: a `README.md` explaining why it's empty. No `package.json`, no framework choice, no scaffolding. Adding a real frontend stack before seeing the designs would mean guessing a decision (React vs. something else, app router vs. pages, component library, and so on) that the designs are supposed to inform.
- No `apps/` wrapper directory. With exactly two apps and no shared internal packages yet, the extra nesting level (`apps/api/`, `apps/web/`) buys nothing; flat `api/`/`web/` is one directory shallower and just as clear. Revisit if a shared package (generated API client, shared types) appears later.
- `docs/`, `README.md`, `docker-compose.yml`, `.env.example` stay at the repository root: they describe or orchestrate the whole system, not one service, so they don't belong inside either app directory.

### CI

The existing workflow's job id is `test`, which `main`'s branch protection rule requires as a status check on every PR. Two choices existed: (a) path-filter the job so it only runs on `api/**` changes, or (b) keep it running unconditionally. Path filtering was rejected: a GitHub Actions job skipped by a path filter does not report a status at all, and a required status check that never reports stays pending forever, permanently blocking merge for any PR that only touches `web/`. So for now the job runs unconditionally, scoped to `api/` via `working-directory`, at the cost of slightly wasted CI time once `web/` has nothing to test. A `web` job will be added, with either both jobs always running or a single aggregator job that always reports regardless of which sub-jobs actually ran, once there's a web stack to test.

## Consequences

- `api/app/`, `api/tests/`, `api/pyproject.toml`, `api/uv.lock`, `api/Dockerfile` (moved via `git mv`, history preserved).
- `docker-compose.yml`'s `api`/`worker` services build from `./api` instead of `.`.
- Every doc path reference to `app/...` becomes `api/app/...` (PRD §63, ARCHITECTURE.md, CODING_STANDARDS.md).
- `AGENTS.md`'s repository summary now describes a monorepo, not an API-only repo.
