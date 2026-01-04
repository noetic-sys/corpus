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
from packages.matrices.models.schemas.matrix_entity_set import MatrixEntitySetsResponse
from packages.matrices.routes.matrices import get_matrix_entity_sets


class GetMatrixEntitySetsErrorResult(ToolErrorResult):
    error: str


class GetMatrixEntitySetsSuccessResult(ToolSuccessResult):
    entity_sets: MatrixEntitySetsResponse


class GetMatrixEntitySetsParameters(ToolParameters):
    matrix_id: int = Field(description="ID of the matrix")


class GetMatrixEntitySetsTool(Tool[GetMatrixEntitySetsParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="get_matrix_entity_sets",
            description="Get all entity sets for a matrix with their members. Entity sets define the dimensions of an N-dimensional matrix (e.g., documents, questions, or custom dimensions). Each entity set contains members (specific documents/questions) with their IDs and order.",
            parameters=GetMatrixEntitySetsParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[GetMatrixEntitySetsParameters]:
        return GetMatrixEntitySetsParameters

    @override
    async def execute(
        self,
        parameters: GetMatrixEntitySetsParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Call the route function directly
            entity_sets_response = await get_matrix_entity_sets(
                matrix_id=parameters.matrix_id,
                current_user=as_user,
            )

            return ToolResult.ok(
                GetMatrixEntitySetsSuccessResult(entity_sets=entity_sets_response)
            )

        except Exception as e:
            return ToolResult.err(GetMatrixEntitySetsErrorResult(error=str(e)))
