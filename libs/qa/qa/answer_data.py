from typing import List, Optional, Union

from pydantic import BaseModel

from qa.citation import CitationReference


class TextAnswerData(BaseModel):
    """Domain model for text-based question types (SHORT_ANSWER, LONG_ANSWER)."""

    type: str = "text"
    value: str
    confidence: float = 1.0
    citations: List[CitationReference] = []


class DateAnswerData(BaseModel):
    """Domain model for DATE question type."""

    type: str = "date"
    value: str  # Original extracted text
    parsed_date: Optional[str] = None  # ISO format date
    confidence: float = 1.0
    citations: List[CitationReference] = []


class CurrencyAnswerData(BaseModel):
    """Domain model for CURRENCY question type."""

    type: str = "currency"
    value: str  # Original extracted text like "$1,234.56"
    amount: Optional[float] = None  # Parsed numeric amount
    currency: Optional[str] = None  # Currency code like "USD"
    confidence: float = 1.0
    citations: List[CitationReference] = []


class SelectAnswerData(BaseModel):
    """Domain model for SELECT question type - represents a single selected option."""

    type: str = "select"
    option_id: int
    option_value: str
    confidence: float = 1.0
    citations: List[CitationReference] = []


# Union type for all possible answer data structures
AnswerData = Union[
    TextAnswerData,
    DateAnswerData,
    CurrencyAnswerData,
    SelectAnswerData,
]


# TODO: rename, make pydantic model
class AIAnswerSet:
    """Structured response from AI containing set-level metadata and individual answers."""

    def __init__(self, answer_found: bool, answers: List[AnswerData]):
        """Initialize with answer_found status and list of answers.

        Args:
            answer_found: Whether any answer was found at all
            answers: List of individual AnswerData objects (can be empty if not found)
        """
        self.answer_found = answer_found
        self.answers = answers

    @classmethod
    def not_found(cls) -> "AIAnswerSet":
        """Create a not found response with empty answers list."""
        return cls(answer_found=False, answers=[])

    @classmethod
    def found(cls, answers: List[AnswerData]) -> "AIAnswerSet":
        """Create a found response with answers."""
        if not answers:
            raise ValueError("Cannot create found response with empty answers list")

        return cls(answer_found=True, answers=answers)

    @property
    def answer_count(self) -> int:
        """Number of individual answers in this set."""
        return len(self.answers)

    def __bool__(self) -> bool:
        """Return True if answers were found."""
        return self.answer_found
