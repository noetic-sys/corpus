from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class QuestionModel(BaseModel):
    id: int
    question_text: str
    matrix_id: int
    company_id: int
    question_type_id: int
    ai_model_id: Optional[int] = None
    ai_config_override: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    min_answers: int
    max_answers: Optional[int] = None
    use_agent_qa: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionCreateModel(BaseModel):
    """Model for creating a new question."""

    question_text: str
    matrix_id: int
    company_id: int
    question_type_id: Optional[int] = 1  # Default to SHORT_ANSWER
    ai_model_id: Optional[int] = None
    ai_config_override: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    min_answers: int = 1  # Default to 1, non-nullable
    max_answers: Optional[int] = 1
    use_agent_qa: bool = False


class QuestionUpdateModel(BaseModel):
    """Model for updating a question."""

    question_text: Optional[str] = None
    question_type_id: Optional[int] = None
    ai_model_id: Optional[int] = None
    ai_config_override: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    min_answers: Optional[int] = None
    max_answers: Optional[int] = None
    use_agent_qa: Optional[bool] = None
