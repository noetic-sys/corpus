"""Domain models for document search results with content matching."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel

from packages.documents.models.domain.document import DocumentModel


class MatchType(str, Enum):
    """Type of match found in document search."""

    FILENAME = "filename"
    CONTENT = "content"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    FILENAME_AND_CONTENT = "filename_and_content"


class DocumentMatchSnippet(BaseModel):
    """A matching snippet from document content."""

    chunk_id: str
    content: str
    score: float
    metadata: dict


class DocumentMatchData(BaseModel):
    """Intermediate model for building document search hits."""

    document_id: int
    best_score: float
    match_type: MatchType
    snippets: List[DocumentMatchSnippet]
    document: Optional[DocumentModel] = None


class DocumentSearchHit(BaseModel):
    """Document search result with match context."""

    document: DocumentModel
    match_score: float
    match_type: MatchType
    snippets: List[DocumentMatchSnippet]


class HybridDocumentSearchResult(BaseModel):
    """Result of hybrid document search."""

    results: List[DocumentSearchHit]
    total_count: int
    has_more: bool
