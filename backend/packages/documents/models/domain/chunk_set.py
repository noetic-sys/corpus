"""Domain models for chunk sets."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ChunkSetModel(BaseModel):
    """Chunk set domain model."""

    id: int
    document_id: int
    company_id: int
    chunking_strategy: str
    total_chunks: int
    s3_prefix: str
    deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChunkSetCreateModel(BaseModel):
    """Model for creating a chunk set."""

    document_id: int
    company_id: int
    chunking_strategy: str = Field(default="agent_v1")
    total_chunks: int
    s3_prefix: str


class ChunkSetUpdateModel(BaseModel):
    """Model for updating a chunk set."""

    total_chunks: Optional[int] = None
    deleted: Optional[bool] = None
