from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class QuestionOptionModel(BaseModel):
    id: int
    option_set_id: int
    value: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionOptionCreateModel(BaseModel):
    """Model for creating a new question option."""

    value: str


class QuestionOptionRepositoryCreateModel(BaseModel):
    """Model for creating a question option at repository level."""

    option_set_id: int
    value: str


class QuestionOptionSetModel(BaseModel):
    """Model that exactly matches QuestionOptionSetEntity - no joined fields."""

    id: int
    question_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionOptionSetRepositoryCreateModel(BaseModel):
    """Model for creating a question option set at repository level."""

    question_id: int


class QuestionOptionSetCreateModel(BaseModel):
    """Model for creating a new question option set."""

    options: List[QuestionOptionCreateModel] = []


class QuestionOptionSetUpdateModel(BaseModel):
    """Model for updating a question option set."""

    options: Optional[List[QuestionOptionCreateModel]] = None


class QuestionOptionSetWithOptionsModel(BaseModel):
    """Composite model created at service level from separate queries."""

    id: int
    question_id: int
    created_at: datetime
    updated_at: datetime
    options: List[QuestionOptionModel] = []
