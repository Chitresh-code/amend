import json

import httpx
import pytest

from app.ingestion.embeddings import (
    DEFAULT_OPENAI_BASE_URL,
    EmbeddingError,
    _chunk_by_budget,
    embed_batch,
)


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_embed_batch_returns_vectors_in_order():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.read())
        return httpx.Response(
            200,
            json={
                "data": [
                    {"embedding": [float(i), float(len(t))]} for i, t in enumerate(payload["input"])
                ]
            },
        )

    vectors = embed_batch(
        ["alpha", "beta"],
        provider="openai",
        model_id="text-embedding-3-large",
        api_key="sk-test",
        client=_client(handler),
    )
    assert vectors == [[0.0, 5.0], [1.0, 4.0]]


def test_embed_batch_empty_input_makes_no_request():
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("should not be called for empty input")

    assert (
        embed_batch([], provider="openai", model_id="m", api_key="k", client=_client(handler)) == []
    )


def test_embed_batch_unsupported_provider_raises():
    with pytest.raises(EmbeddingError):
        embed_batch(["x"], provider="voyage", model_id="m", api_key="k")


def test_embed_batch_retries_on_429_then_succeeds():
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 2:
            return httpx.Response(429, json={"error": "rate limited"})
        return httpx.Response(200, json={"data": [{"embedding": [1.0, 2.0]}]})

    vectors = embed_batch(
        ["x"], provider="openai", model_id="m", api_key="k", client=_client(handler)
    )
    assert vectors == [[1.0, 2.0]]
    assert attempts["count"] == 2


def test_embed_batch_does_not_retry_non_429_http_errors():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "bad request"})

    with pytest.raises(httpx.HTTPStatusError):
        embed_batch(["x"], provider="openai", model_id="m", api_key="k", client=_client(handler))


def test_chunk_by_budget_splits_on_item_count():
    texts = ["a"] * 250
    chunks = _chunk_by_budget(texts)
    assert sum(len(c) for c in chunks) == 250
    assert all(len(c) <= 100 for c in chunks)


def test_chunk_by_budget_respects_char_budget():
    texts = ["x" * 30_000] * 10  # 300k chars total, well under the 100-item cap
    chunks = _chunk_by_budget(texts)
    assert sum(len(c) for c in chunks) == 10
    assert len(chunks) > 1
    for chunk in chunks:
        assert sum(len(t) for t in chunk) <= 200_000


def test_embed_batch_truncates_oversized_input():
    seen_lengths = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.read())
        seen_lengths.append(len(payload["input"][0]))
        return httpx.Response(200, json={"data": [{"embedding": [0.0]}]})

    embed_batch(
        ["x" * 50_000],
        provider="openai",
        model_id="m",
        api_key="k",
        client=_client(handler),
    )
    assert seen_lengths == [32_000]


def test_embed_batch_passes_dimensions_when_given():
    seen_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_payloads.append(json.loads(request.read()))
        return httpx.Response(200, json={"data": [{"embedding": [0.0]}]})

    embed_batch(
        ["x"],
        provider="openai",
        model_id="m",
        api_key="k",
        dimensions=1536,
        client=_client(handler),
    )
    assert seen_payloads[0]["dimensions"] == 1536


def test_embed_batch_omits_dimensions_when_not_given():
    seen_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_payloads.append(json.loads(request.read()))
        return httpx.Response(200, json={"data": [{"embedding": [0.0]}]})

    embed_batch(["x"], provider="openai", model_id="m", api_key="k", client=_client(handler))
    assert "dimensions" not in seen_payloads[0]


def test_embed_batch_uses_default_base_url_when_not_given():
    seen_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json={"data": [{"embedding": [0.0]}]})

    embed_batch(["x"], provider="openai", model_id="m", api_key="k", client=_client(handler))
    assert seen_urls == [f"{DEFAULT_OPENAI_BASE_URL}/embeddings"]


def test_embed_batch_routes_to_custom_base_url():
    seen_urls = []
    seen_models = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        seen_models.append(json.loads(request.read())["model"])
        return httpx.Response(200, json={"data": [{"embedding": [0.0]}]})

    embed_batch(
        ["x"],
        provider="openai",
        model_id="openai/text-embedding-3-large",
        api_key="k",
        base_url="https://openrouter.ai/api/v1",
        client=_client(handler),
    )
    assert seen_urls == ["https://openrouter.ai/api/v1/embeddings"]
    assert seen_models == ["openai/text-embedding-3-large"]
