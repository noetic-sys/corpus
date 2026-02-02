"""Dependencies container for PydanticAI tool execution.

PydanticAI requires a dependencies object to pass context to tools.
This simply wraps our existing types without duplicating them.
"""

from dataclasses import dataclass, field
from typing import Optional, Any, Callable, Awaitable

from packages.agents.tools.base import ToolPermission
from packages.auth.models.domain.authenticated_user import AuthenticatedUser


@dataclass
class AgentDependencies:
    """Context passed to PydanticAI tools during execution.

    Wraps existing types to provide tool access to:
    - User authentication/authorization
    - Conversation context
    - Permission mode for tool filtering
    - Callbacks for real-time tool execution visibility
    """

    user: AuthenticatedUser
    conversation_id: int
    permission_mode: ToolPermission = ToolPermission.READ
    extra_data: Optional[dict[str, Any]] = None
    # Callback when tool starts: (tool_name, tool_call_id, args) -> None
    on_tool_start: Optional[Callable[[str, str, dict], Awaitable[None]]] = field(
        default=None, repr=False
    )
    # Callback when tool completes: (tool_name, tool_call_id, result) -> None
    on_tool_result: Optional[Callable[[str, str, str], Awaitable[None]]] = field(
        default=None, repr=False
    )
