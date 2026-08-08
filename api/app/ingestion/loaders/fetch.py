import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from playwright.sync_api import Browser, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from app.config import settings

# A real browser identity, not just for RBI: some regulator PDF servers apply
# bot mitigation that also inspects the user agent string.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class FetchError(Exception):
    pass


_TRANSIENT_RETRY_ATTEMPTS = 3
_TRANSIENT_RETRY_DELAY_SECONDS = 1.0


def _with_retries[T](fn: Callable[[], T]) -> T:
    # Confirmed against the live SEBI site: a handful of documents in a ~500-doc
    # run hit a transient "peer closed connection" (httpx.RemoteProtocolError,
    # a TransportError subclass). Not retried: HTTPStatusError (a real 4xx/5xx),
    # which no amount of retrying fixes.
    last_exc: httpx.TransportError | None = None
    for attempt in range(_TRANSIENT_RETRY_ATTEMPTS):
        try:
            return fn()
        except httpx.TransportError as exc:
            last_exc = exc
            if attempt < _TRANSIENT_RETRY_ATTEMPTS - 1:
                time.sleep(_TRANSIENT_RETRY_DELAY_SECONDS * (attempt + 1))
    assert last_exc is not None
    raise last_exc


@dataclass(frozen=True)
class FetchedDocument:
    content: bytes
    checksum: str
    retrieved_at: datetime


def _host_allowed(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(
        host == domain or host.endswith(f".{domain}")
        for domain in settings.ingestion_url_allowlist_list
    )


def _check_host(response: httpx.Response) -> None:
    # Runs on every response in the redirect chain, before httpx follows the next
    # hop, so a redirect to a disallowed host is rejected before its body is read.
    if not _host_allowed(str(response.url)):
        raise FetchError(f"disallowed host in redirect chain: {response.url}")


def _checksum(content: bytes) -> FetchedDocument:
    return FetchedDocument(
        content=content,
        checksum=hashlib.sha256(content).hexdigest(),
        retrieved_at=datetime.now(UTC),
    )


def _fetch_via_httpx(url: str, client: httpx.Client) -> bytes:
    with client.stream("GET", url) as response:
        response.raise_for_status()
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > settings.ingestion_max_document_size_bytes:
                raise FetchError(
                    f"{url} exceeds max document size "
                    f"({settings.ingestion_max_document_size_bytes} bytes)"
                )
            chunks.append(chunk)
    return b"".join(chunks)


def _download_with_browser(url: str, browser: Browser) -> bytes:
    page = browser.new_page(user_agent=USER_AGENT)
    try:
        with page.expect_download(timeout=30_000) as download_info:
            try:
                page.goto(url, timeout=30_000)
            except PlaywrightError:
                pass  # a same-navigation download always raises here; expected
        download = download_info.value
        path = download.path()
        if path is None:
            raise FetchError(f"browser download for {url} produced no file")
        content = path.read_bytes()
        if len(content) > settings.ingestion_max_document_size_bytes:
            raise FetchError(
                f"{url} exceeds max document size "
                f"({settings.ingestion_max_document_size_bytes} bytes)"
            )
        return content
    finally:
        page.close()


def _fetch_via_browser(url: str, browser: Browser | None) -> bytes:
    # Some regulator document servers (confirmed: rbidocs.rbi.org.in) sit behind
    # bot mitigation (an F5 TSPD JS challenge) that a plain HTTP client can't pass.
    # A real browser engine executes the challenge automatically; httpx can't.
    # Callers doing many fetches in one run (see app/ingestion/run.py) should pass
    # a shared `browser` so each document doesn't pay browser-launch overhead.
    if browser is not None:
        return _download_with_browser(url, browser)
    with sync_playwright() as p:
        launched = p.chromium.launch()
        try:
            return _download_with_browser(url, launched)
        finally:
            launched.close()


def fetch_html(url: str, *, client: httpx.Client | None = None) -> str:
    if not _host_allowed(url):
        raise FetchError(f"{url} is not on the ingestion URL allowlist")

    owns_client = client is None
    client = client or httpx.Client(
        follow_redirects=True,
        timeout=30.0,
        headers={"User-Agent": USER_AGENT},
        event_hooks={"response": [_check_host]},
    )
    try:
        response = _with_retries(lambda: client.get(url))
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as exc:
        raise FetchError(f"failed to fetch {url}: {exc}") from exc
    finally:
        if owns_client:
            client.close()


def fetch_document(
    url: str, *, client: httpx.Client | None = None, browser: Browser | None = None
) -> FetchedDocument:
    if not _host_allowed(url):
        raise FetchError(f"{url} is not on the ingestion URL allowlist")

    owns_client = client is None
    client = client or httpx.Client(
        follow_redirects=True,
        timeout=30.0,
        headers={"User-Agent": USER_AGENT},
        event_hooks={"response": [_check_host]},
    )
    try:
        try:
            content = _with_retries(lambda: _fetch_via_httpx(url, client))
        except httpx.HTTPError as exc:
            raise FetchError(f"failed to fetch {url}: {exc}") from exc

        if not content.startswith(b"%PDF-"):
            content = _fetch_via_browser(url, browser)
            if not content.startswith(b"%PDF-"):
                raise FetchError(f"{url} did not resolve to a PDF even via browser fetch")
    finally:
        if owns_client:
            client.close()

    return _checksum(content)
