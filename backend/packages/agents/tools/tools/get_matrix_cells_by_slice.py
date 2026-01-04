from typing import Type, List

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
from packages.matrices.models.schemas.matrix import (
    MatrixCellWithAnswerResponse,
    MatrixCellsBatchRequest,
    EntitySetFilter,
)
from packages.matrices.models.domain.matrix_enums import EntityRole
from packages.matrices.routes.matrices import get_matrix_cells_batch


class GetMatrixCellsBySliceErrorResult(ToolErrorResult):
    error: str


class GetMatrixCellsBySliceSuccessResult(ToolSuccessResult):
    matrix_cells: List[MatrixCellWithAnswerResponse]


class EntitySetFilterInput(ToolParameters):
    """Filter for entities in an entity set."""

    entity_set_id: int = Field(description="ID of the entity set")
    entity_ids: List[int] = Field(description="List of entity IDs to filter by")
    role: str = Field(
        description="Role of the entity in the matrix (e.g., DOCUMENT, QUESTION, LEFT, RIGHT)"
    )


class GetMatrixCellsBySliceParameters(ToolParameters):
    matrix_id: int = Field(description="ID of the matrix")
    entity_set_filters: List[EntitySetFilterInput] = Field(
        description="List of entity set filters to slice the matrix by. Each filter specifies an entity set, a list of entity IDs, and a role."
    )


class GetMatrixCellsBySliceTool(Tool[GetMatrixCellsBySliceParameters]):
    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls) -> list[ToolContext]:
        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="get_matrix_cells_by_slice",
            description="Get matrix cells with their current answers by slicing the matrix using entity set filters. This allows querying specific subsets of an N-dimensional matrix (e.g., specific documents × specific questions). Each filter specifies an entity_set_id, a list of entity_ids, and a role (DOCUMENT, QUESTION, LEFT, RIGHT, etc.).",
            parameters=GetMatrixCellsBySliceParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[GetMatrixCellsBySliceParameters]:
        return GetMatrixCellsBySliceParameters

    @override
    async def execute(
        self,
        parameters: GetMatrixCellsBySliceParameters,
        session: AsyncSession,
        as_user: AuthenticatedUser,
    ) -> ToolResult:
        try:
            # Convert EntitySetFilterInput to EntitySetFilter
            entity_set_filters = []
            for filter_input in parameters.entity_set_filters:
                entity_set_filters.append(
                    EntitySetFilter(
                        entity_set_id=filter_input.entity_set_id,
                        entity_ids=filter_input.entity_ids,
                        role=EntityRole(filter_input.role),
                    )
                )

            # Create batch request
            batch_request = MatrixCellsBatchRequest(
                entity_set_filters=entity_set_filters
            )

            # Call the route function directly
            matrix_cells = await get_matrix_cells_batch(
                matrix_id=parameters.matrix_id,
                request=batch_request,
            )

            return ToolResult.ok(
                GetMatrixCellsBySliceSuccessResult(matrix_cells=matrix_cells)
            )

        except Exception as e:
            return ToolResult.err(GetMatrixCellsBySliceErrorResult(error=str(e)))
