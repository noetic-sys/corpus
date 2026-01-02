from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from packages.ai_model.models.schemas.ai_model import AIModelResponse


class QuestionBase(BaseModel):
    question_text: str
    question_type_id: Optional[int] = 1  # Default to SHORT_ANSWER
    ai_model_id: Optional[int] = None
    ai_config_override: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    min_answers: int = 1  # Default to 1, non-nullable
    max_answers: Optional[int] = 1
    use_agent_qa: bool = False  # Default to False, non-nullable

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class QuestionCreate(QuestionBase):
    pass


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    question_type_id: Optional[int] = None
    ai_model_id: Optional[int] = None
    ai_config_override: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    min_answers: Optional[int] = None
    max_answers: Optional[int] = None
    use_agent_qa: Optional[bool] = None  # Optional for partial updates

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class QuestionLabelUpdate(BaseModel):
    label: Optional[str] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
    )


class QuestionResponse(QuestionBase):
    id: int
    matrix_id: int
    created_at: datetime
    updated_at: datetime

    # Optional loaded relationships
    ai_model: Optional[AIModelResponse] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,  # Allows population by both original name and alias
        from_attributes=True,
    )
