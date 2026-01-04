from typing import List, Dict, Optional
from fastapi import HTTPException

from packages.matrices.repositories.matrix_template_variable_repository import (
    MatrixTemplateVariableRepository,
)
from packages.questions.repositories.question_template_variable_repository import (
    QuestionTemplateVariableRepository,
)
from packages.matrices.repositories.matrix_repository import MatrixRepository
from packages.matrices.models.domain.matrix_template_variable import (
    MatrixTemplateVariableModel,
    MatrixTemplateVariableCreateModel,
    MatrixTemplateVariableUpdateModel,
)
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class MatrixTemplateVariableService:
    """Service for handling matrix template variable operations."""

    def __init__(self):
        self.template_var_repo = MatrixTemplateVariableRepository()
        self.question_template_var_repo = QuestionTemplateVariableRepository()
        self.matrix_repo = MatrixRepository()

    @trace_span
    async def create_template_variable(
        self,
        matrix_id: int,
        variable_data: MatrixTemplateVariableCreateModel,
        company_id: int,
    ) -> MatrixTemplateVariableModel:
        """Create a new template variable for a matrix."""
        logger.info(
            f"Creating template variable for matrix {matrix_id}: {variable_data.template_string}"
        )

        # Verify matrix exists and belongs to company
        matrix = await self.matrix_repo.get(matrix_id, company_id)
        if not matrix:
            raise HTTPException(status_code=404, detail="Matrix not found")

        # Check if template string already exists for this matrix
        existing = await self.template_var_repo.get_by_template_string(
            matrix_id, variable_data.template_string, company_id
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Template variable '{variable_data.template_string}' already exists for this matrix",
            )

        # Create template variable (matrix_id and company_id should already be in variable_data)
        variable = await self.template_var_repo.create(variable_data)

        logger.info(f"Created template variable with ID: {variable.id}")
        return variable

    @trace_span
    async def get_template_variable(
        self, variable_id: int, company_id: Optional[int] = None
    ) -> Optional[MatrixTemplateVariableModel]:
        """Get a template variable by ID."""
        return await self.template_var_repo.get(variable_id, company_id)

    @trace_span
    async def get_matrix_template_variables(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> List[MatrixTemplateVariableModel]:
        """Get all template variables for a matrix."""
        return await self.template_var_repo.get_by_matrix_id(matrix_id, company_id)

    @trace_span
    async def get_template_mappings(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> Dict[str, str]:
        """Get template string to value mappings for a matrix."""
        return await self.template_var_repo.get_template_mappings(matrix_id, company_id)

    @trace_span
    async def update_template_variable(
        self,
        variable_id: int,
        variable_update: MatrixTemplateVariableUpdateModel,
        company_id: Optional[int] = None,
    ) -> Optional[MatrixTemplateVariableModel]:
        """Update a template variable."""
        # Get the existing variable to check if value is changing
        existing = await self.template_var_repo.get(variable_id, company_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Template variable not found")

        # Check if template_string is being updated and if it conflicts
        if variable_update.template_string is not None:
            conflict = await self.template_var_repo.get_by_template_string(
                existing.matrix_id, variable_update.template_string, company_id
            )
            if conflict and conflict.id != variable_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Template variable '{variable_update.template_string}' already exists for this matrix",
                )

        variable = await self.template_var_repo.update(variable_id, variable_update)

        if (
            variable
            and variable_update.value is not None
            and variable_update.value != existing.value
        ):
            # Value changed, need to track affected questions
            affected_question_ids = await self.get_affected_questions(variable_id)
            if affected_question_ids:
                logger.info(
                    f"Updated template variable {variable_id}, affects {len(affected_question_ids)} questions"
                )
                # TODO: Trigger reprocessing of affected questions

        return variable

    @trace_span
    async def delete_template_variable(
        self, variable_id: int, company_id: Optional[int] = None
    ) -> bool:
        """Delete a template variable."""
        # Check if variable exists and belongs to company
        existing = await self.template_var_repo.get(variable_id, company_id)
        if not existing:
            return False

        # Check if variable is in use
        usage = await self.question_template_var_repo.get_by_template_variable_id(
            variable_id
        )
        if usage:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot delete template variable - it is used by {len(usage)} questions",
            )

        success = await self.template_var_repo.soft_delete(variable_id)
        if success:
            logger.info(f"Deleted template variable {variable_id}")
        return success

    @trace_span
    async def get_affected_questions(self, variable_id: int) -> List[int]:
        """Get list of question IDs that use a specific template variable."""
        return await self.question_template_var_repo.get_questions_by_template_variable(
            variable_id
        )

    @trace_span
    async def get_template_variables_with_usage(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> List[Dict]:
        """Get template variables with usage count for a matrix."""
        return await self.template_var_repo.get_with_usage_count(matrix_id, company_id)
