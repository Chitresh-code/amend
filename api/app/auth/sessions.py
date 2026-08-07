import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from psycopg import AsyncConnection

from app.config import settings


@dataclass(frozen=True)
class SessionUser:
    user_id: UUID
    email: str
    organization: str | None


def _hash_token(raw_token: str, pepper: str) -> str:
    return hmac.new(pepper.encode(), raw_token.encode(), hashlib.sha256).hexdigest()


def hash_session_token(raw_token: str) -> str:
    return _hash_token(raw_token, settings.session_token_pepper)


async def create_session(conn: AsyncConnection, user_id: UUID) -> tuple[str, datetime]:
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_session_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
    await conn.execute(
        "INSERT INTO user_sessions (user_id, token_hash, expires_at) VALUES (%s, %s, %s)",
        (user_id, token_hash, expires_at),
    )
    return raw_token, expires_at


async def resolve_session(conn: AsyncConnection, raw_token: str) -> SessionUser | None:
    token_hash = hash_session_token(raw_token)
    row = await (
        await conn.execute(
            """
            SELECT s.id, u.id, u.email, u.organization
            FROM user_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = %s
              AND s.revoked_at IS NULL
              AND s.expires_at > now()
              AND u.disabled_at IS NULL
            """,
            (token_hash,),
        )
    ).fetchone()
    if row is None:
        return None

    session_id, user_id, email, organization = row
    new_expires_at = datetime.now(UTC) + timedelta(hours=settings.session_ttl_hours)
    await conn.execute(
        "UPDATE user_sessions SET last_seen_at = now(), expires_at = %s WHERE id = %s",
        (new_expires_at, session_id),
    )
    return SessionUser(user_id=user_id, email=email, organization=organization)


async def revoke_session(conn: AsyncConnection, raw_token: str) -> None:
    token_hash = hash_session_token(raw_token)
    await conn.execute(
        "UPDATE user_sessions SET revoked_at = now() WHERE token_hash = %s AND revoked_at IS NULL",
        (token_hash,),
    )
