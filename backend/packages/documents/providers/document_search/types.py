from enum import StrEnum
from typing import List, Optional, Dict, Any


class DocumentSearchProvider(StrEnum):
    """Document search provider types."""

    POSTGRES = "postgres"
    ELASTICSEARCH = "elasticsearch"


class KeywordSearchProvider(StrEnum):
    """Keyword search provider types."""

    ELASTICSEARCH = "elasticsearch"
    POSTGRES = "postgres"


class VectorSearchProvider(StrEnum):
    """Vector search provider types."""

    ELASTICSEARCH = "elasticsearch"


class ChunkSearchHit:
    """Individual chunk search result with score and metadata."""

    def __init__(
        self,
        chunk_id: str,
        document_id: int,
        company_id: int,
        content: str,
        metadata: Dict[str, Any],
        score: float,
        highlights: Optional[List[str]] = None,
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.company_id = company_id
        self.content = content
        self.metadata = metadata
        self.score = score
        self.highlights = highlights or []


class ChunkSearchResult:
    """Container for chunk search results with metadata."""

    def __init__(self, chunks: List[ChunkSearchHit], total_count: int, has_more: bool):
        self.chunks = chunks
        self.total_count = total_count
        self.has_more = has_more


class ChunkSearchFilters:
    """Search filters for chunk queries."""

    def __init__(
        self,
        company_id: int,
        document_ids: Optional[List[int]] = None,
        matrix_id: Optional[int] = None,
        entity_set_id: Optional[int] = None,
        query_vector: Optional[List[float]] = None,
    ):
        self.company_id = company_id
        self.document_ids = document_ids
        self.matrix_id = matrix_id
        self.entity_set_id = entity_set_id
        self.query_vector = query_vector
