from datetime import datetime

from pydantic import BaseModel


class ApiKeyResponse(BaseModel):
    id: str
    label: str
    key_suffix: str
    created_at: datetime
