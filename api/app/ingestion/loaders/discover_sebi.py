import re
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.ingestion.loaders.discovery import DiscoveredDocument
from app.ingestion.loaders.fetch import USER_AGENT

BASE_URL = "https://www.sebi.gov.in"
LISTING_URL = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do"
AJAX_URL = "https://www.sebi.gov.in/sebiweb/ajax/home/getnewslistinfo.jsp"
# sid/ssid/smid identify the "Legal > Master Circulars" section in SEBI's site nav.
MASTER_CIRCULARS_PARAMS = {"doListing": "yes", "sid": "1", "ssid": "6", "smid": "0"}
PAGE_SIZE = 25

_RECORD_COUNT_RE = re.compile(r"of\s+(\d+)\s+records")
# The PDF lives in an iframe's ?file= query param, not a plain <a href>, which is
# why a naive link scrape (or a summarized page-fetch tool) misses it.
_IFRAME_FILE_RE = re.compile(r"<iframe[^>]*\bsrc=['\"][^'\"]*\?file=([^'\"]+)['\"]")


def _parse_listing_rows(html: str) -> list[DiscoveredDocument]:
    soup = BeautifulSoup(html, "html.parser")
    documents = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) != 2:
            continue
        link = cells[1].find("a", href=True)
        if link is None:
            continue
        documents.append(
            DiscoveredDocument(
                regulator="SEBI",
                document_type="master_circular",
                title=link.get_text(strip=True),
                publication_date_text=cells[0].get_text(strip=True),
                landing_url=str(link["href"]),
            )
        )
    return documents


def _total_record_count(html: str) -> int | None:
    match = _RECORD_COUNT_RE.search(html)
    return int(match.group(1)) if match else None


def discover_sebi(client: httpx.Client | None = None) -> list[DiscoveredDocument]:
    owns_client = client is None
    client = client or httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT})
    try:
        first_page = client.get(LISTING_URL, params=MASTER_CIRCULARS_PARAMS)
        first_page.raise_for_status()
        documents = _parse_listing_rows(first_page.text)

        total_records = _total_record_count(first_page.text) or len(documents)
        total_pages = -(-total_records // PAGE_SIZE)  # ceil division

        for page_index in range(1, total_pages):
            # doDirect is the real page selector; nextValue just needs to be a
            # positive integer (confirmed against the live site during planning).
            response = client.post(
                AJAX_URL,
                data={
                    "nextValue": str(page_index),
                    "next": "n",
                    "search": "",
                    "fromDate": "",
                    "toDate": "",
                    "fromYear": "",
                    "toYear": "",
                    "deptId": "",
                    "sid": MASTER_CIRCULARS_PARAMS["sid"],
                    "ssid": MASTER_CIRCULARS_PARAMS["ssid"],
                    "smid": MASTER_CIRCULARS_PARAMS["smid"],
                    "ssidhidden": "",
                    "intmid": "-1",
                    "sText": "",
                    "ssText": "",
                    "smText": "",
                    "doDirect": str(page_index),
                },
                headers={
                    "Referer": f"{LISTING_URL}?doListing=yes&sid=1&ssid=6&smid=0",
                },
            )
            response.raise_for_status()
            documents.extend(_parse_listing_rows(response.text))

        return documents
    finally:
        if owns_client:
            client.close()


def resolve_pdf_url(landing_page_html: str) -> str | None:
    match = _IFRAME_FILE_RE.search(landing_page_html)
    if match is None:
        return None
    # Older pages (pre-~2011) embed a relative path here; newer ones an absolute
    # URL. urljoin resolves both correctly, returning an absolute URL either way.
    return urljoin(BASE_URL, str(match.group(1)))
