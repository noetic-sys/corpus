from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class QuestionTemplateVariableModel(BaseModel):
    id: int
    question_id: int
    template_variable_id: int
    company_id: int
    created_at: datetime
    deleted: bool = False

    model_config = {"from_attributes": True}


class QuestionTemplateVariableCreateModel(BaseModel):
    """Model for creating a new question template variable association."""

    question_id: int
    template_variable_id: int
    company_id: int
