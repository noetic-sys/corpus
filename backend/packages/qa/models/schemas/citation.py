from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CitationResponse(BaseModel):
    """Response schema for individual citations."""

    id: int
    citation_set_id: int
    document_id: int
    quote_text: str
    citation_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class CitationSetResponse(BaseModel):
    """Response schema for citation sets."""

    id: int
    answer_id: int
    citations: List[CitationResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class CitationSetListResponse(BaseModel):
    """Response schema for listing citation sets."""

    citation_sets: List[CitationSetResponse]
    total: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class CitationReferenceResponse(BaseModel):
    """Response schema for inline citation references."""

    citation_number: int
    quote_text: str
    document_id: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class CitationMinimalResponse(BaseModel):
    """Minimal citation response with just ID and order for frontend hyperlinks."""

    id: int
    citation_order: int
    document_id: int
    quote_text: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )
