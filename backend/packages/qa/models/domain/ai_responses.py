"""AI response models using pydantic for structured JSON parsing."""

from typing import List
import re
from pydantic import BaseModel, field_validator


class CitationItem(BaseModel):
    """Single citation item within citations list."""

    order: int
    quote_text: str
    document_id: int  # Required: AI must specify which document the citation is from


class CurrencyItem(BaseModel):
    """Single currency item in a list response."""

    amount: float
    code: str
    citations: List[CitationItem] = []
    confidence: float = 1.0  # Confidence score 0.0-1.0

    @field_validator("code")
    def validate_currency_code(cls, v):
        """Ensure currency code is 3 uppercase letters."""
        if v and len(v) == 3 and v.isalpha():
            return v.upper()
        raise ValueError(f"Invalid currency code: {v}")


class CurrencyResponse(BaseModel):
    """JSON model for currency responses from AI - always a list."""

    items: List[CurrencyItem] = []


class DateItem(BaseModel):
    """Single date item in a list response."""

    value: str  # ISO format YYYY-MM-DD
    citations: List[CitationItem] = []
    confidence: float = 1.0  # Confidence score 0.0-1.0

    @field_validator("value")
    def validate_date_format(cls, v):
        """Validate ISO date format."""
        if v and re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            return v
        raise ValueError(f"Invalid date format: {v}")


class DateResponse(BaseModel):
    """JSON model for date responses from AI - always a list."""

    items: List[DateItem] = []


class SelectOption(BaseModel):
    """Single select option with citations."""

    value: str
    citations: List[CitationItem] = []
    confidence: float = 1.0  # Confidence score 0.0-1.0


class SelectResponse(BaseModel):
    """JSON model for select responses from AI - unified single/multi select."""

    options: List[SelectOption] = []


class TextItem(BaseModel):
    """Single text item in a list response."""

    value: str
    citations: List[CitationItem] = []
    confidence: float = 1.0  # Confidence score 0.0-1.0


class TextResponse(BaseModel):
    """JSON model for text responses from AI - always a list."""

    items: List[TextItem] = []


# Union type for all possible AI responses
AIResponse = CurrencyResponse | DateResponse | SelectResponse | TextResponse
