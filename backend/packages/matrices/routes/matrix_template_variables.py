from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Path
from packages.auth.dependencies import get_current_active_user
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from common.db.scoped import transaction
from packages.matrices.models.schemas.matrix_template_variable import (
    MatrixTemplateVariableCreate,
    MatrixTemplateVariableUpdate,
    MatrixTemplateVariableResponse,
    TemplateVariableUsageResponse,
)
from packages.matrices.services.matrix_template_variable_service import (
    MatrixTemplateVariableService,
)
from packages.matrices.models.domain.matrix_template_variable import (
    MatrixTemplateVariableCreateModel,
    MatrixTemplateVariableUpdateModel,
)
from packages.questions.services.question_template_variable_service import (
    QuestionTemplateVariableService,
)
from packages.matrices.services.reprocessing_service import get_reprocessing_service
from packages.matrices.models.schemas.matrix import MatrixReprocessRequest
from common.core.otel_axiom_exporter import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/matrices/{matrixId}/template-variables/",
    response_model=MatrixTemplateVariableResponse,
)
async def create_template_variable(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    variable_data: MatrixTemplateVariableCreate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Create a new template variable for a matrix."""
    async with transaction():
        template_service = MatrixTemplateVariableService()
        create_model = MatrixTemplateVariableCreateModel(
            template_string=variable_data.template_string,
            value=variable_data.value,
            matrix_id=matrix_id,
            company_id=current_user.company_id,
        )
        return await template_service.create_template_variable(
            matrix_id, create_model, current_user.company_id
        )


@router.get(
    "/matrices/{matrixId}/template-variables/",
    response_model=List[MatrixTemplateVariableResponse],
    tags=["workflow-agent"],
    operation_id="get_template_variables",
)
async def get_matrix_template_variables(
    matrix_id: int = Path(alias="matrixId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Get all template variables for a matrix."""
    template_service = MatrixTemplateVariableService()
    return await template_service.get_matrix_template_variables(
        matrix_id, current_user.company_id
    )


@router.get(
    "/matrices/{matrixId}/template-variables/with-usage",
    response_model=List[TemplateVariableUsageResponse],
)
async def get_template_variables_with_usage(
    matrix_id: int = Path(alias="matrixId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Get template variables with usage count for a matrix."""
    template_service = MatrixTemplateVariableService()
    usage_data = await template_service.get_template_variables_with_usage(
        matrix_id, current_user.company_id
    )

    return [
        TemplateVariableUsageResponse(
            variable=item["variable"], usage_count=item["usage_count"]
        )
        for item in usage_data
    ]


@router.get(
    "/template-variables/{variableId}", response_model=MatrixTemplateVariableResponse
)
async def get_template_variable(
    variable_id: int = Path(alias="variableId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Get a specific template variable by ID."""
    template_service = MatrixTemplateVariableService()
    variable = await template_service.get_template_variable(
        variable_id, current_user.company_id
    )
    if not variable:
        raise HTTPException(status_code=404, detail="Template variable not found")
    return variable


@router.patch(
    "/template-variables/{variableId}", response_model=MatrixTemplateVariableResponse
)
async def update_template_variable(
    variable_id: Annotated[int, Path(alias="variableId")],
    variable_update: MatrixTemplateVariableUpdate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Update a template variable and reprocess affected questions."""
    async with transaction():
        template_service = MatrixTemplateVariableService()
        question_template_service = QuestionTemplateVariableService()
        reprocessing_service = get_reprocessing_service()

        # Get the existing variable to check for changes
        existing = await template_service.get_template_variable(
            variable_id, current_user.company_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Template variable not found")

        # Get affected questions before update
        affected_questions = (
            await question_template_service.get_questions_affected_by_template_change(
                variable_id
            )
        )

        # Update the variable
        update_model = MatrixTemplateVariableUpdateModel(
            **variable_update.model_dump(exclude_unset=True)
        )
        updated_variable = await template_service.update_template_variable(
            variable_id, update_model, current_user.company_id
        )

        # Reprocess affected questions if value changed
        if (
            variable_update.value
            and variable_update.value != existing.value
            and affected_questions
        ):
            reprocess_request = MatrixReprocessRequest(question_ids=affected_questions)
            reprocessed_count = await reprocessing_service.reprocess_matrix_cells(
                existing.matrix_id, reprocess_request
            )
            logger.info(
                f"Updated template variable {variable_id}, reprocessed {reprocessed_count} cells "
                f"for {len(affected_questions)} affected questions"
            )
        else:
            logger.info(
                f"Updated template variable {variable_id} (no reprocessing needed)"
            )

        return updated_variable


@router.delete("/template-variables/{variableId}")
async def delete_template_variable(
    variable_id: int = Path(alias="variableId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Delete a template variable (only if not in use)."""
    async with transaction():
        template_service = MatrixTemplateVariableService()
        success = await template_service.delete_template_variable(
            variable_id, current_user.company_id
        )
        if not success:
            raise HTTPException(status_code=404, detail="Template variable not found")
        return {"message": "Template variable deleted successfully"}


@router.get(
    "/template-variables/{variableId}/affected-questions",
    response_model=List[int],
)
async def get_affected_questions(
    variable_id: int = Path(alias="variableId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Get list of question IDs that would be affected by changes to this template variable."""
    question_template_service = QuestionTemplateVariableService()
    return await question_template_service.get_questions_affected_by_template_change(
        variable_id
    )
