import redis.asyncio as redis

from app.config import settings

_client: redis.Redis | None = None


def open_redis() -> None:
    # Same reasoning as app/db.py's pool: the client holds connections bound
    # to the event loop it was created on, so it is (re)created per app
    # lifespan rather than once at import time.
    global _client
    _client = redis.from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def get_redis_client() -> redis.Redis:
    assert _client is not None, "redis client not open; call open_redis() first"
    return _client
