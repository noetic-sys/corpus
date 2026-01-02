from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class QuestionTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    validation_schema: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class QuestionTypeCreate(QuestionTypeBase):
    pass


class QuestionTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    validation_schema: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class QuestionTypeResponse(QuestionTypeBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )
