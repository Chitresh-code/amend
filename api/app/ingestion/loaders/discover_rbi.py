import re

import httpx
from bs4 import BeautifulSoup

from app.ingestion.loaders.discovery import DiscoveredDocument
from app.ingestion.loaders.fetch import USER_AGENT

LISTING_URL = "https://rbi.org.in/Scripts/BS_ViewMasDirections.aspx"
_DOC_LINK_RE = re.compile(r"BS_ViewMasDirections\.aspx\?id=(\d+)")
# The real document PDF sits under /notification/PDFs/; banner/chrome PDFs elsewhere
# on the page (e.g. /content/pdfs/) are not the document and must not be picked up.
_DOC_PDF_RE = re.compile(r"https://rbidocs\.rbi\.org\.in/rdocs/notification/PDFs/[^\"'\s]+", re.I)


def discover_rbi(client: httpx.Client | None = None) -> list[DiscoveredDocument]:
    owns_client = client is None
    client = client or httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT})
    try:
        response = client.get(LISTING_URL)
        response.raise_for_status()
        return _parse_listing(response.text)
    finally:
        if owns_client:
            client.close()


def _parse_listing(html: str) -> list[DiscoveredDocument]:
    soup = BeautifulSoup(html, "html.parser")
    documents: list[DiscoveredDocument] = []
    seen_ids: set[str] = set()
    current_date_text: str | None = None

    for row in soup.find_all("tr"):
        header_cell = row.find("td", class_="tableheader")
        if header_cell is not None:
            current_date_text = header_cell.get_text(strip=True) or current_date_text
            continue

        for link in row.find_all("a", class_="link2", href=True):
            match = _DOC_LINK_RE.search(str(link["href"]))
            if match is None:
                continue
            doc_id = match.group(1)
            if doc_id in seen_ids:
                continue
            seen_ids.add(doc_id)
            documents.append(
                DiscoveredDocument(
                    regulator="RBI",
                    document_type="master_direction",
                    title=link.get_text(strip=True),
                    publication_date_text=current_date_text,
                    landing_url=f"{LISTING_URL}?id={doc_id}",
                )
            )

    return documents


def resolve_pdf_url(detail_page_html: str) -> str | None:
    match = _DOC_PDF_RE.search(detail_page_html)
    return match.group(0) if match else None
