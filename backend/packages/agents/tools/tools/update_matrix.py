from typing import Type, Optional

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
from packages.matrices.models.schemas.matrix import MatrixUpdate
from packages.matrices.routes.matrices import update_matrix


class UpdateMatrixErrorResult(ToolErrorResult):
    error: str


class UpdateMatrixSuccessResult(ToolSuccessResult):
    matrix: Optional[MatrixModel]


class UpdateMatrixParameters(ToolParameters):
    matrix_id: int = Field(description="ID of the matrix to update")
    name: Optional[str] = Field(default=None, description="New name for the matrix")
    description: Optional[str] = Field(
        default=None, description="New description for the matrix"
    )


class UpdateMatrixTool(Tool[UpdateMatrixParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.WRITE

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="update_matrix",
            description="Update an existing matrix's name and/or description",
            parameters=UpdateMatrixParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[UpdateMatrixParameters]:
        return UpdateMatrixParameters

    @override
    async def execute(
        self,
        parameters: UpdateMatrixParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Build update data only with provided fields
            update_data = {}
            if parameters.name is not None:
                update_data["name"] = parameters.name
            if parameters.description is not None:
                update_data["description"] = parameters.description

            if not update_data:
                return ToolResult.err(
                    UpdateMatrixErrorResult(error="No update fields provided")
                )

            matrix_update_data = MatrixUpdate(**update_data)

            # Call the update_matrix route function directly with authenticated user
            matrix = await update_matrix(
                matrix_id=parameters.matrix_id,
                matrix_update=matrix_update_data,
                current_user=as_user,
            )

            return ToolResult.ok(UpdateMatrixSuccessResult(matrix=matrix))

        except Exception as e:
            return ToolResult.err(UpdateMatrixErrorResult(error=str(e)))
