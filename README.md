# Amend

Amend is a graph-grounded regulatory research system for querying public RBI and SEBI circulars, master directions, notifications, and amendments. It resolves which version of a regulatory provision currently applies, not just which text is semantically similar to a query, by combining semantic retrieval (pgvector) with regulatory lineage traversal (Neo4j), temporal validity checks, and supersession resolution.

> Ask what the regulation says. Amend determines which version applies and shows the evidence.

Full product requirements: [docs/PRD.md](./docs/PRD.md).

## Stack

* **FastAPI** for the API
* **PostgreSQL + pgvector** for clause storage and semantic retrieval
* **Neo4j** for regulatory lineage, amendment, and supersession relationships
* **[Strands Agents](https://strandsagents.com/)** for the LLM layer. Chat models are bring-your-own-key: each caller supplies their own provider credentials (Anthropic, OpenAI, Gemini, Ollama, ...), stored encrypted and scoped to them, not configured once for the whole deployment
* **Docker Compose** for local and reproducible deployment

## Layout

Monorepo:

* **[api/](./api/)**: the FastAPI service. Self-contained: `cd api && uv sync`. See [api/README.md](./api/README.md).
* **[web/](./web/)**: frontend, not yet scaffolded. Framework choice is pending UI designs; see [web/README.md](./web/README.md).
* **docs/**, `docker-compose.yml`, `.env.example`, this file: describe or orchestrate the whole system, not one app.

## Repository guide

| Document | Purpose |
|---|---|
| [docs/PRD.md](./docs/PRD.md) | Product requirements, goals, non-goals, evaluation targets |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Component design, data flow, why the pipeline is deterministic Python plus a thin agent layer |
| [docs/DATA_MODEL.md](./docs/DATA_MODEL.md) | Postgres DDL and Neo4j schema |
| [docs/decisions/](./docs/decisions/) | Decision records (ADRs): context and rationale behind non-trivial choices |
| [docs/CODING_STANDARDS.md](./docs/CODING_STANDARDS.md) | Style, typing, testing, security rules, commit format, uv workflow |
| [AGENTS.md](./AGENTS.md) | Rules for any coding agent working in this repository: git workflow, engineering principles |

## Getting started

```bash
git clone <repository-url>
cd amend
cp .env.example .env   # fill in database, redis, and encryption-key settings
docker compose up
```

Model provider credentials are not set here: once the API is running, each caller submits their own via `POST /v1/credentials` (see [docs/PRD.md §70](./docs/PRD.md#70-model-provider-pluggability)).

API documentation is served through FastAPI's OpenAPI interface once the `api` service is running (`/docs`).

## Development workflow

* Never commit or push directly to `main`. Branch as `type/short-title` (e.g. `feat/clause-lineage-api`) and open a pull request. See [AGENTS.md](./AGENTS.md) for the full workflow and engineering principles this repository follows.
* Run tests with `pytest`.
* Lint and format with `ruff check` / `ruff format`; type-check with `mypy`.

## Status

Early scaffold. Architecture and evaluation targets are defined in the PRD; implementation follows the phased plan in [docs/PRD.md §64](./docs/PRD.md#64-implementation-phases). `web/` is a placeholder pending UI designs.
