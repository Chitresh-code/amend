from fastapi import APIRouter, Depends, HTTPException, Request, Response
from psycopg import AsyncConnection

from app.api.dependencies import AuthenticatedCaller, get_current_caller
from app.auth.csrf import generate_csrf_token
from app.auth.passwords import hash_password, verify_password
from app.auth.rate_limit import login_attempt_allowed
from app.auth.sessions import create_session, revoke_session
from app.config import settings
from app.db import get_connection
from app.redis import get_redis_client
from app.schemas.auth import LoginRequest, LoginResponse, SessionResponse

router = APIRouter(prefix="/v1/auth", tags=["auth"])

# Hashed once at import time and compared against on every login for an
# unknown email, so response latency does not reveal whether the address
# has an account (PRD §72's generic-401 requirement extended to timing).
_DUMMY_PASSWORD_HASH = hash_password("amend-dummy-password-for-timing-parity")


def _set_auth_cookies(response: Response, request: Request, session_token: str) -> None:
    secure = request.url.scheme == "https"
    response.set_cookie(
        settings.session_cookie_name,
        session_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )
    response.set_cookie(
        settings.csrf_cookie_name,
        generate_csrf_token(),
        httponly=False,
        secure=secure,
        samesite="lax",
        max_age=settings.session_ttl_hours * 3600,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    conn: AsyncConnection = Depends(get_connection),
) -> LoginResponse:
    source_ip = request.client.host if request.client else "unknown"
    if not await login_attempt_allowed(get_redis_client(), source_ip):
        raise HTTPException(status_code=429, detail="Too many login attempts, try again later")

    row = await (
        await conn.execute(
            "SELECT id, email, password_hash, organization FROM users "
            "WHERE email = %s AND disabled_at IS NULL",
            (body.email,),
        )
    ).fetchone()

    if row is None:
        verify_password(_DUMMY_PASSWORD_HASH, body.password)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id, email, password_hash, organization = row
    if not verify_password(password_hash, body.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session_token, _ = await create_session(conn, user_id)
    _set_auth_cookies(response, request, session_token)

    return LoginResponse(user_id=str(user_id), email=email, organization=organization)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    conn: AsyncConnection = Depends(get_connection),
) -> None:
    session_token = request.cookies.get(settings.session_cookie_name)
    if session_token:
        await revoke_session(conn, session_token)
    _clear_auth_cookies(response)


@router.get("/session", response_model=SessionResponse)
async def get_session(
    caller: AuthenticatedCaller = Depends(get_current_caller),
) -> SessionResponse:
    return SessionResponse(
        user_id=str(caller.user_id), email=caller.email, organization=caller.organization
    )
