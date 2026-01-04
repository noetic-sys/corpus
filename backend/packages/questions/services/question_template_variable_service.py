from typing import List, Optional
from fastapi import HTTPException

from packages.questions.repositories.question_template_variable_repository import (
    QuestionTemplateVariableRepository,
)
from packages.questions.repositories.question_repository import QuestionRepository
from packages.matrices.repositories.matrix_template_variable_repository import (
    MatrixTemplateVariableRepository,
)
from packages.questions.models.domain.question_template_variable import (
    QuestionTemplateVariableModel,
    QuestionTemplateVariableCreateModel,
)
from packages.questions.models.domain.template_validation import (
    QuestionTemplateValidationModel,
)
from packages.questions.services.template_processing_service import (
    TemplateProcessingService,
)
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class QuestionTemplateVariableService:
    """Service for managing question-template variable associations."""

    def __init__(self):
        self.question_template_var_repo = QuestionTemplateVariableRepository()
        self.question_repo = QuestionRepository()
        self.template_var_repo = MatrixTemplateVariableRepository()
        self.template_processing_service = TemplateProcessingService()

    @trace_span
    async def create_association(
        self,
        association_data: QuestionTemplateVariableCreateModel,
        company_id: Optional[int] = None,
    ) -> QuestionTemplateVariableModel:
        """Create a new question-template variable association."""
        # Use company_id from data (parameter will be deprecated)
        effective_company_id = association_data.company_id

        # Verify question exists
        question = await self.question_repo.get(
            association_data.question_id, effective_company_id
        )
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Verify template variable exists
        template_var = await self.template_var_repo.get(
            association_data.template_variable_id, effective_company_id
        )
        if not template_var:
            raise HTTPException(status_code=404, detail="Template variable not found")

        # Verify they belong to the same matrix and company
        if question.matrix_id != template_var.matrix_id:
            raise HTTPException(
                status_code=400,
                detail="Question and template variable must belong to the same matrix",
            )
        if question.company_id != template_var.company_id:
            raise HTTPException(
                status_code=400,
                detail="Question and template variable must belong to the same company",
            )

        # Check if association already exists
        exists = await self.question_template_var_repo.exists(
            association_data.question_id,
            association_data.template_variable_id,
            effective_company_id,
        )
        if exists:
            raise HTTPException(status_code=400, detail="Association already exists")

        # Create association
        association = await self.question_template_var_repo.create(association_data)

        logger.info(
            f"Created association between question {association_data.question_id} "
            f"and template variable {association_data.template_variable_id}"
        )
        return association

    @trace_span
    async def get_question_template_variables(
        self, question_id: int, company_id: Optional[int] = None
    ) -> List[QuestionTemplateVariableModel]:
        """Get all template variable associations for a question."""
        return await self.question_template_var_repo.get_by_question_id(
            question_id, company_id
        )

    @trace_span
    async def get_questions_using_template_variable(
        self, template_variable_id: int, company_id: Optional[int] = None
    ) -> List[QuestionTemplateVariableModel]:
        """Get all questions using a specific template variable."""
        return await self.question_template_var_repo.get_by_template_variable_id(
            template_variable_id, company_id
        )

    @trace_span
    async def sync_question_from_text(
        self, question_id: int, company_id: Optional[int] = None
    ) -> List[int]:
        """Automatically sync template variable associations based on question text."""
        # Get the question
        question = await self.question_repo.get(question_id, company_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Use template processing service to sync
        template_var_ids = (
            await self.template_processing_service.sync_question_template_variables(
                question_id,
                question.question_text,
                question.matrix_id,
                question.company_id,
            )
        )

        logger.info(
            f"Synced question {question_id} with {len(template_var_ids)} template variables"
        )
        return template_var_ids

    @trace_span
    async def bulk_sync_questions_from_text(
        self, question_ids: List[int], company_id: Optional[int] = None
    ) -> int:
        """Bulk sync template variable associations for multiple questions."""
        synced_count = 0

        for question_id in question_ids:
            try:
                await self.sync_question_from_text(question_id, company_id)
                synced_count += 1
            except Exception as e:
                logger.error(f"Failed to sync question {question_id}: {e}")

        logger.info(f"Bulk synced {synced_count}/{len(question_ids)} questions")
        return synced_count

    @trace_span
    async def remove_association(
        self,
        question_id: int,
        template_variable_id: int,
        company_id: Optional[int] = None,
    ) -> bool:
        """Remove a specific question-template variable association."""
        # Find the association
        associations = await self.question_template_var_repo.get_by_question_id(
            question_id, company_id
        )
        association_to_delete = None

        for assoc in associations:
            if assoc.template_variable_id == template_variable_id:
                association_to_delete = assoc
                break

        if not association_to_delete:
            return False

        # Soft delete the association
        success = await self.question_template_var_repo.soft_delete(
            association_to_delete.id
        )
        if success:
            logger.info(
                f"Soft deleted association between question {question_id} "
                f"and template variable {template_variable_id}"
            )
        return success

    @trace_span
    async def remove_all_question_associations(
        self, question_id: int, company_id: Optional[int] = None
    ) -> int:
        """Soft delete all template variable associations for a question."""
        count = await self.question_template_var_repo.delete_by_question_id(
            question_id, company_id
        )
        if count > 0:
            logger.info(
                f"Soft deleted {count} template variable associations for question {question_id}"
            )
        return count

    @trace_span
    async def get_questions_affected_by_template_change(
        self, template_variable_id: int, company_id: Optional[int] = None
    ) -> List[int]:
        """Get list of question IDs that would be affected by a template variable change."""
        return await self.question_template_var_repo.get_questions_by_template_variable(
            template_variable_id, company_id
        )

    @trace_span
    async def validate_question_template_variables(
        self, question_id: int, company_id: Optional[int] = None
    ) -> QuestionTemplateValidationModel:
        """Validate that a question's template variables are properly associated."""
        question = await self.question_repo.get(question_id, company_id)
        if not question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Extract variable IDs from question text
        variable_ids_in_text = (
            self.template_processing_service.extract_template_variable_ids(
                question.question_text
            )
        )

        # Get associated variable IDs
        associations = await self.get_question_template_variables(
            question_id, company_id
        )
        associated_variable_ids = {assoc.template_variable_id for assoc in associations}

        return QuestionTemplateValidationModel(
            question_id=question_id,
            variables_in_text=[str(id) for id in variable_ids_in_text],
            associated_variables=[str(id) for id in associated_variable_ids],
            missing_associations=[
                str(id) for id in (variable_ids_in_text - associated_variable_ids)
            ],
            extra_associations=[
                str(id) for id in (associated_variable_ids - variable_ids_in_text)
            ],
            is_valid=variable_ids_in_text == associated_variable_ids,
        )
