"""
Domain models for citation validation results.
"""

from typing import List, Optional

from pydantic import BaseModel


class CitationValidationResult(BaseModel):
    """Result of validating a single citation."""

    citation_id: int
    is_grounded: bool  # Quote exists in document
    grounding_score: float  # 0.0-1.0, exact match = 1.0, fuzzy match < 1.0
    is_relevant: Optional[bool] = None  # Citation supports answer (LLM-based, future)
    relevance_reasoning: Optional[str] = None  # Why citation is/isn't relevant
    error_message: Optional[str] = None


class AnswerValidationResult(BaseModel):
    """Result of validating all citations for an answer."""

    answer_id: int
    all_citations_grounded: bool
    avg_grounding_score: float
    ungrounded_citations: List[int] = []  # Citation IDs that failed grounding
    validation_details: List[CitationValidationResult] = []
