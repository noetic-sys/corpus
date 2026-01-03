from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

import re
from packages.questions.repositories.question_repository import QuestionRepository
from packages.matrices.repositories.matrix_repository import MatrixRepository
from packages.matrices.repositories.matrix_template_variable_repository import (
    MatrixTemplateVariableRepository,
)
from packages.questions.repositories.question_option_repository import (
    QuestionOptionSetRepository,
    QuestionOptionRepository,
)
from packages.ai_model.repositories.ai_model_repository import AIModelRepository
from packages.questions.models.domain.question import (
    QuestionModel,
    QuestionCreateModel,
    QuestionUpdateModel,
)
from packages.questions.models.domain.question_with_options import (
    QuestionWithOptionsCreateModel,
    QuestionWithOptionsUpdateModel,
)
from packages.matrices.models.schemas.matrix import (
    MatrixReprocessRequest,
    EntitySetFilter,
)
from packages.matrices.models.domain.matrix_enums import EntityType, EntityRole
from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.questions.utils.template_validation import validate_template_variables
from packages.questions.services.question_option_service import QuestionOptionService
from packages.matrices.services.reprocessing_service import ReprocessingService
from packages.matrices.services.entity_set_service import get_entity_set_service
from packages.questions.services.question_template_variable_service import (
    QuestionTemplateVariableService,
)
from packages.questions.models.domain.question_template_variable import (
    QuestionTemplateVariableCreateModel,
)
from packages.questions.models.domain.question_option import (
    QuestionOptionSetCreateModel,
    QuestionOptionCreateModel,
)
from packages.billing.services.usage_service import UsageService
from packages.billing.services.quota_service import QuotaService

logger = get_logger(__name__)


