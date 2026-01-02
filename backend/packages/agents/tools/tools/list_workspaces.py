from typing import List, Type

from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession
from typing_extensions import override

from packages.agents.tools.base import (
    ToolDefinition,
    ToolResult,
    ToolPermission,
    ToolContext,
    ToolParameters,
    ToolSuccessResult,
    ToolErrorResult,
    Tool,
)
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.workspaces.models.schemas.workspace import WorkspaceResponse
from packages.workspaces.routes.workspaces import get_workspaces
from packages.workspaces.services.workspace_service import WorkspaceService


class ListWorkspacesErrorResult(ToolErrorResult):
    error: str


class ListWorkspacesSuccessResult(ToolSuccessResult):
    workspaces: List[WorkspaceResponse]


class ListWorkspacesParameters(ToolParameters):
    limit: int = Field(description="maximum number of workspaces to return", default=50)
    skip: int = Field(
        description="number of workspaces to skip for pagination", default=0
    )


class ListWorkspacesTool(Tool[ListWorkspacesParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="list_workspaces",
            description="List all workspaces in the system",
            parameters=ListWorkspacesParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[ListWorkspacesParameters]:
        return ListWorkspacesParameters

    @override
    async def execute(
        self,
        parameters: ListWorkspacesParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Call the get_workspaces route function directly
            workspace_responses = await get_workspaces(
                skip=parameters.skip,
                limit=parameters.limit,
                current_user=as_user,
                workspace_service=WorkspaceService(session),
            )

            # Convert responses back to domain models

            return ToolResult.ok(
                ListWorkspacesSuccessResult(workspaces=workspace_responses)
            )

        except Exception as e:
            return ToolResult.err(ListWorkspacesErrorResult(error=str(e)))
