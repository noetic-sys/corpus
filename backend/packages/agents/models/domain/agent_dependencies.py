"""Dependencies container for PydanticAI tool execution.

PydanticAI requires a dependencies object to pass context to tools.
This simply wraps our existing types without duplicating them.
"""

from dataclasses import dataclass
from typing import Optional, Any

from packages.agents.tools.base import ToolPermission
from packages.auth.models.domain.authenticated_user import AuthenticatedUser


@dataclass
class AgentDependencies:
    """Context passed to PydanticAI tools during execution.

    Wraps existing types to provide tool access to:
    - User authentication/authorization
    - Conversation context
    - Permission mode for tool filtering
    """

    user: AuthenticatedUser
    conversation_id: int
    permission_mode: ToolPermission = ToolPermission.READ
    extra_data: Optional[dict[str, Any]] = None
