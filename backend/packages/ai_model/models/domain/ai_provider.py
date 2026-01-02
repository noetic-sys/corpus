from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AIProviderModel(BaseModel):
    id: int
    name: str
    display_name: str
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIProviderCreateModel(BaseModel):
    """Model for creating a new AI provider."""

    name: str
    display_name: str
    enabled: bool = True


class AIProviderUpdateModel(BaseModel):
    """Model for updating an AI provider."""

    name: Optional[str] = None
    display_name: Optional[str] = None
    enabled: Optional[bool] = None
