import enum
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class QuestionTypeName(enum.Enum):
    SHORT_ANSWER = 1
    LONG_ANSWER = 2
    DATE = 3
    CURRENCY = 4
    SELECT = 5

    @classmethod
    def from_id(cls, question_type_id: int) -> "QuestionTypeName":
        """Convert database ID to QuestionTypeName enum."""
        if not question_type_id:
            return cls.SHORT_ANSWER  # Default

        try:
            return cls(question_type_id)
        except ValueError:
            return cls.SHORT_ANSWER  # Default fallback

    @classmethod
    def from_string(cls, value: str) -> "QuestionTypeName":
        """Convert string name to QuestionTypeName enum (for backward compatibility)."""
        if not value:
            return cls.SHORT_ANSWER  # Default

        # Map string names to enum values
        string_to_enum = {
            "SHORT_ANSWER": cls.SHORT_ANSWER,
            "LONG_ANSWER": cls.LONG_ANSWER,
            "DATE": cls.DATE,
            "CURRENCY": cls.CURRENCY,
            "SELECT": cls.SELECT,
        }

        return string_to_enum.get(value.upper(), cls.SHORT_ANSWER)


class QuestionTypeModel(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    validation_schema: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionTypeCreateModel(BaseModel):
    """Model for creating a new question type (admin use)."""

    name: str
    description: Optional[str] = None
    validation_schema: Optional[Dict[str, Any]] = None
