from typing import Type

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
from packages.matrices.models.domain.matrix import MatrixModel
from packages.matrices.models.schemas.matrix import MatrixCreate
from packages.matrices.routes.matrices import create_matrix


class CreateMatrixErrorResult(ToolErrorResult):
    error: str


class CreateMatrixSuccessResult(ToolSuccessResult):
    matrix: MatrixModel


class CreateMatrixParameters(ToolParameters):
    name: str = Field(description="Name of the matrix")
    description: str = Field(description="Description of the matrix")
    workspace_id: int = Field(description="ID of the workspace to create the matrix in")


class CreateMatrixTool(Tool[CreateMatrixParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.WRITE

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="create_matrix",
            description="Create a new matrix in a workspace",
            parameters=CreateMatrixParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[CreateMatrixParameters]:
        return CreateMatrixParameters

    @override
    async def execute(
        self,
        parameters: CreateMatrixParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            matrix_data = MatrixCreate(
                name=parameters.name,
                description=parameters.description,
                workspace_id=parameters.workspace_id,
            )

            # Call the create_matrix route function directly with authenticated user
            matrix = await create_matrix(matrix=matrix_data, current_user=as_user)

            return ToolResult.ok(CreateMatrixSuccessResult(matrix=matrix))

        except Exception as e:
            return ToolResult.err(CreateMatrixErrorResult(error=str(e)))
