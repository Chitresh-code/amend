from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

from app.api.dependencies import AuthenticatedCaller, get_current_caller
from app.config import settings
from app.credentials import encrypt_key, key_suffix
from app.db import get_connection
from app.schemas.credentials import (
    CredentialCreateRequest,
    CredentialResponse,
    CredentialUpdateRequest,
)

router = APIRouter(prefix="/v1/credentials", tags=["credentials"])


@router.post("", response_model=CredentialResponse)
async def create_or_update_credential(
    body: CredentialCreateRequest,
    caller: AuthenticatedCaller = Depends(get_current_caller),
    conn: AsyncConnection = Depends(get_connection),
) -> CredentialResponse:
    if body.provider not in settings.enabled_model_providers_list:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {body.provider}")

    count_row = await (
        await conn.execute(
            "SELECT count(*) FROM model_credentials WHERE user_id = %s", (caller.user_id,)
        )
    ).fetchone()
    assert count_row is not None
    is_default = count_row[0] == 0

    row = await (
        await conn.execute(
            """
            INSERT INTO model_credentials
                (user_id, provider, model_id, encrypted_key, key_suffix, is_default)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, provider) DO UPDATE SET
                model_id = EXCLUDED.model_id,
                encrypted_key = EXCLUDED.encrypted_key,
                key_suffix = EXCLUDED.key_suffix,
                updated_at = now()
            RETURNING provider, model_id, key_suffix, is_default, created_at
            """,
            (
                caller.user_id,
                body.provider,
                body.model_id,
                encrypt_key(body.api_key),
                key_suffix(body.api_key),
                is_default,
            ),
        )
    ).fetchone()
    assert row is not None

    provider, model_id, suffix, default_flag, created_at = row
    return CredentialResponse(
        provider=provider,
        model_id=model_id,
        key_suffix=suffix,
        is_default=default_flag,
        created_at=created_at,
    )


@router.get("", response_model=list[CredentialResponse])
async def list_credentials(
    caller: AuthenticatedCaller = Depends(get_current_caller),
    conn: AsyncConnection = Depends(get_connection),
) -> list[CredentialResponse]:
    rows = await (
        await conn.execute(
            "SELECT provider, model_id, key_suffix, is_default, created_at "
            "FROM model_credentials WHERE user_id = %s ORDER BY created_at",
            (caller.user_id,),
        )
    ).fetchall()
    return [
        CredentialResponse(
            provider=provider,
            model_id=model_id,
            key_suffix=suffix,
            is_default=is_default,
            created_at=created_at,
        )
        for provider, model_id, suffix, is_default, created_at in rows
    ]


@router.patch("/{provider}", response_model=CredentialResponse)
async def set_default_credential(
    provider: str,
    body: CredentialUpdateRequest,
    caller: AuthenticatedCaller = Depends(get_current_caller),
    conn: AsyncConnection = Depends(get_connection),
) -> CredentialResponse:
    if not body.is_default:
        raise HTTPException(status_code=400, detail="is_default must be true")

    async with conn.transaction():
        await conn.execute(
            "UPDATE model_credentials SET is_default = false WHERE user_id = %s",
            (caller.user_id,),
        )
        row = await (
            await conn.execute(
                """
                UPDATE model_credentials SET is_default = true, updated_at = now()
                WHERE user_id = %s AND provider = %s
                RETURNING provider, model_id, key_suffix, is_default, created_at
                """,
                (caller.user_id, provider),
            )
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Credential not found")

    provider_out, model_id, suffix, is_default, created_at = row
    return CredentialResponse(
        provider=provider_out,
        model_id=model_id,
        key_suffix=suffix,
        is_default=is_default,
        created_at=created_at,
    )


@router.delete("/{provider}", status_code=204)
async def delete_credential(
    provider: str,
    caller: AuthenticatedCaller = Depends(get_current_caller),
    conn: AsyncConnection = Depends(get_connection),
) -> None:
    result = await conn.execute(
        "DELETE FROM model_credentials WHERE user_id = %s AND provider = %s",
        (caller.user_id, provider),
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Credential not found")
