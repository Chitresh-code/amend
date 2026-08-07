from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from psycopg import AsyncConnection

from app.auth.api_keys import resolve_api_key
from app.auth.csrf import CSRF_HEADER_NAME, csrf_token_valid
from app.auth.sessions import resolve_session
from app.config import settings
from app.db import get_connection

UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass(frozen=True)
class AuthenticatedCaller:
    user_id: UUID
    email: str
    auth_method: Literal["session", "api_key"]


async def get_current_caller(
    request: Request,
    conn: AsyncConnection = Depends(get_connection),
) -> AuthenticatedCaller:
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        raw_key = auth_header[len("Bearer ") :].strip()
        api_user = await resolve_api_key(conn, raw_key)
        if api_user is None:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return AuthenticatedCaller(
            user_id=api_user.user_id, email=api_user.email, auth_method="api_key"
        )

    session_token = request.cookies.get(settings.session_cookie_name)
    if session_token:
        session_user = await resolve_session(conn, session_token)
        if session_user is None:
            raise HTTPException(status_code=401, detail="Session expired or invalid")

        if request.method in UNSAFE_METHODS:
            csrf_cookie = request.cookies.get(settings.csrf_cookie_name)
            csrf_header = request.headers.get(CSRF_HEADER_NAME)
            if not csrf_token_valid(csrf_cookie, csrf_header):
                raise HTTPException(status_code=403, detail="CSRF check failed")

        return AuthenticatedCaller(
            user_id=session_user.user_id, email=session_user.email, auth_method="session"
        )

    raise HTTPException(status_code=401, detail="Authentication required")
