import time
from dataclasses import dataclass
from datetime import date, datetime

import psycopg
from playwright.sync_api import Browser, sync_playwright

from app.config import settings
from app.ingestion.clauses import segment_clauses
from app.ingestion.ids import generate_clause_id, generate_document_id
from app.ingestion.loaders import discover_rbi, discover_sebi
from app.ingestion.loaders.discovery import DiscoveredDocument
from app.ingestion.loaders.fetch import FetchError, fetch_document, fetch_html
from app.ingestion.parser import parse_pdf

PARSER_VERSION = "1.0.0"
INGESTION_VERSION = "1.0.0"

_RESOLVERS = {
    "RBI": discover_rbi.resolve_pdf_url,
    "SEBI": discover_sebi.resolve_pdf_url,
}


@dataclass
class RunSummary:
    succeeded: int = 0
    skipped: int = 0
    failed: int = 0


def _parse_date(text: str | None) -> date | None:
    if not text:
        return None
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _already_succeeded(conn: psycopg.Connection, document_id: str, checksum: str) -> bool:
    row = conn.execute(
        "SELECT status, checksum_at_run FROM ingestion_state WHERE document_id = %s",
        (document_id,),
    ).fetchone()
    return row is not None and row[0] == "succeeded" and row[1] == checksum


def _record_state(
    conn: psycopg.Connection,
    document_id: str,
    status: str,
    checksum: str | None,
    error: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO ingestion_state
            (document_id, stage, status, last_run_at, last_error, checksum_at_run)
        VALUES (%s, 'segment', %s, now(), %s, %s)
        ON CONFLICT (document_id) DO UPDATE SET
            status = EXCLUDED.status,
            last_run_at = EXCLUDED.last_run_at,
            last_error = EXCLUDED.last_error,
            checksum_at_run = EXCLUDED.checksum_at_run
        """,
        (document_id, status, error, checksum),
    )


def _upsert_document(
    conn: psycopg.Connection,
    *,
    document_id: str,
    regulator: str,
    document_type: str,
    title: str,
    publication_date: date | None,
    source_url: str,
    checksum: str,
    retrieved_at: datetime,
) -> None:
    conn.execute(
        """
        INSERT INTO documents
            (document_id, regulator, document_type, title, publication_date,
             source_url, source_checksum, retrieved_at, parser_version, ingestion_version)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (document_id) DO UPDATE SET
            title = EXCLUDED.title,
            publication_date = EXCLUDED.publication_date,
            source_url = EXCLUDED.source_url,
            source_checksum = EXCLUDED.source_checksum,
            retrieved_at = EXCLUDED.retrieved_at,
            parser_version = EXCLUDED.parser_version,
            ingestion_version = EXCLUDED.ingestion_version
        """,
        (
            document_id,
            regulator,
            document_type,
            title,
            publication_date,
            source_url,
            checksum,
            retrieved_at,
            PARSER_VERSION,
            INGESTION_VERSION,
        ),
    )


def _replace_clauses(conn: psycopg.Connection, document_id: str, content: bytes) -> None:
    raw_clauses = segment_clauses(parse_pdf(content))
    clause_ids = [generate_clause_id(document_id, i) for i in range(len(raw_clauses))]

    conn.execute("DELETE FROM clauses WHERE document_id = %s", (document_id,))
    for i, clause in enumerate(raw_clauses):
        parent_id = clause_ids[clause.parent_index] if clause.parent_index is not None else None
        conn.execute(
            """
            INSERT INTO clauses
                (clause_id, document_id, parent_clause_id, clause_number, heading, text,
                 page_number)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                clause_ids[i],
                document_id,
                parent_id,
                clause.clause_number,
                clause.heading,
                clause.text,
                clause.page_number,
            ),
        )


def _ingest_one(conn: psycopg.Connection, doc: DiscoveredDocument, browser: Browser) -> str:
    """Returns 'succeeded' or 'skipped'; raises FetchError/RuntimeError on failure."""
    landing_html = fetch_html(doc.landing_url)
    pdf_url = _RESOLVERS[doc.regulator](landing_html)
    if pdf_url is None:
        raise RuntimeError(f"could not resolve a PDF URL from {doc.landing_url}")

    fetched = fetch_document(pdf_url, browser=browser)
    document_id = generate_document_id(doc.regulator, doc.landing_url, pdf_url)

    if _already_succeeded(conn, document_id, fetched.checksum):
        return "skipped"

    with conn.transaction():
        _upsert_document(
            conn,
            document_id=document_id,
            regulator=doc.regulator,
            document_type=doc.document_type,
            title=doc.title,
            publication_date=_parse_date(doc.publication_date_text),
            source_url=pdf_url,
            checksum=fetched.checksum,
            retrieved_at=fetched.retrieved_at,
        )
        _replace_clauses(conn, document_id, fetched.content)
        _record_state(conn, document_id, "succeeded", fetched.checksum)

    return "succeeded"


def run(conn: psycopg.Connection, *, regulators: tuple[str, ...] = ("RBI", "SEBI")) -> RunSummary:
    # conn must be opened with autocommit=True: individual statements (e.g. the
    # ingestion_state read below) commit immediately instead of holding an
    # ambient transaction open that would turn the per-document `with
    # conn.transaction()` blocks into no-op savepoints instead of real commits.
    discovered: list[DiscoveredDocument] = []
    if "RBI" in regulators:
        discovered.extend(discover_rbi.discover_rbi())
    if "SEBI" in regulators:
        discovered.extend(discover_sebi.discover_sebi())

    summary = RunSummary()
    # One browser for the whole run, reused across every document that needs the
    # bot-mitigation fallback (see loaders/fetch.py) - launching fresh per document
    # would mean hundreds of browser startups for a full corpus run.
    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            for i, doc in enumerate(discovered):
                try:
                    result = _ingest_one(conn, doc, browser)
                    if result == "succeeded":
                        summary.succeeded += 1
                    else:
                        summary.skipped += 1
                except (FetchError, RuntimeError) as exc:
                    document_id = generate_document_id(
                        doc.regulator, doc.landing_url, doc.landing_url
                    )
                    _record_state(conn, document_id, "failed", None, error=str(exc))
                    summary.failed += 1

                if i < len(discovered) - 1:
                    time.sleep(settings.ingestion_request_delay_seconds)
        finally:
            browser.close()

    return summary
