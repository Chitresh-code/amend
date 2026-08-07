from pydantic import BaseModel, Field


class EmbeddingIndexResponse(BaseModel):
    embedding_model_id: str
    provider: str
    model_id: str
    status: str
    clause_count: int
    is_default: bool


class EmbeddingIndexCreateRequest(BaseModel):
    provider: str
    model_id: str
    dimension: int = Field(gt=0)


class EmbeddingIndexUpdateRequest(BaseModel):
    is_default: bool
