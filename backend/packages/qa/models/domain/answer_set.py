from datetime import datetime
from pydantic import BaseModel


class AnswerSetModel(BaseModel):
    """Domain model for answer sets."""

    id: int
    matrix_cell_id: int
    question_type_id: int
    company_id: int
    answer_found: bool = False
    confidence: float = 1.0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AnswerSetCreateModel(BaseModel):
    """Model for creating a new answer set."""

    matrix_cell_id: int
    question_type_id: int
    company_id: int
    answer_found: bool = False
    confidence: float = 1.0
