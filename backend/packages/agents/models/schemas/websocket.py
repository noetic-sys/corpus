from datetime import datetime
from typing import Optional, List, Literal, Union, Dict, Any
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from common.providers.ai.models import ChatCompletionMessageToolCall
from packages.agents.tools.base import ToolPermission


# Base WebSocket message
class WebSocketMessage(BaseModel):
    type: str

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


# Client -> Server messages
class UserMessageRequest(WebSocketMessage):
    type: Literal["user_message"] = "user_message"
    content: str
    permission_mode: ToolPermission = ToolPermission.READ
    extra_data: Optional[Dict[str, Any]] = None


class GetHistoryRequest(WebSocketMessage):
    type: Literal["get_history"] = "get_history"


class PingRequest(WebSocketMessage):
    type: Literal["ping"] = "ping"


# Server -> Client messages
class ConnectedResponse(WebSocketMessage):
    type: Literal["connected"] = "connected"
    conversation_id: int
    title: Optional[str] = None


class MessageReceivedResponse(WebSocketMessage):
    type: Literal["message_received"] = "message_received"
    content: str


class AgentMessageResponse(WebSocketMessage):
    type: Literal["agent_message"] = "agent_message"
    id: int
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[ChatCompletionMessageToolCall]] = None
    tool_call_id: Optional[str] = None
    permission_mode: ToolPermission = ToolPermission.READ
    sequence_number: int
    created_at: datetime


class ResponseCompleteResponse(WebSocketMessage):
    type: Literal["response_complete"] = "response_complete"


class ConversationHistoryResponse(WebSocketMessage):
    type: Literal["conversation_history"] = "conversation_history"
    messages: List[AgentMessageResponse]


class ErrorResponse(WebSocketMessage):
    type: Literal["error"] = "error"
    error: str
    code: Optional[str] = None


class PongResponse(WebSocketMessage):
    type: Literal["pong"] = "pong"


# Union types for type checking
ClientMessage = Union[UserMessageRequest, GetHistoryRequest, PingRequest]

ServerMessage = Union[
    ConnectedResponse,
    MessageReceivedResponse,
    AgentMessageResponse,
    ResponseCompleteResponse,
    ConversationHistoryResponse,
    ErrorResponse,
    PongResponse,
]
