import hashlib
import hmac

from psycopg import AsyncConnection

from app.auth.sessions import SessionUser
from app.config import settings


def hash_api_key(raw_key: str) -> str:
    return hmac.new(
        settings.api_key_hash_pepper.encode(), raw_key.encode(), hashlib.sha256
    ).hexdigest()


async def resolve_api_key(conn: AsyncConnection, raw_key: str) -> SessionUser | None:
    key_hash = hash_api_key(raw_key)
    row = await (
        await conn.execute(
            """
            SELECT u.id, u.email
            FROM api_keys k
            JOIN users u ON u.id = k.user_id
            WHERE k.key_hash = %s
              AND k.revoked_at IS NULL
              AND u.disabled_at IS NULL
            """,
            (key_hash,),
        )
    ).fetchone()
    if row is None:
        return None
    user_id, email = row
    return SessionUser(user_id=user_id, email=email)
