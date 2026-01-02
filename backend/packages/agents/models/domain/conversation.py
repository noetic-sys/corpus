from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class ConversationModel(BaseModel):
    id: int
    title: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    ai_model_id: Optional[int] = None
    company_id: int
    is_active: bool = True
    deleted: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationCreateModel(BaseModel):
    title: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    ai_model_id: Optional[int] = None
    company_id: int


class ConversationUpdateModel(BaseModel):
    title: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    ai_model_id: Optional[int] = None
    is_active: Optional[bool] = None
    updated_at: Optional[datetime] = None
