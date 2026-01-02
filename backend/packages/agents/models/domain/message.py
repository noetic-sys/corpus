from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from common.providers.ai.models import ChatCompletionMessageToolCall
from packages.agents.tools.base import ToolPermission


class MessageModel(BaseModel):
    id: int
    conversation_id: int
    role: str  # user, assistant, system, tool
    content: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None
    tool_call_id: Optional[str] = None
    sequence_number: int
    company_id: int
    permission_mode: ToolPermission = ToolPermission.READ
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreateModel(BaseModel):
    conversation_id: int
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None
    tool_call_id: Optional[str] = None
    sequence_number: int
    company_id: int
    permission_mode: ToolPermission = ToolPermission.READ
    extra_data: Optional[Dict[str, Any]] = None


class MessageUpdateModel(BaseModel):
    content: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None
    extra_data: Optional[Dict[str, Any]] = None
