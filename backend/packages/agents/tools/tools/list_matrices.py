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
from packages.matrices.models.schemas.matrix import MatrixListResponse
from packages.matrices.routes.matrices import get_matrices_by_workspace


class ListMatricesErrorResult(ToolErrorResult):
    error: str


class ListMatricesSuccessResult(ToolSuccessResult):
    matrices: List[MatrixListResponse]
    total_count: int


class ListMatricesParameters(ToolParameters):
    workspace_id: int = Field(description="workspace id to get matrices for")
    limit: int = Field(description="maximum number of matrices to return", default=50)
    skip: int = Field(
        description="number of matrices to skip for pagination", default=0
    )


class ListMatricesTool(Tool[ListMatricesParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="list_matrices",
            description="List matrices for a specific workspace",
            parameters=ListMatricesParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[ListMatricesParameters]:
        return ListMatricesParameters

    @override
    async def execute(
        self,
        parameters: ListMatricesParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Call the get_matrices_by_workspace route function directly
            matrix_responses = await get_matrices_by_workspace(
                workspace_id=parameters.workspace_id,
                skip=parameters.skip,
                limit=parameters.limit,
                current_user=as_user,
            )

            return ToolResult.ok(
                ListMatricesSuccessResult(
                    matrices=matrix_responses, total_count=len(matrix_responses)
                )
            )

        except Exception as e:
            return ToolResult.err(ListMatricesErrorResult(error=str(e)))
