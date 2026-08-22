import hashlib
from datetime import UTC, datetime
from pathlib import Path

from app.ingestion.parser import parse_pdf
from app.ingestion.references import extract_reference_number
from app.ingestion.run import (
    _already_succeeded,
    _record_state,
    _replace_clauses,
    _resolve_reference_number,
    _upsert_document,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _ingest_fixture(db_conn, document_id: str, filename: str) -> str:
    content = _load(filename)
    checksum = hashlib.sha256(content).hexdigest()
    pages = parse_pdf(content)
    _upsert_document(
        db_conn,
        document_id=document_id,
        regulator="RBI",
        document_type="master_direction",
        title="Test document",
        reference_number=extract_reference_number(pages),
        publication_date=None,
        source_url="https://rbidocs.rbi.org.in/rdocs/notification/PDFs/test.PDF",
        checksum=checksum,
        retrieved_at=datetime.now(UTC),
    )
    _replace_clauses(db_conn, document_id, pages)
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


def test_ingest_populates_reference_number_from_pdf_header(db_conn):
    _ingest_fixture(db_conn, "rbi:test-4", "rbi_master_direction_import_goods_services.pdf")

    row = db_conn.execute(
        "SELECT reference_number FROM documents WHERE document_id = %s", ("rbi:test-4",)
    ).fetchone()
    assert row is not None
    assert row[0] == "RBI/FED/2016-17/12"


def test_resolve_reference_number_finds_ingested_target(db_conn):
    _ingest_fixture(db_conn, "rbi:test-5", "rbi_master_direction_import_goods_services.pdf")

    resolved = _resolve_reference_number(db_conn, "RBI/FED/2016-17/12", "rbi:some-other-doc")
    assert resolved == "rbi:test-5"


def test_resolve_reference_number_returns_none_when_unresolved(db_conn):
    assert _resolve_reference_number(db_conn, "RBI/DOES-NOT-EXIST/1", "rbi:test-6") is None


def test_resolve_reference_number_excludes_self(db_conn):
    _ingest_fixture(db_conn, "rbi:test-7", "rbi_master_direction_import_goods_services.pdf")

    assert _resolve_reference_number(db_conn, "RBI/FED/2016-17/12", "rbi:test-7") is None
