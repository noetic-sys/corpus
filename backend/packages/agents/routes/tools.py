from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from packages.auth.dependencies import get_current_active_user
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.agents.services.tool_service import ToolService
from packages.agents.tools.base import ToolDefinition
from common.core.otel_axiom_exporter import trace_span, get_logger

router = APIRouter()
logger = get_logger(__name__)


class ToolExecutionRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]


class ToolExecutionResponse(BaseModel):
    success: bool
    result: Any = None
    error: str = None


@router.get("/tools/", response_model=List[ToolDefinition])
async def get_available_tools():
    """Get all available tools."""
    tool_service = ToolService()
    return tool_service.get_available_tools()


@router.get("/tools/openai-format/")
async def get_tools_openai_format():
    """Get tools in OpenAI function calling format."""
    tool_service = ToolService()
    return tool_service.format_tools_for_openai()


@router.post("/tools/execute/", response_model=ToolExecutionResponse)
@trace_span
async def execute_tool(
    request: ToolExecutionRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Execute a tool with the given parameters (for testing)."""
    tool_service = ToolService()

    logger.info(f"Executing tool: {request.tool_name}")

    result = await tool_service.execute_tool(
        request.tool_name, request.parameters, current_user
    )

    if result.error:
        return ToolExecutionResponse(
            success=False,
            error=(
                str(result.error.error)
                if hasattr(result.error, "error")
                else str(result.error)
            ),
        )
    else:
        return ToolExecutionResponse(
            success=True, result=result.result.model_dump() if result.result else None
        )
