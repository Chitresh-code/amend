from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from psycopg import AsyncConnection

from app.api.dependencies import AuthenticatedCaller, get_current_caller
from app.db import get_connection
from app.schemas.conversations import ConversationResponse, ConversationUpdateRequest

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
async def list_conversations(
    caller: AuthenticatedCaller = Depends(get_current_caller),
    conn: AsyncConnection = Depends(get_connection),
) -> list[ConversationResponse]:
    rows = await (
        await conn.execute(
            "SELECT conversation_id, title, pinned, last_active_at FROM conversations "
            "WHERE user_id = %s ORDER BY pinned DESC, last_active_at DESC",
            (caller.user_id,),
        )
    ).fetchall()
    return [
        ConversationResponse(
            conversation_id=str(conversation_id),
            title=title,
            pinned=pinned,
            last_active_at=last_active_at,
        )
        for conversation_id, title, pinned, last_active_at in rows
    ]


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: UUID,
    body: ConversationUpdateRequest,
    caller: AuthenticatedCaller = Depends(get_current_caller),
    conn: AsyncConnection = Depends(get_connection),
) -> ConversationResponse:
    row = await (
        await conn.execute(
            """
            UPDATE conversations
            SET pinned = COALESCE(%s, pinned), title = COALESCE(%s, title)
            WHERE user_id = %s AND conversation_id = %s
            RETURNING conversation_id, title, pinned, last_active_at
            """,
            (body.pinned, body.title, caller.user_id, conversation_id),
        )
    ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation_id_out, title, pinned, last_active_at = row
    return ConversationResponse(
        conversation_id=str(conversation_id_out),
        title=title,
        pinned=pinned,
        last_active_at=last_active_at,
    )


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: UUID,
    caller: AuthenticatedCaller = Depends(get_current_caller),
    conn: AsyncConnection = Depends(get_connection),
) -> None:
    result = await conn.execute(
        "DELETE FROM conversations WHERE user_id = %s AND conversation_id = %s",
        (caller.user_id, conversation_id),
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")
