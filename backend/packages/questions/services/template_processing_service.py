from __future__ import annotations
import re
from typing import List, Set
from sqlalchemy.ext.asyncio import AsyncSession

from packages.matrices.repositories.matrix_template_variable_repository import (
    MatrixTemplateVariableRepository,
)
from packages.questions.repositories.question_template_variable_repository import (
    QuestionTemplateVariableRepository,
)
from packages.questions.models.domain.question_template_variable import (
    QuestionTemplateVariableCreateModel,
)
from packages.questions.models.domain.template_validation import (
    TemplateVariableValidationModel,
    TemplateVariableValidationResultModel,
    TemplatePreviewModel,
)
from packages.matrices.models.domain.matrix_enums import EntityRole
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class TemplateProcessingService:
    """Service for processing ID-based template variables in question text."""

    # Pattern for ID-based template variables: #{{123}}
    ID_PATTERN = re.compile(r"#\{\{(\d+)\}\}")

    # Template pattern (ID-based only)
    TEMPLATE_PATTERN = ID_PATTERN

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.template_var_repo = MatrixTemplateVariableRepository(db_session)
        self.question_template_var_repo = QuestionTemplateVariableRepository(db_session)

    @trace_span
    def extract_template_variable_ids(self, text: str) -> Set[int]:
        """Extract template variable IDs from ID-based patterns in text."""
        id_matches = self.ID_PATTERN.findall(text)
        return {int(var_id) for var_id in id_matches}

    @trace_span
    async def resolve_template_variables(self, text: str, matrix_id: int) -> str:
        """Replace ID-based template variables in text with their actual values."""
        template_var_ids = self.extract_template_variable_ids(text)
        if not template_var_ids:
            return text

        # Get template variables for the matrix
        template_vars = await self.template_var_repo.get_by_matrix_id(matrix_id)
        id_to_value = {var.id: var.value for var in template_vars}

        resolved_text = text
        for var_id in template_var_ids:
            pattern = "#{{" + str(var_id) + "}}"
            if var_id in id_to_value:
                resolved_text = resolved_text.replace(pattern, id_to_value[var_id])
                logger.debug(
                    f"Resolved template variable #{var_id} to '{id_to_value[var_id]}'"
                )
            else:
                logger.warning(
                    f"Template variable ID '{var_id}' not found in matrix {matrix_id}"
                )

        return resolved_text

    @trace_span
    async def validate_template_variables(
        self, text: str, matrix_id: int
    ) -> TemplateVariableValidationResultModel:
        """Validate that all template variable IDs in text exist in the matrix."""
        variable_ids = self.extract_template_variable_ids(text)
        if not variable_ids:
            return TemplateVariableValidationResultModel(validations=[])

        # Get all template variables for the matrix
        template_vars = await self.template_var_repo.get_by_matrix_id(matrix_id)
        existing_ids = {var.id for var in template_vars}

        validations = [
            TemplateVariableValidationModel(
                template_variable_id=var_id, exists=var_id in existing_ids
            )
            for var_id in variable_ids
        ]

        return TemplateVariableValidationResultModel(validations=validations)

    @trace_span
    async def get_missing_template_variables(
        self, text: str, matrix_id: int
    ) -> List[int]:
        """Get list of template variable IDs in text that don't exist in the matrix."""
        validation = await self.validate_template_variables(text, matrix_id)
        return [v.template_variable_id for v in validation.validations if not v.exists]

    @trace_span
    async def sync_question_template_variables(
        self, question_id: int, question_text: str, matrix_id: int, company_id: int
    ) -> List[int]:
        """Sync template variable associations for a question based on its text.

        Steps:
        1. Extract all template variable IDs from the question text
        2. Get existing associations for the question (non-soft-deleted)
        3. Add new template variables found in text that aren't already associated
        4. Soft delete existing associations for variables not found in text
        """
        # Step 1: Extract template variable IDs from ID-based patterns
        new_template_var_ids = self.extract_template_variable_ids(question_text)
        logger.info(
            f"Question {question_id}: Found {len(new_template_var_ids)} template variables: {list(new_template_var_ids)}"
        )

        # Step 2: Get current associations (non-soft-deleted)
        current_associations = await self.question_template_var_repo.get_by_question_id(
            question_id, company_id
        )
        current_template_var_ids = {
            assoc.template_variable_id for assoc in current_associations
        }
        logger.info(
            f"Question {question_id}: Currently has {len(current_template_var_ids)} associations: {list(current_template_var_ids)}"
        )

        # Get template variables for logging
        template_vars = await self.template_var_repo.get_by_matrix_id(matrix_id)
        id_to_name = {var.id: var.template_string for var in template_vars}

        # Step 3: Determine what needs to be added and what needs to be removed
        to_add = new_template_var_ids - current_template_var_ids
        to_remove = current_template_var_ids - new_template_var_ids

        logger.info(
            f"Question {question_id}: Will add {len(to_add)} associations: {[id_to_name.get(id, f'ID-{id}') for id in to_add]}"
        )
        logger.info(
            f"Question {question_id}: Will soft delete {len(to_remove)} associations: {[id_to_name.get(id, f'ID-{id}') for id in to_remove]}"
        )

        # Step 4: Add new associations
        for template_var_id in to_add:
            # Check if there's a soft deleted association we can restore
            existing = (
                await self.question_template_var_repo.find_soft_deleted_association(
                    question_id, template_var_id, company_id
                )
            )

            if existing:
                # Restore soft deleted association
                success = await self.question_template_var_repo.restore_soft_deleted_association(
                    existing.id
                )
                if success:
                    logger.info(
                        f"Question {question_id}: Restored soft deleted association for template variable {id_to_name.get(template_var_id, template_var_id)}"
                    )
            else:
                # Create new association
                create_model = QuestionTemplateVariableCreateModel(
                    question_id=question_id,
                    template_variable_id=template_var_id,
                    company_id=company_id,
                )
                await self.question_template_var_repo.create(create_model)
                logger.info(
                    f"Question {question_id}: Created new association for template variable {id_to_name.get(template_var_id, template_var_id)}"
                )

        # Step 5: Soft delete removed associations
        for template_var_id in to_remove:
            # Find the association to soft delete
            association_to_delete = None
            for assoc in current_associations:
                if assoc.template_variable_id == template_var_id:
                    association_to_delete = assoc
                    break

            if association_to_delete:
                await self.question_template_var_repo.soft_delete(
                    association_to_delete.id
                )
                logger.info(
                    f"Question {question_id}: Soft deleted association for template variable {id_to_name.get(template_var_id, template_var_id)}"
                )

        await self.db_session.flush()

        logger.info(
            f"Question {question_id}: Sync complete. Final template variable count: {len(new_template_var_ids)}"
        )
        return list(new_template_var_ids)

    @trace_span
    async def get_questions_using_template_variable(
        self, template_variable_id: int
    ) -> List[int]:
        """Get list of question IDs that use a specific template variable."""
        return await self.question_template_var_repo.get_questions_by_template_variable(
            template_variable_id
        )

    @trace_span
    async def get_questions_using_any_template_variables(
        self, template_variable_ids: List[int]
    ) -> List[int]:
        """Get list of question IDs that use any of the specified template variables."""
        return await self.question_template_var_repo.bulk_get_questions_by_variables(
            template_variable_ids
        )

    @trace_span
    def has_template_variables(self, text: str) -> bool:
        """Check if text contains any template variables."""
        return bool(self.TEMPLATE_PATTERN.search(text))

    @trace_span
    def extract_document_placeholder_roles(self, text: str) -> Set[EntityRole]:
        """Extract document placeholder roles from text (@{{LEFT}}, @{{RIGHT}}, @{{DOCUMENT}})."""
        doc_pattern = re.compile(r"@\{\{(LEFT|RIGHT|DOCUMENT)\}\}")
        matches = doc_pattern.findall(text)
        # Convert string matches to EntityRole enums
        return {EntityRole(match.lower()) for match in matches}

    @trace_span
    def has_document_placeholders(self, text: str) -> bool:
        """Check if text contains any document placeholders."""
        doc_pattern = re.compile(r"@\{\{(LEFT|RIGHT|DOCUMENT)\}\}")
        return bool(doc_pattern.search(text))

    @trace_span
    def resolve_document_placeholders(
        self, text: str, entity_refs: List["DocumentReference"]
    ) -> str:  # noqa: F821
        """Replace document placeholders in text with actual entity references.

        Args:
            text: Text containing @{{LEFT}}, @{{RIGHT}}, @{{DOCUMENT}} placeholders
            entity_refs: List of DocumentReference objects with document_id and role (EntityRole enum)

        Returns:
            Text with placeholders replaced by "Document {id}"
        """
        if not self.has_document_placeholders(text):
            return text

        # Build a mapping of EntityRole -> document_id
        role_to_entity_id = {}
        for entity_ref in entity_refs:
            if entity_ref.role == EntityRole.LEFT:
                role_to_entity_id[EntityRole.LEFT] = entity_ref.document_id
            elif entity_ref.role == EntityRole.RIGHT:
                role_to_entity_id[EntityRole.RIGHT] = entity_ref.document_id
            elif entity_ref.role == EntityRole.DOCUMENT:
                role_to_entity_id[EntityRole.DOCUMENT] = entity_ref.document_id

        resolved_text = text

        # Replace @{{LEFT}}
        if EntityRole.LEFT in role_to_entity_id:
            doc_reference = f"Document {role_to_entity_id[EntityRole.LEFT]}"
            resolved_text = resolved_text.replace("@{{LEFT}}", doc_reference)
            logger.debug(f"Resolved @{{{{LEFT}}}} to '{doc_reference}'")
        else:
            logger.warning("@{{LEFT}} found in text but no LEFT entity_ref in cell")

        # Replace @{{RIGHT}}
        if EntityRole.RIGHT in role_to_entity_id:
            doc_reference = f"Document {role_to_entity_id[EntityRole.RIGHT]}"
            resolved_text = resolved_text.replace("@{{RIGHT}}", doc_reference)
            logger.debug(f"Resolved @{{{{RIGHT}}}} to '{doc_reference}'")
        else:
            logger.warning("@{{RIGHT}} found in text but no RIGHT entity_ref in cell")

        # Replace @{{DOCUMENT}}
        if EntityRole.DOCUMENT in role_to_entity_id:
            doc_reference = f"Document {role_to_entity_id[EntityRole.DOCUMENT]}"
            resolved_text = resolved_text.replace("@{{DOCUMENT}}", doc_reference)
            logger.debug(f"Resolved @{{{{DOCUMENT}}}} to '{doc_reference}'")

        return resolved_text

    @trace_span
    async def preview_resolved_text(
        self, text: str, matrix_id: int
    ) -> TemplatePreviewModel:
        """Preview how text would look with template variables resolved."""
        return TemplatePreviewModel(
            original=text,
            resolved=await self.resolve_template_variables(text, matrix_id),
            variables_used=list(self.extract_template_variable_ids(text)),
        )
