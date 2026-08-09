# Amend API

FastAPI service: retrieval pipeline, Strands Agents LLM layer, Postgres/Neo4j access. See the [repository root README](../README.md) for the monorepo overview and [../docs/](../docs/) for product requirements, architecture, and schema.

## Development

```bash
cd api
uv sync --dev
uv run ruff check .
uv run ruff format --check .
uv run mypy app
uv run pytest
```

Run the full stack (this service plus Postgres, Neo4j, Redis) from the repository root: `docker compose up`.

## Ingestion

The ingestion worker (`python -m app.ingestion`, also `docker-compose.yml`'s `worker` service) needs a Chromium binary for the RBI document fetch path (see `app/ingestion/loaders/fetch.py`), a one-time local setup step:

```bash
uv run playwright install chromium
```

After the corpus is ingested, `python -m app.ingestion.embed` builds the embedding index registered by migration `0010` (`openai:text-embedding-3-large`), embedding every clause that isn't already in `clause_embeddings_openai_text_embedding_3_large` and flipping it to `ready` once complete. Needs a real `INGESTION_EMBEDDING_API_KEY` in `.env`; safe to re-run (only embeds clauses not already indexed).
