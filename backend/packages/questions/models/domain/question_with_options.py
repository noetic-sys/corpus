from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from .question_option import QuestionOptionCreateModel


class QuestionWithOptionsCreateModel(BaseModel):
    """Domain model for creating a question with options in a single transaction."""

    question_text: str
    question_type_id: int
    ai_model_id: Optional[int] = None
    ai_config_override: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    min_answers: int = 1  # Default to 1, non-nullable
    max_answers: Optional[int] = 1  # Default to 1
    use_agent_qa: bool = False  # Default to False, non-nullable
    options: List[QuestionOptionCreateModel] = []


class QuestionWithOptionsUpdateModel(BaseModel):
    """Domain model for updating a question with options in a single transaction."""

    question_text: Optional[str] = None
    question_type_id: Optional[int] = None
    ai_model_id: Optional[int] = None
    ai_config_override: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    min_answers: Optional[int] = None
    max_answers: Optional[int] = None
    use_agent_qa: Optional[bool] = None  # Optional for partial updates
    options: Optional[List[QuestionOptionCreateModel]] = None
