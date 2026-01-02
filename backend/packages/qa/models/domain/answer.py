from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from .answer_data import AnswerData


class AnswerModel(BaseModel):
    """Domain model for individual answers within an answer set."""

    id: int
    answer_set_id: int
    company_id: int
    answer_data: AnswerData  # Typed answer data for validation
    current_citation_set_id: Optional[int] = None  # Pointer to current citation set
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnswerCreateModel(BaseModel):
    """Model for creating a new answer."""

    answer_set_id: int
    company_id: int
    answer_data: AnswerData


class AnswerUpdateModel(BaseModel):
    """Model for updating an answer."""

    answer_set_id: Optional[int] = None
    company_id: Optional[int] = None
    answer_data: Optional[AnswerData] = None
    current_citation_set_id: Optional[int] = None
