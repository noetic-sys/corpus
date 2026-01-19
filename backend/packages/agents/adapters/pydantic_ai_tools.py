"""Adapter to bridge existing tools to PydanticAI's tool system.

PydanticAI expects tools as decorated functions. This adapter creates
dynamic tool functions that delegate to our existing ToolService.
"""

import json
from typing import Any

from pydantic_ai import RunContext

from packages.agents.models.domain.agent_dependencies import AgentDependencies
from packages.agents.services.tool_service import ToolService
from packages.agents.tools.base import ToolPermission
from packages.agents.tools.registry import registry
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


async def execute_tool_for_pydantic_ai(
    ctx: RunContext[AgentDependencies],
    tool_name: str,
    parameters: dict[str, Any],
) -> str:
    """Execute a tool through ToolService and return result as string.

    This is the core bridge function that PydanticAI tool wrappers call.
    """
    tool_service = ToolService()

    result = await tool_service.execute_tool(
        tool_name=tool_name,
        parameters=parameters,
        user=ctx.deps.user,
    )

    if result.error:
        try:
            error_dict = result.error.model_dump()
            return f"Tool execution failed: {json.dumps(error_dict, default=str, indent=2)}"
        except Exception:
            return f"Tool execution failed: {str(result.error)}"
    elif result.result:
        return json.dumps(result.result.model_dump(), default=str, indent=2)
    else:
        return "Tool executed successfully with no result"


def get_tools_for_permission(permission: ToolPermission) -> list[dict[str, Any]]:
    """Get tool definitions in PydanticAI format for given permission level.

    Returns tools in the format PydanticAI expects for dynamic tool registration.
    """
    tool_service = ToolService()
    definitions = tool_service.get_available_tools(permission=permission)

    tools = []
    for definition in definitions:
        tools.append({
            "name": definition.name,
            "description": definition.description,
            "parameters": definition.parameters,
        })

    return tools


def create_dynamic_tool_executor(tool_name: str):
    """Create a tool executor function for a specific tool.

    PydanticAI needs individual functions per tool. This factory creates
    them dynamically from our registry.
    """

    async def tool_executor(
        ctx: RunContext[AgentDependencies],
        **kwargs: Any,
    ) -> str:
        return await execute_tool_for_pydantic_ai(ctx, tool_name, kwargs)

    # Set function metadata for PydanticAI
    tool_executor.__name__ = tool_name
    tool_executor.__doc__ = registry.get_tool(tool_name).definition().description

    return tool_executor
