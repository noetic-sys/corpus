from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from common.db.session import get_db, get_db_readonly
from packages.agents.services.tool_service import get_tool_service
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
async def get_available_tools(
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get all available tools."""
    tool_service = get_tool_service(db)
    return tool_service.get_available_tools()


@router.get("/tools/openai-format/")
async def get_tools_openai_format(
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get tools in OpenAI function calling format."""
    tool_service = get_tool_service(db)
    return tool_service.format_tools_for_openai()


@router.post("/tools/execute/", response_model=ToolExecutionResponse)
@trace_span
async def execute_tool(
    request: ToolExecutionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Execute a tool with the given parameters (for testing)."""
    tool_service = get_tool_service(db)

    logger.info(f"Executing tool: {request.tool_name}")

    result = await tool_service.execute_tool(request.tool_name, request.parameters)

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
