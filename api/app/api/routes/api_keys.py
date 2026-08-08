from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

from app.api.dependencies import AuthenticatedCaller, get_current_caller
from app.db import get_connection
from app.schemas.api_keys import ApiKeyResponse

router = APIRouter(prefix="/v1/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    caller: AuthenticatedCaller = Depends(get_current_caller),
    conn: AsyncConnection = Depends(get_connection),
) -> list[ApiKeyResponse]:
    rows = await (
        await conn.execute(
            "SELECT id, label, key_suffix, created_at FROM api_keys "
            "WHERE user_id = %s AND revoked_at IS NULL ORDER BY created_at",
            (caller.user_id,),
        )
    ).fetchall()
    return [
        ApiKeyResponse(id=str(key_id), label=label, key_suffix=suffix, created_at=created_at)
        for key_id, label, suffix, created_at in rows
    ]


@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: UUID,
    caller: AuthenticatedCaller = Depends(get_current_caller),
    conn: AsyncConnection = Depends(get_connection),
) -> None:
    result = await conn.execute(
        "UPDATE api_keys SET revoked_at = now() "
        "WHERE user_id = %s AND id = %s AND revoked_at IS NULL",
        (caller.user_id, key_id),
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="API key not found")