class QuestionService:
    """Service for handling question operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.question_repo = QuestionRepository(db_session)
        self.matrix_repo = MatrixRepository(db_session)
        self.template_var_repo = MatrixTemplateVariableRepository()
        self.option_set_repo = QuestionOptionSetRepository()
        self.option_repo = QuestionOptionRepository()
        self.question_option_service = QuestionOptionService(db_session)
        self.reprocessing_service = ReprocessingService(db_session)
        self.ai_model_repo = AIModelRepository()

    async def _get_available_template_variables(self, matrix_id: int) -> List[str]:
        """Get list of available template variable names for a matrix."""
        template_vars = await self.template_var_repo.get_by_matrix_id(matrix_id)
        return [var.template_string for var in template_vars]

    async def _validate_question_template_variables(
        self, question_text: str, matrix_id: int, available_variables: List[str]
    ) -> None:
        """Validate template variables in question text and raise HTTPException if invalid."""
        # Get matrix to check its type
        matrix = await self.matrix_repo.get(matrix_id)
        if not matrix:
            raise HTTPException(status_code=404, detail="Matrix not found")

        validation_result = validate_template_variables(
            question_text, matrix.matrix_type, available_variables
        )

        if not validation_result.is_valid:
            error_msg = f"Invalid template variables in question: {', '.join(validation_result.errors)}"
            logger.warning(
                f"Template validation failed for matrix {matrix_id}: {error_msg}"
            )
            raise HTTPException(status_code=400, detail=error_msg)

        # Log warnings but don't block
        if validation_result.warnings:
            logger.warning(
                f"Template validation warnings for matrix {matrix_id}: {', '.join(validation_result.warnings)}"
            )

    async def _validate_ai_model_selection(self, ai_model_id: Optional[int]) -> None:
        """Validate AI model selection and raise HTTPException if invalid."""
        if ai_model_id is None:
            return  # No model specified, will use global default

        # Check if model exists and is enabled
        ai_model = await self.ai_model_repo.get_with_provider(ai_model_id)
        if not ai_model:
            raise HTTPException(
                status_code=400, detail=f"AI model with ID {ai_model_id} not found"
            )

        if not ai_model.enabled:
            raise HTTPException(
                status_code=400,
                detail=f"AI model '{ai_model.display_name}' is not enabled",
            )

        # Check if provider is enabled
        if ai_model.provider and not ai_model.provider.enabled:
            raise HTTPException(
                status_code=400,
                detail=f"AI provider '{ai_model.provider.display_name}' is not enabled",
            )

    def _validate_answer_count_configuration(
        self, min_answers: int, max_answers: Optional[int]
    ) -> None:
        """Validate min/max answer configuration and raise HTTPException if invalid."""
        if min_answers < 1:
            raise HTTPException(
                status_code=400, detail="min_answers must be at least 1"
            )

        if max_answers is not None and max_answers < min_answers:
            raise HTTPException(
                status_code=400,
                detail=f"max_answers ({max_answers}) must be greater than or equal to min_answers ({min_answers})",
            )

    @trace_span
    async def create_question(
        self, matrix_id: int, question_data: QuestionCreateModel, company_id: int
    ) -> QuestionModel:
        """Create a new question."""
        logger.info(
            f"Creating question for matrix {matrix_id}: {question_data.question_text}"
        )
        logger.warning(f"question data: {question_data}")

        # Verify matrix exists and belongs to company
        matrix = await self.matrix_repo.get(matrix_id)
        if not matrix:
            raise HTTPException(status_code=404, detail="Matrix not found")

        # Validate template variables in question text
        available_variables = await self._get_available_template_variables(matrix_id)
        await self._validate_question_template_variables(
            question_data.question_text, matrix_id, available_variables
        )

        # Validate AI model selection if provided
        await self._validate_ai_model_selection(question_data.ai_model_id)

        # Validate answer count configuration
        self._validate_answer_count_configuration(
            question_data.min_answers, question_data.max_answers
        )

        question_create = QuestionCreateModel(
            question_text=question_data.question_text,
            question_type_id=question_data.question_type_id,
            ai_model_id=question_data.ai_model_id,
            ai_config_override=question_data.ai_config_override,
            label=question_data.label,
            min_answers=question_data.min_answers,
            max_answers=question_data.max_answers,
            use_agent_qa=question_data.use_agent_qa,
            matrix_id=matrix_id,
            company_id=company_id,
        )
        question = await self.question_repo.create(question_create)

        logger.info(f"Created question with ID: {question.id}")
        return question

    @trace_span
    async def get_question(
        self, question_id: int, company_id: Optional[int] = None
    ) -> Optional[QuestionModel]:
        """Get a question by ID with optional company filtering."""
        return await self.question_repo.get(question_id, company_id)

    @trace_span
    async def update_question(
        self,
        question_id: int,
        question_update: QuestionUpdateModel,
        company_id: Optional[int] = None,
    ) -> Optional[QuestionModel]:
        """Update a question."""
        # Check if question exists first
        existing_question = await self.question_repo.get(question_id, company_id)
        if not existing_question:
            return None

        # If question_text is being updated, validate template variables
        if question_update.question_text is not None:
            # Validate template variables in the new question text
            available_variables = await self._get_available_template_variables(
                existing_question.matrix_id
            )
            await self._validate_question_template_variables(
                question_update.question_text,
                existing_question.matrix_id,
                available_variables,
            )

        # If AI model is being updated, validate selection
        if question_update.ai_model_id is not None:
            await self._validate_ai_model_selection(question_update.ai_model_id)

        # If answer count configuration is being updated, validate it
        if (
            question_update.min_answers is not None
            or question_update.max_answers is not None
        ):
            # Use existing values as defaults for validation
            min_val = (
                question_update.min_answers
                if question_update.min_answers is not None
                else existing_question.min_answers
            )
            max_val = (
                question_update.max_answers
                if question_update.max_answers is not None
                else existing_question.max_answers
            )
            self._validate_answer_count_configuration(min_val, max_val)

        update_data = question_update.model_dump(exclude_unset=True)
        logger.info(f"Updating question {question_id} with data: {update_data}")
        question = await self.question_repo.update(question_id, question_update)
        if question:
            logger.info(
                f"Updated question {question_id} - final values: min_answers={question.min_answers}, max_answers={question.max_answers}"
            )
        return question

    @trace_span
    async def update_question_label(
        self, question_id: int, label_update: QuestionUpdateModel
    ) -> Optional[QuestionModel]:
        """Update only the label of a question. This operation does not trigger reprocessing."""
        question = await self.question_repo.update(question_id, label_update)
        if question:
            logger.info(
                f"Updated label for question {question_id} to: {label_update.label}"
            )
        return question

    @trace_span
    async def delete_question(
        self, question_id: int, company_id: Optional[int] = None
    ) -> bool:
        """Delete a question with optional company access control."""
        success = await self.question_repo.delete(question_id, company_id)
        if success:
            logger.info(f"Deleted question {question_id}")
        return success

    @trace_span
    async def get_questions_for_matrix(
        self, matrix_id: int, company_id: Optional[int] = None
    ) -> List[QuestionModel]:
        """Get all questions for a matrix with optional company filtering."""
        return await self.question_repo.get_by_matrix_id(matrix_id, company_id)

    @trace_span
    async def create_question_with_options(
        self,
        matrix_id: int,
        question_data: QuestionWithOptionsCreateModel,
        company_id: int,
    ) -> QuestionModel:
        """Create a question with options transactionally."""
        logger.info(
            f"Creating question with options for matrix {matrix_id}: {question_data.question_text}"
        )

        # Verify matrix exists and belongs to company
        matrix = await self.matrix_repo.get(matrix_id)
        if not matrix:
            raise HTTPException(status_code=404, detail="Matrix not found")

        # Validate template variables in question text
        available_variables = await self._get_available_template_variables(matrix_id)
        await self._validate_question_template_variables(
            question_data.question_text, matrix_id, available_variables
        )

        # Validate AI model selection if provided
        await self._validate_ai_model_selection(question_data.ai_model_id)

        # Validate answer count configuration
        self._validate_answer_count_configuration(
            question_data.min_answers, question_data.max_answers
        )

        # Create question using proper domain model
        question_create = QuestionCreateModel(
            question_text=question_data.question_text,
            question_type_id=question_data.question_type_id,
            ai_model_id=question_data.ai_model_id,
            ai_config_override=question_data.ai_config_override,
            label=question_data.label,
            min_answers=question_data.min_answers,
            max_answers=question_data.max_answers,
            use_agent_qa=question_data.use_agent_qa,
            matrix_id=matrix_id,
            company_id=company_id,
        )
        question = await self.question_repo.create(question_create)

        # If options are provided, create option set and options
        if question_data.options:
            try:
                # Create option set
                option_set = await self.option_set_repo.create_for_question(question.id)

                # Create options using proper models
                await self.option_repo.bulk_create_for_set(
                    option_set.id, question_data.options
                )

                logger.info(
                    f"Created question {question.id} with {len(question_data.options)} options"
                )
            except Exception as e:
                logger.error(
                    f"Failed to create options for question {question.id}: {e}"
                )
                raise HTTPException(
                    status_code=500, detail="Failed to create question with options"
                )

        logger.info(f"Created question with ID: {question.id}")
        return question

    def _needs_reprocessing_for_options_update(
        self, question_update: QuestionWithOptionsUpdateModel
    ) -> bool:
        """Check if the question with options update requires reprocessing of cells."""
        update_data = question_update.model_dump(exclude_unset=True)

        # Fields that don't require reprocessing
        non_reprocessing_fields = {"label"}

        # Check if any field that requires reprocessing is being updated
        reprocessing_fields = set(update_data.keys()) - non_reprocessing_fields
        return len(reprocessing_fields) > 0

    @trace_span
    async def update_question_with_options_and_reprocess(
        self,
        matrix_id: int,
        question_id: int,
        question_update: QuestionWithOptionsUpdateModel,
        company_id: int,
    ) -> QuestionModel:
        """Update a question with options and automatically reprocess affected cells."""

        # First, verify the question exists and belongs to this matrix and company
        existing_question = await self.get_question(question_id, company_id)
        if existing_question is None:
            raise HTTPException(status_code=404, detail="Question not found")
        if existing_question.matrix_id != matrix_id:
            raise HTTPException(
                status_code=400, detail="Question does not belong to this matrix"
            )

        # Update question fields if provided
        # Get all fields from the update model, excluding 'options' which is handled separately
        # NOTE: We use exclude_unset=True instead of exclude_none=True to preserve intentional None values
        question_fields = question_update.model_dump(
            exclude_unset=True, exclude={"options"}
        )

        logger.info(f"Question update fields extracted: {question_fields}")

        if question_fields:
            basic_update = QuestionUpdateModel(**question_fields)

            logger.info(
                f"Created QuestionUpdate object with min_answers={getattr(basic_update, 'min_answers', 'NOT_SET')}, max_answers={getattr(basic_update, 'max_answers', 'NOT_SET')}"
            )
            question = await self.update_question(question_id, basic_update, company_id)
            if question is None:
                raise HTTPException(status_code=404, detail="Failed to update question")
        else:
            question = existing_question

        # Update options if provided
        if question_update.options is not None:
            # Delete existing option set if it exists
            await self.question_option_service.delete_option_set(question_id)

            # Create new option set with options if options were provided
            if question_update.options:
                option_set_create = QuestionOptionSetCreateModel(
                    options=question_update.options
                )
                await self.question_option_service.create_option_set(
                    question_id, option_set_create
                )

        # Only reprocess if the update affects processing-relevant fields
        if self._needs_reprocessing_for_options_update(question_update):
            # Check agentic QA quota if question uses agentic mode (raises 429 if exceeded)
            if question.use_agent_qa:
                quota_service = QuotaService(self.db_session)
                await quota_service.check_agentic_qa_quota(company_id)

            # Get question entity set to build reprocess request
            entity_set_service = get_entity_set_service(self.db_session)
            question_entity_set = await entity_set_service.get_entity_set_by_type(
                matrix_id, EntityType.QUESTION
            )

            if not question_entity_set:
                raise HTTPException(
                    status_code=500, detail="Question entity set not found for matrix"
                )

            reprocess_request = MatrixReprocessRequest(
                entity_set_filters=[
                    EntitySetFilter(
                        entity_set_id=question_entity_set.id,
                        entity_ids=[question_id],
                        role=EntityRole.QUESTION,
                    )
                ]
            )
            reprocessed_count = await self.reprocessing_service.reprocess_matrix_cells(
                matrix_id, reprocess_request
            )
            logger.info(
                f"Updated question {question_id} in matrix {matrix_id} and reprocessed {reprocessed_count} cells"
            )

            # Track agentic QA usage if question uses agentic mode
            if question.use_agent_qa and reprocessed_count > 0:
                usage_service = UsageService()
                await usage_service.track_agentic_qa(
                    company_id=company_id,
                    quantity=reprocessed_count,
                    question_id=question_id,
                )
                logger.info(
                    f"Tracked agentic QA usage for {reprocessed_count} cells (question {question_id})"
                )
        else:
            logger.info(
                f"Updated question {question_id} in matrix {matrix_id} (label-only update, skipped reprocessing)"
            )

        return question

    @trace_span
    async def duplicate_question(
        self, question_id: int, company_id: Optional[int] = None
    ) -> QuestionModel:
        """Duplicate a question within the same matrix, including its options and template variable associations."""

        # Get the original question
        original_question = await self.get_question(question_id, company_id)
        if not original_question:
            raise HTTPException(status_code=404, detail="Question not found")

        # Create new question data based on original (no ID remapping needed for same matrix)
        question_create = QuestionCreateModel(
            question_text=original_question.question_text,
            matrix_id=original_question.matrix_id,
            company_id=original_question.company_id,
            question_type_id=original_question.question_type_id,
            ai_model_id=original_question.ai_model_id,
            ai_config_override=original_question.ai_config_override,
            label=(
                f"{original_question.label} (Copy)" if original_question.label else None
            ),
            min_answers=original_question.min_answers,
            max_answers=original_question.max_answers,
            use_agent_qa=original_question.use_agent_qa,
        )

        # Create the duplicate question
        duplicate_question = await self.question_repo.create(question_create)

        # Get and duplicate options if they exist
        original_option_set = (
            await self.question_option_service.get_option_set_with_options(question_id)
        )

        if original_option_set and original_option_set.options:

            # Convert option values to the correct model type
            option_create_models = [
                QuestionOptionCreateModel(value=option.value)
                for option in original_option_set.options
            ]

            # Create new option set for the duplicate question
            option_set_create = QuestionOptionSetCreateModel(
                options=option_create_models
            )
            await self.question_option_service.create_option_set(
                duplicate_question.id, option_set_create
            )

        # Duplicate template variable associations (same IDs since it's the same matrix)
        await self._duplicate_template_variable_associations_same_matrix(
            question_id, duplicate_question.id
        )

        logger.info(
            f"Duplicated question {question_id} as new question {duplicate_question.id}"
        )
        return duplicate_question

    @trace_span
    async def _duplicate_template_variable_associations_same_matrix(
        self, source_question_id: int, target_question_id: int
    ) -> None:
        """Duplicate template variable associations for questions in the same matrix."""

        template_var_service = QuestionTemplateVariableService(self.db_session)

        # Get template variable associations from source question
        source_associations = (
            await template_var_service.get_question_template_variables(
                source_question_id
            )
        )

        if not source_associations:
            logger.info(
                f"No template variable associations found for source question {source_question_id}"
            )
            return

        # Create new associations for the duplicate question (same template variable IDs)
        for source_assoc in source_associations:
            new_assoc_data = QuestionTemplateVariableCreateModel(
                question_id=target_question_id,
                template_variable_id=source_assoc.template_variable_id,
                company_id=source_assoc.company_id,
            )

            await template_var_service.create_association(new_assoc_data)
            logger.info(
                f"Duplicated template variable association: question {target_question_id} -> template var {source_assoc.template_variable_id}"
            )

        logger.info(
            f"Duplicated {len(source_associations)} template variable associations for question {target_question_id}"
        )

    @trace_span
    async def duplicate_questions_to_matrix(
        self, source_matrix_id: int, target_matrix_id: int
    ) -> List[QuestionModel]:
        """Duplicate all questions from source matrix to target matrix, including their options."""
        logger.info(
            f"Duplicating questions from matrix {source_matrix_id} to matrix {target_matrix_id}"
        )

        # Get all questions from source matrix
        source_questions = await self.get_questions_for_matrix(source_matrix_id)

        if not source_questions or source_questions == []:
            logger.info(f"No questions found in source matrix {source_matrix_id}")
            return []

        first_question = source_questions[0]
        duplicated_questions = []
        for source_question in source_questions:
            # Create new question data for target matrix
            question_create = QuestionCreateModel(
                question_text=source_question.question_text,
                matrix_id=target_matrix_id,
                company_id=first_question.company_id,
                question_type_id=source_question.question_type_id,
                ai_model_id=source_question.ai_model_id,
                ai_config_override=source_question.ai_config_override,
                label=source_question.label,
                min_answers=source_question.min_answers,
                max_answers=source_question.max_answers,
                use_agent_qa=source_question.use_agent_qa,
            )

            # Create the duplicate question
            duplicate_question = await self.question_repo.create(question_create)

            # Duplicate options if they exist
            original_option_set = (
                await self.question_option_service.get_option_set_with_options(
                    source_question.id
                )
            )

            if original_option_set and original_option_set.options:

                # Convert option values to the correct model type
                option_create_models = [
                    QuestionOptionCreateModel(value=option.value)
                    for option in original_option_set.options
                ]

                # Create new option set for the duplicate question
                option_set_create = QuestionOptionSetCreateModel(
                    options=option_create_models
                )
                await self.question_option_service.create_option_set(
                    duplicate_question.id, option_set_create
                )

            duplicated_questions.append(duplicate_question)

        logger.info(
            f"Duplicated {len(duplicated_questions)} questions to matrix {target_matrix_id}"
        )
        return duplicated_questions

    @trace_span
    async def duplicate_questions_to_matrix_with_template_mapping(
        self,
        source_matrix_id: int,
        target_matrix_id: int,
        template_variable_id_mapping: dict[int, int],
    ) -> List[QuestionModel]:
        """Duplicate questions with template variable ID remapping and associations."""
        logger.info(
            f"Duplicating questions from matrix {source_matrix_id} to matrix {target_matrix_id} with template mapping"
        )

        # Get all questions from source matrix
        source_questions = await self.get_questions_for_matrix(source_matrix_id)

        if not source_questions or source_questions == []:
            logger.info(f"No questions found in source matrix {source_matrix_id}")
            return []

        first_question = source_questions[0]
        duplicated_questions = []
        for source_question in source_questions:
            # Update question text to use new template variable IDs
            updated_question_text = self._remap_template_variable_ids_in_text(
                source_question.question_text, template_variable_id_mapping
            )

            # Create new question data for target matrix
            question_create = QuestionCreateModel(
                question_text=updated_question_text,
                matrix_id=target_matrix_id,
                company_id=first_question.company_id,
                question_type_id=source_question.question_type_id,
                ai_model_id=source_question.ai_model_id,
                ai_config_override=source_question.ai_config_override,
                label=source_question.label,
                min_answers=source_question.min_answers,
                max_answers=source_question.max_answers,
                use_agent_qa=source_question.use_agent_qa,
            )

            # Create the duplicate question
            duplicate_question = await self.question_repo.create(question_create)

            # Duplicate options if they exist
            original_option_set = (
                await self.question_option_service.get_option_set_with_options(
                    source_question.id
                )
            )

            if original_option_set and original_option_set.options:

                # Convert option values to the correct model type
                option_create_models = [
                    QuestionOptionCreateModel(value=option.value)
                    for option in original_option_set.options
                ]

                # Create new option set for the duplicate question
                option_set_create = QuestionOptionSetCreateModel(
                    options=option_create_models
                )
                await self.question_option_service.create_option_set(
                    duplicate_question.id, option_set_create
                )

            # Create template variable associations for the new question
            await self._create_template_variable_associations(
                duplicate_question.id, source_question.id, template_variable_id_mapping
            )

            duplicated_questions.append(duplicate_question)

        logger.info(
            f"Duplicated {len(duplicated_questions)} questions to matrix {target_matrix_id} with template mapping"
        )
        return duplicated_questions

    def _remap_template_variable_ids_in_text(
        self, question_text: str, id_mapping: dict[int, int]
    ) -> str:
        """Remap template variable IDs in question text using the provided mapping."""

        if not id_mapping:
            return question_text

        updated_text = question_text

        # Pattern to match template variables like #{{123}}
        pattern = r"#\{\{(\d+)\}\}"

        def replace_id(match):
            old_id = int(match.group(1))
            if old_id in id_mapping:
                new_id = id_mapping[old_id]
                logger.debug(
                    f"Remapping template variable ID {old_id} -> {new_id} in question text"
                )
                return f"#{{{{{new_id}}}}}"
            else:
                logger.warning(
                    f"Template variable ID {old_id} not found in mapping - keeping original"
                )
                return match.group(0)

        updated_text = re.sub(pattern, replace_id, updated_text)

        if updated_text != question_text:
            logger.info(f"Updated question text: '{question_text}' -> '{updated_text}'")

        return updated_text

    @trace_span
    async def _create_template_variable_associations(
        self, new_question_id: int, source_question_id: int, id_mapping: dict[int, int]
    ) -> None:
        """Create template variable associations for the new question based on source question associations."""

        if not id_mapping:
            return

        template_var_service = QuestionTemplateVariableService(self.db_session)

        # Get template variable associations from source question
        source_associations = (
            await template_var_service.get_question_template_variables(
                source_question_id
            )
        )

        if not source_associations:
            logger.info(
                f"No template variable associations found for source question {source_question_id}"
            )
            return

        # Create new associations for the duplicate question
        for source_assoc in source_associations:
            old_template_var_id = source_assoc.template_variable_id

            if old_template_var_id in id_mapping:
                new_template_var_id = id_mapping[old_template_var_id]

                # Create new association
                new_assoc_data = QuestionTemplateVariableCreateModel(
                    question_id=new_question_id,
                    template_variable_id=new_template_var_id,
                    company_id=source_assoc.company_id,
                )

                await template_var_service.create_association(new_assoc_data)
                logger.info(
                    f"Created template variable association: question {new_question_id} -> template var {new_template_var_id}"
                )
            else:
                logger.warning(
                    f"Template variable ID {old_template_var_id} not found in mapping - skipping association"
                )

        logger.info(
            f"Created {len(source_associations)} template variable associations for question {new_question_id}"
        )

    @trace_span
    async def count_agentic_questions(
        self, question_ids: List[int], company_id: Optional[int] = None
    ) -> int:
        """Count how many of the given question IDs have use_agent_qa=True."""
        return await self.question_repo.count_agentic_questions(
            question_ids, company_id
        )


def get_question_service(db_session: AsyncSession) -> QuestionService:
    """Get question service instance."""
    return QuestionService(db_session)
