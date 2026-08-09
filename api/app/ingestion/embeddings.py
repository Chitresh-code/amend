import time
from collections.abc import Callable

import httpx

# base_url matches the OpenAI SDK's own convention (the API root, not the full
# endpoint) so the same value works for OpenAI itself, OpenRouter
# ("https://openrouter.ai/api/v1", model_id "openai/text-embedding-3-large"),
# Azure OpenAI, or a self-hosted OpenAI-compatible proxy.
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"

# ponytail: char-based approximation of OpenAI's per-input (8,192 token) and
# per-request (300,000 token) caps, ~4 chars/token, not a real tokenizer. Real
# clause text is tiny (p99 ~7.5k chars across the real corpus); this only
# bites the rare mis-segmented outlier clause. Swap in tiktoken if this ever
# undercounts against the real API.
_MAX_INPUT_CHARS = 32_000
_MAX_BATCH_ITEMS = 100
_MAX_BATCH_CHARS = 200_000

_RETRY_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 2.0


class EmbeddingError(Exception):
    pass


def _with_retries[T](fn: Callable[[], T]) -> T:
    last_exc: httpx.TransportError | httpx.HTTPStatusError | None = None
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            return fn()
        except httpx.TransportError as exc:
            last_exc = exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 429:
                raise
            last_exc = exc
        if attempt < _RETRY_ATTEMPTS - 1:
            time.sleep(_RETRY_DELAY_SECONDS * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def _embed_openai(
    texts: list[str],
    model_id: str,
    api_key: str,
    client: httpx.Client,
    dimensions: int | None,
    base_url: str | None,
) -> list[list[float]]:
    truncated = [t[:_MAX_INPUT_CHARS] for t in texts]
    payload: dict[str, object] = {"model": model_id, "input": truncated}
    if dimensions is not None:
        payload["dimensions"] = dimensions

    def _post() -> httpx.Response:
        response = client.post(
            f"{base_url or DEFAULT_OPENAI_BASE_URL}/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        response.raise_for_status()
        return response

    response = _with_retries(_post)
    data = response.json()["data"]
    return [item["embedding"] for item in data]


_PROVIDERS: dict[
    str,
    Callable[[list[str], str, str, httpx.Client, int | None, str | None], list[list[float]]],
] = {
    "openai": _embed_openai,
}


def _chunk_by_budget(texts: list[str]) -> list[list[str]]:
    chunks: list[list[str]] = []
    current: list[str] = []
    current_chars = 0
    for text in texts:
        truncated_len = min(len(text), _MAX_INPUT_CHARS)
        if current and (
            len(current) >= _MAX_BATCH_ITEMS or current_chars + truncated_len > _MAX_BATCH_CHARS
        ):
            chunks.append(current)
            current, current_chars = [], 0
        current.append(text)
        current_chars += truncated_len
    if current:
        chunks.append(current)
    return chunks


def embed_batch(
    texts: list[str],
    *,
    provider: str,
    model_id: str,
    api_key: str,
    dimensions: int | None = None,
    base_url: str | None = None,
    client: httpx.Client | None = None,
) -> list[list[float]]:
    if provider not in _PROVIDERS:
        raise EmbeddingError(f"unsupported embedding provider: {provider}")
    if not texts:
        return []

    owns_client = client is None
    client = client or httpx.Client(timeout=60.0)
    try:
        results: list[list[float]] = []
        for chunk in _chunk_by_budget(texts):
            results.extend(
                _PROVIDERS[provider](chunk, model_id, api_key, client, dimensions, base_url)
            )
        return results
    finally:
        if owns_client:
            client.close()
