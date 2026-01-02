"""Domain models for chunks."""

from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel


class ChunkModel(BaseModel):
    """Chunk domain model."""

    id: int
    chunk_set_id: int
    chunk_id: str
    document_id: int
    company_id: int
    s3_key: str
    chunk_metadata: Dict[str, Any]
    chunk_order: int
    deleted: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChunkCreateModel(BaseModel):
    """Model for creating a chunk."""

    chunk_set_id: int
    chunk_id: str
    document_id: int
    company_id: int
    s3_key: str
    chunk_metadata: Dict[str, Any]
    chunk_order: int


class ChunkUpdateModel(BaseModel):
    """Model for updating a chunk."""

    deleted: Optional[bool] = None
