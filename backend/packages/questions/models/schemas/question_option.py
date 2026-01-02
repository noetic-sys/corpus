from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class QuestionOptionBase(BaseModel):
    value: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class QuestionOptionCreate(QuestionOptionBase):
    pass


class QuestionOptionResponse(QuestionOptionBase):
    id: int
    option_set_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )


class QuestionOptionSetBase(BaseModel):
    pass


class QuestionOptionSetCreate(QuestionOptionSetBase):
    options: List[QuestionOptionCreate] = []

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class QuestionOptionSetUpdate(QuestionOptionSetBase):
    options: Optional[List[QuestionOptionCreate]] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class QuestionOptionSetResponse(QuestionOptionSetBase):
    """Response model with full option set and options."""

    id: int
    question_id: int
    created_at: datetime
    updated_at: datetime
    options: List[QuestionOptionResponse] = []

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )
