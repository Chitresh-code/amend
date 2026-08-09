import logging
import re
from dataclasses import dataclass

import psycopg
from pgvector.psycopg import register_vector

from app.config import settings
from app.ingestion.embeddings import embed_batch

logger = logging.getLogger(__name__)

# table_name always originates from a migration (DATA_MODEL.md §1.3), never
# from request input, but this is still interpolated into raw SQL below, so
# it's validated defensively before use.
_TABLE_NAME_RE = re.compile(r"^clause_embeddings_[a-z0-9_]+$")

_SELECT_BATCH_SIZE = 500


class IndexBuildError(Exception):
    pass


@dataclass
class BuildSummary:
    embedded: int = 0
    failed: int = 0


def _resolve_table(conn: psycopg.Connection, embedding_model_id: str) -> tuple[str, int]:
    row = conn.execute(
        "SELECT table_name, dimension FROM embedding_models WHERE embedding_model_id = %s",
        (embedding_model_id,),
    ).fetchone()
    if row is None or row[0] is None:
        raise IndexBuildError(
            f"{embedding_model_id} has no table_name; apply its migration before running this job"
        )
    table_name = str(row[0])
    if not _TABLE_NAME_RE.match(table_name):
        raise IndexBuildError(f"refusing to use unexpected table name: {table_name}")
    return table_name, int(row[1])


def _pending_clauses(
    conn: psycopg.Connection, table_name: str, exclude_ids: list[str]
) -> list[tuple[str, str]]:
    return conn.execute(
        f"""
        SELECT c.clause_id, c.text FROM clauses c
        LEFT JOIN {table_name} e ON e.clause_id = c.clause_id
        WHERE e.clause_id IS NULL AND NOT (c.clause_id = ANY(%s))
        ORDER BY c.clause_id
        LIMIT %s
        """,  # noqa: S608 - table_name validated above, not request input
        (exclude_ids, _SELECT_BATCH_SIZE),
    ).fetchall()


def build_index(conn: psycopg.Connection, *, embedding_model_id: str | None = None) -> BuildSummary:
    # conn must be opened with autocommit=True, same reasoning as
    # app/ingestion/run.py: a non-autocommit connection's plain SELECT below
    # would start an ambient transaction that turns the INSERT below into a
    # no-op nested savepoint instead of a real commit.
    register_vector(conn)
    embedding_model_id = embedding_model_id or (
        f"{settings.ingestion_embedding_provider}:{settings.ingestion_embedding_model_id}"
    )
    table_name, dimension = _resolve_table(conn, embedding_model_id)

    summary = BuildSummary()
    # Clause ids from a batch that failed this run: excluded from later
    # SELECTs so one bad batch doesn't get re-selected forever within this
    # invocation. They're retried on the *next* invocation (not persisted as
    # excluded), same as app/ingestion/run.py leaving a failed document for
    # the next run rather than blocking everything behind it.
    failed_this_run: list[str] = []
    while True:
        pending = _pending_clauses(conn, table_name, failed_this_run)
        if not pending:
            break

        clause_ids = [row[0] for row in pending]
        texts = [row[1] for row in pending]
        try:
            vectors = embed_batch(
                texts,
                provider=settings.ingestion_embedding_provider,
                model_id=settings.ingestion_embedding_model_id,
                api_key=settings.ingestion_embedding_api_key,
                dimensions=dimension,
                base_url=settings.ingestion_embedding_base_url or None,
            )
        except Exception:
            # A failing batch must not abort the whole ~83k-clause run (same
            # resilience shape as app/ingestion/run.py's per-document catch).
            logger.exception("embedding batch failed for %d clauses, skipping", len(clause_ids))
            summary.failed += len(clause_ids)
            failed_this_run.extend(clause_ids)
            continue

        with conn.transaction():
            with conn.cursor() as cur:
                cur.executemany(
                    f"INSERT INTO {table_name} (clause_id, embedding) VALUES (%s, %s) "  # noqa: S608
                    "ON CONFLICT (clause_id) DO NOTHING",
                    list(zip(clause_ids, vectors, strict=True)),
                )
        summary.embedded += len(clause_ids)
        logger.info("embedded %d clauses so far", summary.embedded)

    # The pending queue is drained at this point (every clause has either
    # succeeded or failed this run); a small residual failure count doesn't
    # block readiness, same as Phase 1 accepting 2/544 documents as a known
    # limitation rather than blocking the whole corpus on a perfect run.
    # Failed clauses are simply absent from the index and retried next run.
    conn.execute(
        "UPDATE embedding_models SET status = 'ready' WHERE embedding_model_id = %s",
        (embedding_model_id,),
    )

    return summary


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with psycopg.connect(settings.postgres_dsn, autocommit=True) as conn:
        summary = build_index(conn)
    logger.info(
        "embedding index build complete: embedded=%d failed=%d", summary.embedded, summary.failed
    )


if __name__ == "__main__":
    main()
