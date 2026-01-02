from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from packages.qa.models.domain.answer_data import AnswerData


class AnswerResponse(BaseModel):
    """Response schema for individual answers."""

    id: int
    answer_set_id: int
    answer_data: AnswerData
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class AnswerSetResponse(BaseModel):
    """Response schema for answer sets."""

    id: int
    matrix_cell_id: int
    question_type_id: int
    answer_found: bool
    confidence: float = 1.0
    answers: List[AnswerResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class AnswerSetListResponse(BaseModel):
    """Response schema for listing answer sets."""

    answer_sets: List[AnswerSetResponse]
    total: int

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )
