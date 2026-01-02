from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.agents.tools.registry import registry
from packages.agents.tools.base import (
    ToolResult,
    ToolDefinition,
    GenericToolErrorResult,
    ToolPermission,
)
from common.db.session import AsyncSessionLocal
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class ToolService:
    """Service for executing tools safely."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.registry = registry

    @trace_span
    async def execute_tool(
        self, tool_name: str, parameters: Dict[str, Any], user: AuthenticatedUser
    ) -> ToolResult:
        """Execute a tool with the given parameters in its own transaction."""
        try:
            # Get the tool class from registry
            tool_class = self.registry.get_tool(tool_name)
            tool_instance = tool_class()

            logger.info(f"Executing tool: {tool_name}")
            logger.debug(f"Tool parameters: {parameters}")

            # Validate and parse parameters using the tool's parameter class
            try:
                parameter_class = tool_class.parameter_class()
                parsed_params = parameter_class(**parameters)
            except ValidationError as e:
                logger.error(f"Parameter validation failed for tool {tool_name}: {e}")
                error_result = GenericToolErrorResult(
                    error=f"Parameter validation failed: {str(e)}"
                )
                return ToolResult.err(error_result)

            # Create a fresh database session for tool execution with proper transaction boundaries
            async with AsyncSessionLocal() as tool_session:
                try:
                    # Execute the tool with its own session and authenticated user
                    result = await tool_instance.execute(
                        parsed_params, tool_session, as_user=user
                    )

                    if result.error:
                        logger.warning(
                            f"Tool {tool_name} returned error: {result.error}"
                        )
                        # Don't commit on tool-level errors, but don't rollback either
                        # The tool may have intended the error (e.g., validation failure)
                    else:
                        # Commit the transaction on successful tool execution
                        await tool_session.commit()
                        logger.info(
                            f"Tool {tool_name} executed successfully and committed"
                        )

                    return result

                except Exception as tool_exec_error:
                    # Rollback the transaction on unexpected errors during tool execution
                    await tool_session.rollback()
                    logger.error(
                        f"Tool {tool_name} execution failed, transaction rolled back: {tool_exec_error}"
                    )
                    # Return error result instead of raising - maintain AI tool calling contract
                    error_result = GenericToolErrorResult(
                        error=f"Tool execution failed: {str(tool_exec_error)}"
                    )
                    return ToolResult.err(error_result)

        except ValueError as e:
            logger.error(f"Tool not found: {tool_name}")
            error_result = GenericToolErrorResult(error=f"Tool not found: {tool_name}")
            return ToolResult.err(error_result)

        except Exception as e:
            logger.error(f"Unexpected error executing tool {tool_name}: {e}")
            error_result = GenericToolErrorResult(
                error=f"Tool execution failed: {str(e)}"
            )
            return ToolResult.err(error_result)

    def get_available_tools(
        self, permission: ToolPermission = ToolPermission.READ
    ) -> List[ToolDefinition]:
        """Get all available tool definitions for the given permission level."""
        return self.registry.get_tool_definitions(permission=permission)

    def get_tool_names(self) -> List[str]:
        """Get list of all available tool names."""
        return self.registry.list_tool_names()

    def format_tools_for_openai(
        self, permission: ToolPermission = ToolPermission.READ
    ) -> List[Dict[str, Any]]:
        """Format tools for OpenAI function calling format with permission filtering."""
        tools = []
        for definition in self.get_available_tools(permission=permission):
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": definition.name,
                        "description": definition.description,
                        "parameters": definition.parameters,
                    },
                }
            )
        return tools


def get_tool_service(db_session: AsyncSession) -> ToolService:
    """Get tool service instance."""
    return ToolService(db_session)
