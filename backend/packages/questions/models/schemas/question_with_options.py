from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from .question_option import QuestionOptionCreate


class QuestionWithOptionsCreate(BaseModel):
    """Model for creating a question with options in a single transaction."""

    question_text: str
    question_type_id: int
    ai_model_id: Optional[int] = None
    ai_config_override: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    min_answers: int = 1  # Default to 1, non-nullable
    max_answers: Optional[int] = 1  # Default to 1, null means unlimited
    use_agent_qa: bool = False  # Default to False, non-nullable
    options: List[QuestionOptionCreate] = []

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class QuestionWithOptionsUpdate(BaseModel):
    """Model for updating a question with options in a single transaction."""

    question_text: Optional[str] = None
    question_type_id: Optional[int] = None
    ai_model_id: Optional[int] = None
    ai_config_override: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    min_answers: Optional[int] = None
    max_answers: Optional[int] = None
    use_agent_qa: Optional[bool] = None  # Optional for partial updates
    options: Optional[List[QuestionOptionCreate]] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class QuestionWithOptionsResponse(BaseModel):
    """Response model for question with options."""

    question_id: int
    question_text: str
    question_type_id: int
    matrix_id: int
    option_set_id: Optional[int] = None
    options: List[dict] = []

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )
