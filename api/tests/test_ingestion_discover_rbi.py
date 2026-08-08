from pathlib import Path

from app.ingestion.loaders.discover_rbi import _parse_listing, resolve_pdf_url

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8", errors="ignore")


def test_parse_listing_extracts_all_documents_deduped():
    documents = _parse_listing(_load("rbi_listing_page.html"))
    assert len(documents) == 411
    assert all(d.regulator == "RBI" for d in documents)
    landing_urls = {d.landing_url for d in documents}
    assert len(landing_urls) == len(documents)


def test_parse_listing_associates_dates_from_header_rows():
    documents = _parse_listing(_load("rbi_listing_page.html"))
    with_date = [d for d in documents if d.publication_date_text]
    assert len(with_date) == len(documents)


def test_resolve_pdf_url_finds_notification_pdf_not_banner_pdfs():
    pdf_url = resolve_pdf_url(_load("rbi_detail_page.html"))
    assert pdf_url is not None
    assert "/rdocs/notification/PDFs/" in pdf_url
    assert "content/pdfs" not in pdf_url.lower()
