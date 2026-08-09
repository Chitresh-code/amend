from datetime import datetime

from pydantic import BaseModel


class CredentialCreateRequest(BaseModel):
    provider: str
    model_id: str
    api_key: str
    # Routes provider's calls to an OpenAI-compatible host other than its own
    # default (OpenRouter, Azure OpenAI, a self-hosted proxy). Not a new
    # provider value; PRD §70.3.
    base_url: str | None = None


class CredentialResponse(BaseModel):
    provider: str
    model_id: str
    configured: bool = True
    key_suffix: str
    base_url: str | None = None
    is_default: bool
    created_at: datetime


class CredentialUpdateRequest(BaseModel):
    is_default: bool
