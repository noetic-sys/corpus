from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ConversationBase(BaseModel):
    title: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    ai_model_id: Optional[int] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    ai_model_id: Optional[int] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ConversationResponse(ConversationBase):
    id: int
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
