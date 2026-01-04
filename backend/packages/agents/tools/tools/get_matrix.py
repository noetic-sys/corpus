from typing import Optional, Type

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
from packages.matrices.models.schemas.matrix import MatrixResponse
from packages.matrices.routes.matrices import get_matrix


class GetMatrixErrorResult(ToolErrorResult):
    error: str


class GetMatrixSuccessResult(ToolSuccessResult):
    matrix: Optional[MatrixResponse]


class GetMatrixParameters(ToolParameters):
    matrix_id: int = Field(description="the matrix id to retrieve")


class GetMatrixTool(Tool[GetMatrixParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="get_matrix",
            description="Get details about a specific matrix by ID",
            parameters=GetMatrixParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[GetMatrixParameters]:
        return GetMatrixParameters

    @override
    async def execute(
        self,
        parameters: GetMatrixParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            matrix = await get_matrix(
                matrix_id=parameters.matrix_id, current_user=as_user
            )

            return ToolResult.ok(GetMatrixSuccessResult(matrix=matrix))

        except Exception as e:
            return ToolResult.err(GetMatrixErrorResult(error=str(e)))
