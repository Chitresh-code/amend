from datetime import datetime

from pydantic import BaseModel


class CredentialCreateRequest(BaseModel):
    provider: str
    model_id: str
    api_key: str


class CredentialResponse(BaseModel):
    provider: str
    model_id: str
    configured: bool = True
    key_suffix: str
    is_default: bool
    created_at: datetime


class CredentialUpdateRequest(BaseModel):
    is_default: bool
