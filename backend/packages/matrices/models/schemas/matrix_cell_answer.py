from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from packages.qa.models.schemas.citation import CitationMinimalResponse


# Answer Data Response Schemas (for API output only)
# Citations are provided separately in AnswerWithCitations wrapper.
# Domain models in qa/models/domain/answer_data.py have citations embedded for agent uploads.
class TextAnswerDataResponse(BaseModel):
    """Answer data for text-based question types (SHORT_ANSWER, LONG_ANSWER)."""

    type: str = "text"
    value: str
    confidence: float = 1.0

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class DateAnswerDataResponse(BaseModel):
    """Answer data for DATE question type."""

    type: str = "date"
    value: str  # Original extracted text
    parsed_date: Optional[str] = None  # ISO format date
    confidence: float = 1.0

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class CurrencyAnswerDataResponse(BaseModel):
    """Answer data for CURRENCY question type."""

    type: str = "currency"
    value: str  # Original extracted text like "$1,234.56"
    amount: Optional[float] = None  # Parsed numeric amount
    currency: Optional[str] = None  # Currency code like "USD"
    confidence: float = 1.0

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class SelectAnswerDataResponse(BaseModel):
    """Answer data for SELECT question type - represents a single selected option."""

    type: str = "select"
    option_id: int
    option_value: str
    confidence: float = 1.0

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


# Union type for all possible answer data structures (response format)
AnswerDataResponse = Union[
    TextAnswerDataResponse,
    DateAnswerDataResponse,
    CurrencyAnswerDataResponse,
    SelectAnswerDataResponse,
]


class AnswerWithCitations(BaseModel):
    """Wrapper that combines answer data with its citations."""

    answer_data: AnswerDataResponse
    citations: List[CitationMinimalResponse] = []

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class ProcessingMetadataSchema(BaseModel):
    """Optional metadata about how the answer was generated."""

    model_used: Optional[str] = None
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
    extraction_method: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixCellAnswerResponse(BaseModel):
    """Response schema for matrix cell answer sets with parsed data.

    Contains answer_found at the response level and answers as a list.
    Empty answers list indicates no answers found.
    """

    id: int  # Answer set ID
    matrix_cell_id: int
    question_type_id: int
    answers: List[AnswerWithCitations] = []  # List of answers with their citations
    answer_found: bool = True
    confidence: float = 1.0  # Average confidence across all answers
    processing_metadata: Optional[ProcessingMetadataSchema] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class MatrixCellAnswerListResponse(BaseModel):
    """Response schema for listing matrix cell answers."""

    answers: List[MatrixCellAnswerResponse]
    total: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )
