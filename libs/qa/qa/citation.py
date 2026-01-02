from datetime import datetime
from typing import List

from pydantic import BaseModel


class CitationModel(BaseModel):
    """Domain model for a single citation."""

    id: int
    citation_set_id: int
    document_id: int
    company_id: int
    quote_text: str  # Exact text from document for highlighting
    citation_order: int  # For [[cite:1]], [[cite:2]] ordering
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CitationCreateWithoutSetIdModel(BaseModel):
    """Model for creating a new citation without citation_set_id (used when creating citation set + citations together)."""

    document_id: int
    company_id: int
    quote_text: str  # Must match document text exactly
    citation_order: int


class CitationCreateModel(BaseModel):
    """Model for creating a new citation with citation_set_id."""

    citation_set_id: int
    document_id: int
    company_id: int
    quote_text: str  # Must match document text exactly
    citation_order: int


class CitationSetModel(BaseModel):
    """Domain model for a citation set."""

    id: int
    answer_id: int
    company_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CitationSetWithCitationsModel(BaseModel):
    """Domain model for a citation set with citations loaded."""

    id: int
    answer_id: int
    company_id: int
    citations: List[CitationModel] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CitationSetCreateOnlyModel(BaseModel):
    """Model for creating a new citation set without citations."""

    answer_id: int
    company_id: int


class CitationSetCreateModel(BaseModel):
    """Model for creating a new citation set with citations."""

    answer_id: int
    company_id: int
    citations: List[CitationCreateWithoutSetIdModel]


class CitationReference(BaseModel):
    """Model for inline citation references in answer text."""

    citation_number: int  # [1], [2], etc.
    quote_text: str  # Exact quote from document
    document_id: int
