import hashlib
from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.run import (
    _already_succeeded,
    _record_state,
    _replace_clauses,
    _upsert_document,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _ingest_fixture(db_conn, document_id: str, filename: str) -> str:
    content = _load(filename)
    checksum = hashlib.sha256(content).hexdigest()
    _upsert_document(
        db_conn,
        document_id=document_id,
        regulator="RBI",
        document_type="master_direction",
        title="Test document",
        publication_date=None,
        source_url="https://rbidocs.rbi.org.in/rdocs/notification/PDFs/test.PDF",
        checksum=checksum,
        retrieved_at=datetime.now(UTC),
    )
    _replace_clauses(db_conn, document_id, content)
    _record_state(db_conn, document_id, "succeeded", checksum)
    return checksum


def test_ingest_writes_document_and_clauses(db_conn):
    checksum = _ingest_fixture(
        db_conn, "rbi:test-1", "rbi_master_direction_import_goods_services.pdf"
    )

    doc_row = db_conn.execute(
        "SELECT title, source_checksum FROM documents WHERE document_id = %s", ("rbi:test-1",)
    ).fetchone()
    assert doc_row is not None
    assert doc_row[1] == checksum

    clause_count = db_conn.execute(
        "SELECT count(*) FROM clauses WHERE document_id = %s", ("rbi:test-1",)
    ).fetchone()
    assert clause_count is not None
    assert clause_count[0] > 10


def test_reingesting_same_content_is_idempotent(db_conn):
    _ingest_fixture(db_conn, "rbi:test-2", "rbi_master_direction_import_goods_services.pdf")
    first_count = db_conn.execute(
        "SELECT count(*) FROM clauses WHERE document_id = %s", ("rbi:test-2",)
    ).fetchone()

    _ingest_fixture(db_conn, "rbi:test-2", "rbi_master_direction_import_goods_services.pdf")
    second_count = db_conn.execute(
        "SELECT count(*) FROM clauses WHERE document_id = %s", ("rbi:test-2",)
    ).fetchone()

    assert first_count == second_count

    doc_count = db_conn.execute(
        "SELECT count(*) FROM documents WHERE document_id = %s", ("rbi:test-2",)
    ).fetchone()
    assert doc_count is not None
    assert doc_count[0] == 1


def test_already_succeeded_detects_matching_checksum(db_conn):
    checksum = _ingest_fixture(
        db_conn, "rbi:test-3", "rbi_master_direction_import_goods_services.pdf"
    )

    assert _already_succeeded(db_conn, "rbi:test-3", checksum) is True
    assert _already_succeeded(db_conn, "rbi:test-3", "different-checksum") is False
    assert _already_succeeded(db_conn, "rbi:unknown-doc", checksum) is False
