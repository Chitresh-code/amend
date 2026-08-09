from datetime import UTC, datetime

import pytest

from app.ingestion import embed as embed_module
from app.ingestion.embed import IndexBuildError, build_index

EMBEDDING_MODEL_ID = "openai:text-embedding-3-large"


@pytest.fixture
def seed_embedding_model(db_conn):
    # Mirrors migration 0010's INSERT: clean_state truncates embedding_models
    # before every test (test_embedding_indexes_api.py relies on it starting
    # empty), so tests exercising build_index seed this row themselves.
    db_conn.execute(
        """
        INSERT INTO embedding_models (embedding_model_id, provider, model_id, dimension,
                                       status, table_name)
        VALUES (%s, 'openai', 'text-embedding-3-large', 1536, 'building',
                'clause_embeddings_openai_text_embedding_3_large')
        """,
        (EMBEDDING_MODEL_ID,),
    )


def _seed_clauses(db_conn, document_id: str, clause_ids: list[str]) -> None:
    db_conn.execute(
        """
        INSERT INTO documents
            (document_id, regulator, document_type, title, source_url, source_checksum,
             retrieved_at, parser_version, ingestion_version)
        VALUES (%s, 'RBI', 'master_direction', 'Test doc', 'https://rbi.org.in/x.pdf', 'abc',
                %s, '1.0.0', '1.0.0')
        """,
        (document_id, datetime.now(UTC)),
    )
    for i, clause_id in enumerate(clause_ids):
        db_conn.execute(
            "INSERT INTO clauses (clause_id, document_id, clause_number, text) "
            "VALUES (%s, %s, %s, %s)",
            (clause_id, document_id, str(i + 1), f"clause text {i}"),
        )


def _fake_embed_batch(texts, **kwargs):
    return [[0.1] * 1536 for _ in texts]


def test_build_index_embeds_pending_clauses(db_conn, monkeypatch, seed_embedding_model):
    monkeypatch.setattr(embed_module, "embed_batch", _fake_embed_batch)
    _seed_clauses(db_conn, "rbi:embed-test-1", ["rbi:embed-test-1:0", "rbi:embed-test-1:1"])

    summary = build_index(db_conn, embedding_model_id=EMBEDDING_MODEL_ID)

    assert summary.embedded == 2
    assert summary.failed == 0
    count = db_conn.execute(
        "SELECT count(*) FROM clause_embeddings_openai_text_embedding_3_large"
    ).fetchone()
    assert count is not None
    assert count[0] == 2

    status = db_conn.execute(
        "SELECT status FROM embedding_models WHERE embedding_model_id = %s", (EMBEDDING_MODEL_ID,)
    ).fetchone()
    assert status is not None
    assert status[0] == "ready"


def test_build_index_is_idempotent(db_conn, monkeypatch, seed_embedding_model):
    calls = {"count": 0}

    def counting_embed_batch(texts, **kwargs):
        calls["count"] += len(texts)
        return _fake_embed_batch(texts, **kwargs)

    monkeypatch.setattr(embed_module, "embed_batch", counting_embed_batch)
    _seed_clauses(db_conn, "rbi:embed-test-2", ["rbi:embed-test-2:0"])

    build_index(db_conn, embedding_model_id=EMBEDDING_MODEL_ID)
    assert calls["count"] == 1

    summary = build_index(db_conn, embedding_model_id=EMBEDDING_MODEL_ID)
    assert summary.embedded == 0
    assert calls["count"] == 1  # no re-embedding of already-embedded clauses


def test_build_index_continues_past_a_failing_batch(db_conn, monkeypatch, seed_embedding_model):
    def flaky_embed_batch(texts, **kwargs):
        if any("bad" in t for t in texts):
            raise RuntimeError("embedding provider error")
        return _fake_embed_batch(texts, **kwargs)

    monkeypatch.setattr(embed_module, "embed_batch", flaky_embed_batch)
    monkeypatch.setattr(embed_module, "_SELECT_BATCH_SIZE", 1)

    db_conn.execute(
        """
        INSERT INTO documents
            (document_id, regulator, document_type, title, source_url, source_checksum,
             retrieved_at, parser_version, ingestion_version)
        VALUES ('rbi:embed-test-3', 'RBI', 'master_direction', 'Test doc',
                'https://rbi.org.in/x.pdf', 'abc', %s, '1.0.0', '1.0.0')
        """,
        (datetime.now(UTC),),
    )
    db_conn.execute(
        "INSERT INTO clauses (clause_id, document_id, clause_number, text) VALUES "
        "('rbi:embed-test-3:0', 'rbi:embed-test-3', '1', 'bad clause'), "
        "('rbi:embed-test-3:1', 'rbi:embed-test-3', '2', 'good clause')"
    )

    summary = build_index(db_conn, embedding_model_id=EMBEDDING_MODEL_ID)

    assert summary.embedded == 1
    assert summary.failed == 1
    # A residual failure doesn't block readiness (mirrors Phase 1 accepting a
    # small known-failure count rather than blocking the whole corpus); the
    # failed clause is simply retried on the next invocation.
    status = db_conn.execute(
        "SELECT status FROM embedding_models WHERE embedding_model_id = %s", (EMBEDDING_MODEL_ID,)
    ).fetchone()
    assert status is not None
    assert status[0] == "ready"


def test_build_index_raises_for_unregistered_model(db_conn):
    with pytest.raises(IndexBuildError):
        build_index(db_conn, embedding_model_id="voyage:voyage-law-2")
