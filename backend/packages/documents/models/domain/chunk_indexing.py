"""Domain models for chunk indexing."""

from pydantic import BaseModel
from typing import Dict, Any, List


class ChunkIndexingModel(BaseModel):
    """Model for chunk data to be indexed."""

    chunk_id: str
    document_id: int
    company_id: int
    content: str
    metadata: Dict[str, Any]


class ChunkEmbeddingModel(BaseModel):
    """Model for chunk embedding data to be indexed."""

    chunk_id: str
    document_id: int
    company_id: int
    embedding: List[float]
    metadata: Dict[str, Any]
