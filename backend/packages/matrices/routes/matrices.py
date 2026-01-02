from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from packages.matrices.models.domain.matrix_enums import EntityType
from packages.matrices.services.matrix_template_variable_service import (
    MatrixTemplateVariableService,
)

from packages.matrices.strategies.factory import CellStrategyFactory
from common.db.session import get_db, get_db_readonly
from packages.matrices.models.schemas.matrix import (
    MatrixCreate,
    MatrixUpdate,
    MatrixResponse,
    MatrixListResponse,
    MatrixCellUpdate,
    MatrixCellResponse,
    MatrixCellWithAnswerResponse,
    MatrixReprocessRequest,
    MatrixCellReprocessResponse,
    MatrixSoftDeleteRequest,
    MatrixSoftDeleteResponse,
    MatrixDuplicateRequest,
    MatrixDuplicateResponse,
    MatrixCellsBatchRequest,
    EntityRefResponse,
    MatrixStructureResponse,
    EntitySetSummary,
    MatrixStatsResponse,
)
from packages.matrices.models.schemas.matrix_entity_set import (
    MatrixEntitySetsResponse,
    EntitySetResponse,
    EntitySetMemberResponse,
)
from packages.matrices.models.domain.matrix import MatrixCreateModel, MatrixUpdateModel
from packages.matrices.models.schemas.matrix_cell_answer import (
    MatrixCellAnswerResponse,
)
from packages.matrices.models.schemas.matrix_template_variable import (
    MatrixTemplateVariableResponse,
)
from packages.matrices.services.reprocessing_service import get_reprocessing_service
from packages.matrices.services.soft_delete_service import get_soft_delete_service
from packages.matrices.services.matrix_service import get_matrix_service
from packages.matrices.services.entity_set_service import get_entity_set_service
from packages.auth.dependencies import get_current_active_user, get_service_account
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from common.core.otel_axiom_exporter import trace_span, get_logger
from common.db.transaction_utils import transaction
from packages.matrices.mappers.matrix_cell_mappers import (
    build_matrix_cell_answer_response,
)

router = APIRouter()
logger = get_logger(__name__)

# Import limiter


# Matrix endpoints
@router.post("/matrices/", response_model=MatrixResponse)
async def create_matrix(
    matrix: MatrixCreate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    matrix_service = get_matrix_service(db)
    create_model = MatrixCreateModel(
        name=matrix.name,
        description=matrix.description,
        workspace_id=matrix.workspace_id,
        company_id=current_user.company_id,
        matrix_type=matrix.matrix_type,
    )
    return await matrix_service.create_matrix(create_model)


@router.get("/matrices/", response_model=List[MatrixListResponse])
async def list_matrices(
    skip: int = 0,
    limit: int = 100,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_readonly),
):
    matrix_service = get_matrix_service(db)
    return await matrix_service.list_matrices(skip, limit, current_user.company_id)


