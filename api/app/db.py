from collections.abc import AsyncIterator

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from app.config import settings

_pool: AsyncConnectionPool | None = None


async def open_pool() -> None:
    # A closed AsyncConnectionPool cannot be reopened, so each call builds a
    # fresh instance bound to the caller's current event loop. This matters
    # for tests: every `with TestClient(app)` block runs its own event loop
    # via the app's lifespan, so the pool must be (re)created inside it.
    global _pool
    _pool = AsyncConnectionPool(conninfo=settings.postgres_dsn, open=False)
    await _pool.open(wait=True)


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def get_connection() -> AsyncIterator[AsyncConnection]:
    assert _pool is not None, "connection pool not open; call open_pool() first"
    async with _pool.connection() as conn:
        yield conn
