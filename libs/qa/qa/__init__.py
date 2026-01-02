"""QA domain models and utilities."""

from qa.ai_response_parser import AIResponseParser
from qa.ai_responses import (
    AIResponse,
    CitationItem,
    CurrencyItem,
    CurrencyResponse,
    DateItem,
    DateResponse,
    SelectOption,
    SelectResponse,
    TextItem,
    TextResponse,
)
from qa.answer_data import (
    AIAnswerSet,
    AnswerData,
    CurrencyAnswerData,
    DateAnswerData,
    SelectAnswerData,
    TextAnswerData,
)
from qa.citation import (
    CitationCreateModel,
    CitationCreateWithoutSetIdModel,
    CitationModel,
    CitationReference,
    CitationSetCreateModel,
    CitationSetCreateOnlyModel,
    CitationSetModel,
    CitationSetWithCitationsModel,
)
from qa.citation_validation import AnswerValidationResult, CitationValidationResult

__all__ = [
    # Citation models
    "CitationModel",
    "CitationCreateWithoutSetIdModel",
    "CitationCreateModel",
    "CitationSetModel",
    "CitationSetWithCitationsModel",
    "CitationSetCreateOnlyModel",
    "CitationSetCreateModel",
    "CitationReference",
    # Citation validation
    "CitationValidationResult",
    "AnswerValidationResult",
    # Answer data
    "TextAnswerData",
    "DateAnswerData",
    "CurrencyAnswerData",
    "SelectAnswerData",
    "AnswerData",
    "AIAnswerSet",
    # AI responses
    "CitationItem",
    "CurrencyItem",
    "CurrencyResponse",
    "DateItem",
    "DateResponse",
    "SelectOption",
    "SelectResponse",
    "TextItem",
    "TextResponse",
    "AIResponse",
    # Parser
    "AIResponseParser",
]