@router.get(
    "/workspaces/{workspaceId}/matrices/",
    response_model=List[MatrixListResponse],
    tags=["workflow-agent"],
    operation_id="get_matrices_by_workspace",
)
@trace_span
async def get_matrices_by_workspace(
    workspace_id: int = Path(alias="workspaceId"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get all matrices for a specific workspace."""
    matrix_service = get_matrix_service(db)
    return await matrix_service.get_matrices_by_workspace(
        workspace_id, skip, limit, current_user.company_id
    )


@router.get(
    "/matrices/{matrixId}",
    response_model=MatrixResponse,
    tags=["workflow-agent"],
    operation_id="get_matrix",
)
async def get_matrix(
    matrix_id: int = Path(alias="matrixId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_readonly),
):
    matrix_service = get_matrix_service(db)
    matrix = await matrix_service.get_matrix(matrix_id, current_user.company_id)
    if matrix is None:
        raise HTTPException(status_code=404, detail="Matrix not found")
    # Convert domain model to response schema
    return MatrixResponse.model_validate(matrix)


@router.get(
    "/matrices/{matrixId}/entity-sets",
    response_model=MatrixEntitySetsResponse,
    tags=["workflow-agent"],
    operation_id="get_matrix_entity_sets",
)
@trace_span
async def get_matrix_entity_sets(
    matrix_id: int = Path(alias="matrixId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get all entity sets for a matrix with their members.

    This endpoint provides complete entity set information needed by the frontend to:
    1. Determine matrix dimensionality
    2. Construct entity_set_filters for tile batch queries
    3. Map entity IDs (document/question IDs) to entity set member IDs
    """
    matrix_service = get_matrix_service(db)
    entity_set_service = get_entity_set_service(db)

    # Get matrix to verify existence and get matrix_type
    matrix = await matrix_service.get_matrix(matrix_id, current_user.company_id)
    if not matrix:
        raise HTTPException(status_code=404, detail="Matrix not found")

    # Get all entity sets with their members
    entity_sets_with_members = await entity_set_service.get_entity_sets_with_members(
        matrix_id, current_user.company_id
    )

    # Build response
    entity_set_responses = []
    for entity_set, members in entity_sets_with_members:
        member_responses = [
            EntitySetMemberResponse.model_validate(member) for member in members
        ]
        entity_set_response = EntitySetResponse.model_validate(entity_set)
        entity_set_response.members = member_responses
        entity_set_responses.append(entity_set_response)

    return MatrixEntitySetsResponse(
        matrix_id=matrix_id,
        matrix_type=matrix.matrix_type,
        entity_sets=entity_set_responses,
    )


@router.get("/matrices/{matrixId}/stats", response_model=MatrixStatsResponse)
@trace_span
async def get_matrix_stats(
    matrix_id: int = Path(alias="matrixId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get cell statistics for a matrix (count by status)."""
    matrix_service = get_matrix_service(db)

    # Verify matrix exists and user has access
    matrix = await matrix_service.get_matrix(matrix_id, current_user.company_id)
    if matrix is None:
        raise HTTPException(status_code=404, detail="Matrix not found")

    stats = await matrix_service.get_matrix_cell_stats(
        matrix_id, current_user.company_id
    )
    return MatrixStatsResponse.model_validate(stats)


@router.patch("/matrices/{matrixId}", response_model=MatrixResponse)
async def update_matrix(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    matrix_update: MatrixUpdate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    matrix_service = get_matrix_service(db)
    update_model = MatrixUpdateModel(
        name=matrix_update.name,
        description=matrix_update.description,
    )
    matrix = await matrix_service.update_matrix(
        matrix_id, update_model, current_user.company_id
    )
    if matrix is None:
        raise HTTPException(status_code=404, detail="Matrix not found")
    return matrix


@router.delete("/matrices/{matrixId}")
async def delete_matrix(
    matrix_id: int = Path(alias="matrixId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    matrix_service = get_matrix_service(db)
    success = await matrix_service.delete_matrix(matrix_id, current_user.company_id)
    if not success:
        raise HTTPException(status_code=404, detail="Matrix not found")
    return {"message": "Matrix deleted successfully"}


# Matrix Cell endpoints
@router.get("/matrix-cells/{cellId}", response_model=MatrixCellResponse)
async def get_matrix_cell(
    cell_id: Annotated[int, Path(alias="cellId")],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_readonly),
):
    matrix_service = get_matrix_service(db)
    cell = await matrix_service.get_matrix_cell(cell_id, current_user.company_id)
    if cell is None:
        raise HTTPException(status_code=404, detail="Matrix cell not found")
    return cell


@router.patch("/matrix-cells/{cellId}", response_model=MatrixCellResponse)
async def update_matrix_cell(
    cell_id: Annotated[int, Path(alias="cellId")],
    cell_update: MatrixCellUpdate,
    db: AsyncSession = Depends(get_db),
):
    matrix_service = get_matrix_service(db)

    update_data = cell_update.model_dump(exclude_unset=True)
    cell = await matrix_service.update_matrix_cell(cell_id, **update_data)

    if cell is None:
        raise HTTPException(status_code=404, detail="Matrix cell not found")

    return cell


# Matrix Cell streaming endpoints
# TODO: add users
@router.get("/matrices/{matrixId}/cells", response_model=List[MatrixCellResponse])
@trace_span
async def get_matrix_cells(
    matrix_id: int = Path(alias="matrixId"),
    document_id: Optional[int] = Query(None, alias="documentId"),
    question_id: Optional[int] = Query(None, alias="questionId"),
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get matrix cells with optional filtering by document_id or question_id."""
    matrix_service = get_matrix_service(db)
    entity_set_service = get_entity_set_service(db)

    if document_id and question_id:
        # Get cells filtered by document first
        doc_entity_set = await entity_set_service.get_entity_set_by_type(
            matrix_id, EntityType.DOCUMENT
        )
        if not doc_entity_set:
            return []
        cells = await matrix_service.get_matrix_cells_by_document(
            matrix_id, document_id, doc_entity_set.id
        )

    elif document_id:
        entity_set = await entity_set_service.get_entity_set_by_type(
            matrix_id, EntityType.DOCUMENT
        )
        if not entity_set:
            return []
        cells = await matrix_service.get_matrix_cells_by_document(
            matrix_id, document_id, entity_set.id
        )
    elif question_id:
        entity_set = await entity_set_service.get_entity_set_by_type(
            matrix_id, EntityType.QUESTION
        )
        if not entity_set:
            return []
        cells = await matrix_service.get_matrix_cells_by_question(
            matrix_id, question_id, entity_set.id
        )
    else:
        cells = await matrix_service.get_matrix_cells(matrix_id)

    # Load entity refs for all cells with member data
    cell_ids = [cell.id for cell in cells]
    (
        entity_refs_by_cell,
        members_by_id,
    ) = await entity_set_service.load_entity_refs_for_cells(cell_ids)

    # Build responses with entity_refs converted to EntityRefResponse
    responses = []
    for cell in cells:
        entity_refs = entity_refs_by_cell.get(cell.id, [])

        # Convert MatrixCellEntityReferenceModel to EntityRefResponse
        entity_ref_responses = []
        for ref in entity_refs:
            member = members_by_id.get(ref.entity_set_member_id)
            if member:
                entity_ref_responses.append(
                    EntityRefResponse(
                        id=ref.id,
                        entity_set_id=ref.entity_set_id,
                        entity_set_member_id=ref.entity_set_member_id,
                        entity_type=member.entity_type,
                        entity_id=member.entity_id,
                        role=ref.role,
                        entity_order=ref.entity_order,
                    )
                )

        # If filtering by both document and question, check if this cell has the question
        if document_id and question_id:
            has_question = any(
                ref.entity_id == question_id and ref.entity_type == EntityType.QUESTION
                for ref in entity_ref_responses
            )
            if not has_question:
                continue

        responses.append(
            MatrixCellResponse(
                id=cell.id,
                matrix_id=cell.matrix_id,
                current_answer_set_id=cell.current_answer_set_id,
                status=cell.status,
                created_at=cell.created_at,
                updated_at=cell.updated_at,
                entity_refs=entity_ref_responses,
            )
        )

    return responses


# Matrix Cell Answer endpoints


@router.get(
    "/matrix-cells/{cellId}/answers/current",
    response_model=Optional[MatrixCellAnswerResponse],
)
@trace_span
async def get_current_matrix_cell_answer(
    cell_id: int = Path(alias="cellId"),
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get the current answer for a matrix cell."""
    matrix_service = get_matrix_service(db)

    # Verify cell exists
    cell = await matrix_service.get_matrix_cell(cell_id)
    if not cell:
        raise HTTPException(status_code=404, detail="Matrix cell not found")

    if not cell.current_answer_set_id:
        return None

    # Get current answer set
    current_answer_set = await matrix_service.answer_set_service.get_answer_set(
        cell.current_answer_set_id
    )
    if not current_answer_set:
        return None

    # Get first answer from answer set for compatibility
    answers = await matrix_service.answer_service.get_answers_for_answer_set(
        current_answer_set.id
    )

    return await build_matrix_cell_answer_response(current_answer_set, matrix_service)


@router.get(
    "/matrices/{matrixId}/entity-sets/{entitySetId}/documents/{documentId}/cells/with-answers",
    response_model=List[MatrixCellWithAnswerResponse],
    tags=["workflow-agent"],
    operation_id="get_matrix_cells_by_document",
)
@trace_span
async def get_matrix_cells_with_current_answers_by_document(
    matrix_id: int = Path(alias="matrixId"),
    entity_set_id: int = Path(alias="entitySetId"),
    document_id: int = Path(alias="documentId"),
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get all matrix cells with their current answers for a specific document (entity-ref based)."""
    matrix_service = get_matrix_service(db)
    return await matrix_service.get_matrix_cells_with_current_answer_sets_by_document(
        matrix_id, document_id, entity_set_id
    )


@router.get(
    "/matrices/{matrixId}/entity-sets/{entitySetId}/questions/{questionId}/cells/with-answers",
    response_model=List[MatrixCellWithAnswerResponse],
    tags=["workflow-agent"],
    operation_id="get_matrix_cells_by_question",
)
@trace_span
async def get_matrix_cells_with_current_answers_by_question(
    matrix_id: int = Path(alias="matrixId"),
    entity_set_id: int = Path(alias="entitySetId"),
    question_id: int = Path(alias="questionId"),
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get all matrix cells with their current answers for a specific question (entity-ref based)."""
    matrix_service = get_matrix_service(db)
    return await matrix_service.get_matrix_cells_with_current_answer_sets_by_question(
        matrix_id, question_id, entity_set_id
    )


@router.post(
    "/matrices/{matrixId}/cells/batch",
    response_model=List[MatrixCellWithAnswerResponse],
    tags=["workflow-agent"],
    operation_id="get_matrix_cells_batch",
)
@trace_span
async def get_matrix_cells_batch(
    matrix_id: int = Path(alias="matrixId"),
    request: MatrixCellsBatchRequest = ...,
    db: AsyncSession = Depends(get_db_readonly),
):
    """Batch fetch matrix cells using entity_set_filters (entity-ref based).

    Frontend provides entity_set_filters to specify which entities to fetch cells for.
    Finds all cells that reference any of the specified entities (role-agnostic).

    Example: POST /matrices/1/cells/batch
    Body: {
        "entitySetFilters": [
            {"entitySetId": 1, "entityIds": [10, 11, 12]},
            {"entitySetId": 2, "entityIds": [20, 21, 22]}
        ]
    }
    Returns all cells that reference any of those entities in any role.
    """
    if not request.entity_set_filters:
        raise HTTPException(
            status_code=400,
            detail="entitySetFilters must contain at least one filter",
        )

    matrix_service = get_matrix_service(db)
    return await matrix_service.get_matrix_cells_with_current_answer_sets_by_batch(
        matrix_id, request.entity_set_filters
    )


@router.post(
    "/matrices/{matrixId}/reprocess", response_model=MatrixCellReprocessResponse
)
@trace_span
async def reprocess_matrix_cells(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    request: MatrixReprocessRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Reprocess matrix cells based on the specified criteria."""

    # Validate that at least one criteria is provided
    if not any(
        [
            request.whole_matrix,
            request.entity_set_filters,
            request.cell_ids,
        ]
    ):
        raise HTTPException(
            status_code=400,
            detail="At least one reprocessing criteria must be specified (whole_matrix, entity_set_filters, or cell_ids)",
        )

    reprocessing_service = get_reprocessing_service(db)
    cells_reprocessed = await reprocessing_service.reprocess_matrix_cells(
        matrix_id, request
    )

    if cells_reprocessed == 0:
        return MatrixCellReprocessResponse(
            cells_reprocessed=0,
            message="No cells found matching the specified criteria",
        )

    return MatrixCellReprocessResponse(
        cells_reprocessed=cells_reprocessed,
        message=f"Matrix cell reprocessing started successfully for {cells_reprocessed} cells",
    )


@router.post(
    "/matrices/{matrixId}/soft-delete", response_model=MatrixSoftDeleteResponse
)
@trace_span
async def soft_delete_matrix_entities(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    request: MatrixSoftDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Soft delete matrix entities (documents, questions, or matrices) and their related cells."""
    # Validate that at least one criteria is provided
    if not any([request.entity_set_filters, request.matrix_ids]):
        raise HTTPException(
            status_code=400,
            detail="At least one entity type must be specified for deletion (entity_set_filters or matrix_ids)",
        )

    # Validate matrix exists for entity set filter deletions
    if request.entity_set_filters:
        matrix_service = get_matrix_service(db)
        matrix = await matrix_service.get_matrix(matrix_id)
        if not matrix:
            raise HTTPException(status_code=404, detail="Matrix not found")

    async with transaction(db):
        soft_delete_service = get_soft_delete_service(db)
        (
            entities_deleted,
            cells_deleted,
        ) = await soft_delete_service.soft_delete_entities(matrix_id, request)

        if entities_deleted == 0:
            return MatrixSoftDeleteResponse(
                entities_deleted=0,
                cells_deleted=0,
                message="No entities found matching the specified criteria",
            )

        return MatrixSoftDeleteResponse(
            entities_deleted=entities_deleted,
            cells_deleted=cells_deleted,
            message=f"Successfully soft deleted {entities_deleted} entities and {cells_deleted} related cells",
        )


@router.post("/matrices/{matrixId}/duplicate", response_model=MatrixDuplicateResponse)
@trace_span
async def duplicate_matrix(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    request: MatrixDuplicateRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Duplicate a matrix with specified duplication type (documents only, questions only, or full matrix)."""
    matrix_service = get_matrix_service(db)

    # Use the service's duplicate_matrix method which is already transactional
    # TODO: validate ownership
    return await matrix_service.duplicate_matrix(matrix_id, request)


@router.get(
    "/matrices/{matrixId}/template-variables",
    response_model=List[MatrixTemplateVariableResponse],
)
@trace_span
async def get_matrix_template_variables(
    matrix_id: int = Path(alias="matrixId"),
    db: AsyncSession = Depends(get_db_readonly),
) -> List[MatrixTemplateVariableResponse]:
    """Get template variables for a matrix (used for duplication form)."""

    template_service = MatrixTemplateVariableService(db)
    template_variables = await template_service.get_matrix_template_variables(matrix_id)

    return template_variables


@router.get(
    "/matrices/{matrixId}/structure",
    response_model=MatrixStructureResponse,
    tags=["workflow-agent"],
    operation_id="get_matrix_structure",
)
@trace_span
async def get_matrix_structure(
    matrix_id: int = Path(alias="matrixId"),
    current_user: AuthenticatedUser = Depends(get_service_account),
    db: AsyncSession = Depends(get_db_readonly),
) -> MatrixStructureResponse:
    """Get matrix structure metadata for understanding cell data.

    Provides information about:
    - Matrix type and dimensionality
    - Entity sets (what entities are on each axis)
    - Entity roles (DOCUMENT, LEFT, RIGHT, QUESTION)
    - System placeholders (@{{LEFT}}, @{{RIGHT}})
    - Cell structure (what data each cell contains)

    This helps workflow agents understand how to interpret matrix data
    when generating documents from cell data.
    """
    matrix_service = get_matrix_service(db)
    entity_set_service = get_entity_set_service(db)

    # Get matrix
    matrix = await matrix_service.get_matrix(matrix_id, current_user.company_id)
    if not matrix:
        raise HTTPException(status_code=404, detail="Matrix not found")

    # Get entity sets with members
    entity_sets_with_members = await entity_set_service.get_entity_sets_with_members(
        matrix_id, current_user.company_id
    )

    # Build entity set summaries
    entity_set_summaries = []
    for entity_set, members in entity_sets_with_members:
        entity_set_summaries.append(
            EntitySetSummary(
                id=entity_set.id,
                name=entity_set.name,
                entity_type=entity_set.entity_type,
                member_count=len(members),
                description=entity_set.description,
            )
        )

    # Get strategy for this matrix type
    strategy = CellStrategyFactory.get_strategy(matrix.matrix_type, db)
    structure_metadata = strategy.get_structure_metadata()

    return MatrixStructureResponse(
        matrix_id=matrix.id,
        matrix_name=matrix.name,
        matrix_type=matrix.matrix_type,
        entity_sets=entity_set_summaries,
        explanation=structure_metadata.explanation,
        roles_explanation=structure_metadata.roles_explanation,
        system_placeholders=structure_metadata.system_placeholders,
        cell_structure=structure_metadata.cell_structure,
    )
