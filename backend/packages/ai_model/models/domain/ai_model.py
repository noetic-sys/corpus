from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from .ai_provider import AIProviderModel


class AIModelModel(BaseModel):
    id: int
    provider_id: int
    model_name: str
    display_name: str
    default_temperature: float
    default_max_tokens: Optional[int]
    enabled: bool
    created_at: datetime
    updated_at: datetime

    # Optional loaded relationships
    # TODO: i messed this up and its so baked in now. get rid of this though. simple models only
    provider: Optional[AIProviderModel] = None

    model_config = {"from_attributes": True}


class AIModelCreateModel(BaseModel):
    """Model for creating a new AI model."""

    provider_id: int
    model_name: str
    display_name: str
    default_temperature: float = 0.7
    default_max_tokens: Optional[int] = None
    enabled: bool = True


class AIModelUpdateModel(BaseModel):
    """Model for updating an AI model."""

    provider_id: Optional[int] = None
    model_name: Optional[str] = None
    display_name: Optional[str] = None
    default_temperature: Optional[float] = None
    default_max_tokens: Optional[int] = None
    enabled: Optional[bool] = None
