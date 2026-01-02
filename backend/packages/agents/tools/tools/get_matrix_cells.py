from typing import List, Optional, Type

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
from packages.matrices.models.schemas.matrix import MatrixCellResponse
from packages.matrices.routes.matrices import get_matrix_cells


class GetMatrixCellsErrorResult(ToolErrorResult):
    error: str


class GetMatrixCellsSuccessResult(ToolSuccessResult):
    cells: List[MatrixCellResponse]


class GetMatrixCellsParameters(ToolParameters):
    matrix_id: int = Field(description="the matrix id to get cells for")
    document_id: Optional[int] = Field(
        description="optional document id to filter cells", default=None
    )
    question_id: Optional[int] = Field(
        description="optional question id to filter cells", default=None
    )


class GetMatrixCellsTool(Tool[GetMatrixCellsParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="get_matrix_cells",
            description="Get matrix cells, optionally filtered by document or question",
            parameters=GetMatrixCellsParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[GetMatrixCellsParameters]:
        return GetMatrixCellsParameters

    @override
    async def execute(
        self,
        parameters: GetMatrixCellsParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            cells = await get_matrix_cells(
                matrix_id=parameters.matrix_id,
                document_id=parameters.document_id,
                question_id=parameters.question_id,
                db=session,
            )

            return ToolResult.ok(GetMatrixCellsSuccessResult(cells=cells))

        except Exception as e:
            return ToolResult.err(GetMatrixCellsErrorResult(error=str(e)))
