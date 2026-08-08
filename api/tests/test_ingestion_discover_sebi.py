from pathlib import Path

from app.ingestion.loaders.discover_sebi import (
    _parse_listing_rows,
    _total_record_count,
    resolve_pdf_url,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8", errors="ignore")


def test_parse_listing_rows_extracts_documents():
    documents = _parse_listing_rows(_load("sebi_listing_page1.html"))
    assert len(documents) == 25
    assert all(d.regulator == "SEBI" for d in documents)
    assert all(d.landing_url.startswith("https://www.sebi.gov.in/") for d in documents)


def test_parse_listing_rows_handles_ajax_page():
    documents = _parse_listing_rows(_load("sebi_listing_ajax_page2.html"))
    assert len(documents) == 25


def test_total_record_count_parsed_from_listing_page():
    assert _total_record_count(_load("sebi_listing_page1.html")) == 133


def test_resolve_pdf_url_extracts_iframe_target():
    pdf_url = resolve_pdf_url(_load("sebi_landing_page.html"))
    assert pdf_url is not None
    assert pdf_url.startswith("https://www.sebi.gov.in/sebi_data/attachdocs/")
    assert pdf_url.endswith(".pdf")
