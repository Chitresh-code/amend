from datetime import UTC, datetime

import psycopg
import pytest
import pytest_asyncio
from pgvector.psycopg import register_vector

from app.config import settings
from app.retrieval.vector_search import RetrievalError, search_clauses

EMBEDDING_MODEL_ID = "openai:text-embedding-3-large"


def _vector(*, first: float, second: float = 0.0) -> list[float]:
    return [first, second] + [0.0] * 1534


@pytest_asyncio.fixture
async def async_db_conn():
    conn = await psycopg.AsyncConnection.connect(settings.postgres_dsn, autocommit=True)
    try:
        yield conn
    finally:
        await conn.close()


def _seed(db_conn) -> None:
    db_conn.execute(
        """
        INSERT INTO embedding_models (embedding_model_id, provider, model_id, dimension,
                                       status, table_name)
        VALUES (%s, 'openai', 'text-embedding-3-large', 1536, 'ready',
                'clause_embeddings_openai_text_embedding_3_large')
        """,
        (EMBEDDING_MODEL_ID,),
    )
    db_conn.execute(
        """
        INSERT INTO documents
            (document_id, regulator, document_type, title, source_url, source_checksum,
             retrieved_at, parser_version, ingestion_version)
        VALUES
            ('rbi:vs-1', 'RBI', 'master_direction', 'RBI doc', 'https://rbi.org.in/x.pdf',
             'a', %(now)s, '1.0.0', '1.0.0'),
            ('sebi:vs-1', 'SEBI', 'master_circular', 'SEBI doc', 'https://sebi.gov.in/x.pdf',
             'b', %(now)s, '1.0.0', '1.0.0')
        """,
        {"now": datetime.now(UTC)},
    )
    db_conn.execute(
        "INSERT INTO clauses (clause_id, document_id, clause_number, heading, text) VALUES "
        "('rbi:vs-1:0', 'rbi:vs-1', '1', 'Close match', 'closest text'), "
        "('rbi:vs-1:1', 'rbi:vs-1', '2', 'Far match', 'far text'), "
        "('sebi:vs-1:0', 'sebi:vs-1', '1', 'SEBI match', 'sebi text')"
    )

    register_vector(db_conn)
    with db_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO clause_embeddings_openai_text_embedding_3_large "
            "(clause_id, embedding) VALUES (%s, %s), (%s, %s), (%s, %s)",
            (
                "rbi:vs-1:0",
                _vector(first=1.0),
                "rbi:vs-1:1",
                _vector(first=-1.0),
                "sebi:vs-1:0",
                _vector(first=0.9, second=0.2),
            ),
        )


@pytest.mark.asyncio
async def test_search_clauses_ranks_by_cosine_distance(db_conn, async_db_conn):
    _seed(db_conn)
    query = _vector(first=1.0)

    results = await search_clauses(async_db_conn, query, EMBEDDING_MODEL_ID, top_k=10)

    assert [r.clause_id for r in results] == ["rbi:vs-1:0", "sebi:vs-1:0", "rbi:vs-1:1"]
    assert results[0].score < results[1].score < results[2].score


@pytest.mark.asyncio
async def test_search_clauses_filters_by_regulator(db_conn, async_db_conn):
    _seed(db_conn)
    query = _vector(first=1.0)

    results = await search_clauses(
        async_db_conn, query, EMBEDDING_MODEL_ID, top_k=10, regulator="SEBI"
    )

    assert [r.clause_id for r in results] == ["sebi:vs-1:0"]


@pytest.mark.asyncio
async def test_search_clauses_respects_top_k(db_conn, async_db_conn):
    _seed(db_conn)
    query = _vector(first=1.0)

    results = await search_clauses(async_db_conn, query, EMBEDDING_MODEL_ID, top_k=1)

    assert len(results) == 1
    assert results[0].clause_id == "rbi:vs-1:0"


@pytest.mark.asyncio
async def test_search_clauses_raises_for_non_ready_index(db_conn, async_db_conn):
    db_conn.execute(
        """
        INSERT INTO embedding_models (embedding_model_id, provider, model_id, dimension,
                                       status, table_name)
        VALUES ('voyage:voyage-law-2', 'voyage', 'voyage-law-2', 1024, 'registered', NULL)
        """
    )

    with pytest.raises(RetrievalError):
        await search_clauses(async_db_conn, [0.0] * 1024, "voyage:voyage-law-2")

    with pytest.raises(RetrievalError):
        await search_clauses(async_db_conn, [0.0] * 1536, "unknown:model")
