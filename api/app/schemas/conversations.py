from datetime import datetime

from pydantic import BaseModel


class ConversationResponse(BaseModel):
    conversation_id: str
    title: str | None
    pinned: bool
    last_active_at: datetime


class ConversationUpdateRequest(BaseModel):
    pinned: bool | None = None
    title: str | None = None
