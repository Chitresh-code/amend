from redis.asyncio import Redis

from app.config import settings


async def login_attempt_allowed(redis_client: Redis, source_ip: str) -> bool:
    """Fixed-window counter: allows the first N attempts per IP per window."""
    key = f"login_attempts:{source_ip}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, settings.login_rate_limit_window_seconds)
    return count <= settings.login_rate_limit_attempts
