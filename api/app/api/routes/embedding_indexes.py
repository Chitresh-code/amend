from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection
from psycopg.errors import UniqueViolation

from app.api.dependencies import AuthenticatedCaller, get_current_caller
from app.db import get_connection
from app.schemas.embedding_indexes import (
    EmbeddingIndexCreateRequest,
    EmbeddingIndexResponse,
    EmbeddingIndexUpdateRequest,
)

router = APIRouter(prefix="/v1/embedding-indexes", tags=["embedding-indexes"])


def _to_response(row: tuple[str, str, str, str, bool]) -> EmbeddingIndexResponse:
    embedding_model_id, provider, model_id, status, is_default = row
    # ponytail: clause_count is always 0 until the offline index-build step (PRD
    # §75) and its per-model clause_embeddings_<slug> tables exist to count from.
    return EmbeddingIndexResponse(
        embedding_model_id=embedding_model_id,
        provider=provider,
        model_id=model_id,
        status=status,
        clause_count=0,
        is_default=is_default,
    )


@router.get("", response_model=list[EmbeddingIndexResponse])
async def list_embedding_indexes(
    _: AuthenticatedCaller = Depends(get_current_caller),
    conn: AsyncConnection = Depends(get_connection),
) -> list[EmbeddingIndexResponse]:
    rows = await (
        await conn.execute(
            "SELECT embedding_model_id, provider, model_id, status, is_default "
            "FROM embedding_models ORDER BY created_at"
        )
    ).fetchall()
    return [_to_response(row) for row in rows]


@router.post("", response_model=EmbeddingIndexResponse, status_code=201)
async def register_embedding_index(
    body: EmbeddingIndexCreateRequest,
    _: AuthenticatedCaller = Depends(get_current_caller),
    conn: AsyncConnection = Depends(get_connection),
) -> EmbeddingIndexResponse:
    embedding_model_id = f"{body.provider}:{body.model_id}"
    try:
        row = await (
            await conn.execute(
                """
                INSERT INTO embedding_models (embedding_model_id, provider, model_id, dimension)
                VALUES (%s, %s, %s, %s)
                RETURNING embedding_model_id, provider, model_id, status, is_default
                """,
                (embedding_model_id, body.provider, body.model_id, body.dimension),
            )
        ).fetchone()
    except UniqueViolation as exc:
        raise HTTPException(
            status_code=409, detail=f"{embedding_model_id} is already registered"
        ) from exc
    assert row is not None
    return _to_response(row)


@router.patch("/{embedding_model_id:path}", response_model=EmbeddingIndexResponse)
async def set_default_embedding_index(
    embedding_model_id: str,
    body: EmbeddingIndexUpdateRequest,
    _: AuthenticatedCaller = Depends(get_current_caller),
    conn: AsyncConnection = Depends(get_connection),
) -> EmbeddingIndexResponse:
    if not body.is_default:
        raise HTTPException(status_code=400, detail="is_default must be true")

    status_row = await (
        await conn.execute(
            "SELECT status FROM embedding_models WHERE embedding_model_id = %s",
            (embedding_model_id,),
        )
    ).fetchone()
    if status_row is None:
        raise HTTPException(status_code=404, detail="Embedding index not found")
    if status_row[0] != "ready":
        raise HTTPException(
            status_code=400, detail="Only a ready embedding index can be set as default"
        )

    async with conn.transaction():
        await conn.execute("UPDATE embedding_models SET is_default = false")
        row = await (
            await conn.execute(
                """
                UPDATE embedding_models SET is_default = true
                WHERE embedding_model_id = %s
                RETURNING embedding_model_id, provider, model_id, status, is_default
                """,
                (embedding_model_id,),
            )
        ).fetchone()
    assert row is not None
    return _to_response(row)
