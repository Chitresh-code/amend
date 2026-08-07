# Amend: Coding Standards

Applies to `api/`, human- or agent-authored; paths below are relative to that directory unless stated otherwise. `web/` has no code yet (see [docs/decisions/0002-monorepo-layout.md](./decisions/0002-monorepo-layout.md)) and will get its own conventions once a stack is chosen, likely in a `web/`-scoped section here rather than a separate file. See [ARCHITECTURE.md](./ARCHITECTURE.md) for component boundaries, [DATA_MODEL.md](./DATA_MODEL.md) for schema, and [AGENTS.md](../AGENTS.md) for the engineering principles that govern how work is done, not just how code looks.

## Language and tooling

- Python 3.12+ (matches the floor needed by `strands-agents` and current FastAPI/pydantic).
- Formatting and linting: **ruff** (`ruff format`, `ruff check`), one tool instead of black + isort + flake8.
- Static typing: **mypy**, run in CI. All new code is typed; no `Any` used to avoid solving a real typing problem.
- Tests: **pytest**.

### Dependency management: uv only

`uv` is the only supported tool for installing, running, and managing dependencies in this repository. No `pip install`, no `poetry`, no manually-maintained `requirements.txt`.

- Add a dependency with `uv add <package>`, remove one with `uv remove <package>`. Never hand-edit a version into the `dependencies` array in `pyproject.toml`.
- `uv add` writes a lower-bound version constraint on its own (`package>=X.Y.Z`, the version it resolved at add time), configured explicitly via `[tool.uv] add-bounds = "lower"` in `pyproject.toml`. That constraint is the tool's, not a manually chosen pin: it lets `uv sync`/`uv lock --upgrade` move forward to newer compatible releases, while `uv.lock` pins the exact versions everyone actually installs.
- Only add an upper bound or an exact pin by hand when a real, observed conflict or regression requires it, and say why in the commit that adds it. Speculative pinning ("just in case") is not a reason.
- `uv.lock` is committed. `.venv/` is not (already in `.gitignore`).
- Provider extras for `strands-agents` (`anthropic`, `openai`, `gemini`, `ollama`) go through the same flow: `uv add --optional <extra> "strands-agents[<extra>]"`.
- Dev-only tools (`pytest`, `ruff`, `mypy`, ...) go in the `dev` dependency group: `uv add --dev <package>`.

## Style

- Type hints on every function signature (parameters and return type). Use `X | None`, not `Optional[X]`.
- Pydantic models for anything crossing a boundary: API request/response bodies, config, LLM structured output. Not for internal-only data that never leaves a function.
- No bare `except:`. Catch the specific exception you can handle; let everything else propagate.
- No mutable default arguments.
- Prefer composition and plain functions over class hierarchies. A class needs a reason (state to hold, or an interface with more than one real implementation); see AGENTS.md's engineering principles for the general bar on abstraction.
- f-strings for formatting; no `%`-formatting or `.format()` in new code.

## Comments

Follow the comment standard in [AGENTS.md](../AGENTS.md#evidence-driven-engineering-principles) (§8): no decorative separators, no comments restating what the code already says. A comment earns its place by explaining a non-obvious constraint, a trade-off, or a workaround, for example why a Cypher query is structured a particular way, not what it queries.

## Testing

- Every deterministic pipeline stage (`api/app/pipeline/`) has unit tests that run without a live database or model: construct `PipelineState` directly, assert on the output state.
- Every API route has at least one integration test against a test database (docker-compose test profile or an ephemeral fixture), covering the success path and the documented failure modes (validation error, not-found, insufficient-evidence response).
- Strands `Agent` calls are not mocked to assert they "worked": mocking an LLM call and asserting success proves nothing about grounding quality. Instead:
  - Deterministic logic around the agent (prompt construction, evidence formatting, citation extraction/validation) is unit tested directly.
  - Actual model behavior is covered by the evaluation suite (`evaluation/`, PRD §53 to §60), not `tests/`.
- Ingestion parsing has regression fixtures: a known-input document mapped to an expected clause tree, checked into `tests/fixtures/`. Parser changes that alter output on these fixtures require a deliberate fixture update, not a silent pass.
- New non-trivial logic (a branch, a loop, a parser rule, anything touching money, security, or citation correctness) ships with a test in the same change. No exceptions for "add it later."

## Security

- **Cypher**: parameterized queries only, via the driver's parameter binding. Never format user input into a Cypher string. Code review should treat any f-string or `.format()` near a Cypher query as a blocking finding.
- **SQL**: parameterized queries or a query builder, same rule.
- **Ingestion URLs**: validate against an explicit allowlist of regulator domains before fetching (PRD §45); reject redirects outside the allowlist.
- **Secrets**: environment variables only, loaded through `api/app/config.py`. Never a literal default value for a credential: missing config fails startup rather than falling back to an empty string or a placeholder key.
- **Caller-supplied model credentials** (PRD §70.2): decrypt only for the duration of the request that needs them. Never log a decrypted key, include it in an exception message, write it to query telemetry, or return it from any endpoint (`POST /v1/credentials` returns a masked suffix, never the key). Treat any code path that could put a decrypted credential into a log statement or error response as a blocking security finding.
- **Prompt boundary**: when constructing agent input, retrieved document text is passed as clearly delimited, labeled evidence (PRD §46). It is never concatenated into the system prompt, and the agent's system prompt explicitly instructs it to treat document content as data, not instructions.
- **Logging**: structured logging, not string concatenation. Query telemetry never includes raw user PII beyond what PRD §47 and §52 explicitly call for, and never includes decrypted provider credentials.

## Commit messages

Exactly one line: `type(scope): summary`.

- `type` is one of `feat`, `fix`, `refactor`, `test`, `docs`, `build`, `ci`, `chore`, `perf`, `revert`.
- `scope` is the module or area affected (`ingestion`, `retrieval`, `graph`, `api`, `agents`, and so on).
- `summary` is imperative, lowercase, no trailing period.
- No body unless explicitly requested. No attribution trailers, co-author lines, or generated-by notices; see [AGENTS.md](../AGENTS.md) §10 to §11.

Example: `fix(supersession): resolve chain when amendment has no explicit reference`

## Branching and PRs

Covered in full in [AGENTS.md](../AGENTS.md). Summary: never commit to `main` directly; branch as `type/short-title`; open a PR.
