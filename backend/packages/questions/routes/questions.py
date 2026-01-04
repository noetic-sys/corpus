from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from packages.auth.dependencies import get_current_active_user
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from common.db.scoped import transaction
from packages.questions.models.schemas.question import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    QuestionLabelUpdate,
)
from packages.questions.models.schemas.question_with_options import (
    QuestionWithOptionsCreate,
    QuestionWithOptionsUpdate,
)
from packages.matrices.models.schemas.matrix import MatrixReprocessRequest
from packages.questions.models.schemas.question_option import (
    QuestionOptionSetCreate,
    QuestionOptionSetUpdate,
    QuestionOptionSetResponse,
    QuestionOptionCreate as QuestionOptionCreateSchema,
    QuestionOptionResponse,
)
from packages.questions.models.domain.question_option import (
    QuestionOptionSetCreateModel,
    QuestionOptionSetUpdateModel,
    QuestionOptionCreateModel,
)
from packages.questions.models.domain.question import (
    QuestionCreateModel,
    QuestionUpdateModel,
)
from packages.questions.models.domain.question_with_options import (
    QuestionWithOptionsCreateModel,
    QuestionWithOptionsUpdateModel,
)
from common.mappers.model_mapper import map_preserving_fields_set
from packages.matrices.services.reprocessing_service import get_reprocessing_service
from packages.matrices.services.batch_processing_service import (
    get_batch_processing_service,
)
from packages.questions.services.question_option_service import (
    get_question_option_service,
)
from packages.questions.services.question_service import get_question_service
from packages.documents.services.document_service import get_document_service
from packages.questions.services.template_processing_service import (
    TemplateProcessingService,
)
from packages.questions.services.question_template_variable_service import (
    QuestionTemplateVariableService,
)
from packages.matrices.models.schemas.matrix_template_variable import (
    TemplateValidationResponse,
)
from packages.matrices.services.entity_set_service import get_entity_set_service
from packages.matrices.repositories.entity_set_member_repository import (
    EntitySetMemberRepository,
)
from packages.matrices.models.domain.matrix_enums import EntityType
from common.core.otel_axiom_exporter import trace_span, get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/matrices/{matrixId}/questions/", response_model=QuestionResponse)
async def create_question(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    question: QuestionCreate,
    entity_set_id: Annotated[
        int,
        Query(
            alias="entitySetId", description="Question entity set ID to add question to"
        ),
    ],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    async with transaction():
        question_service = get_question_service()
        document_service = get_document_service()
        batch_processing_service = get_batch_processing_service()
        template_processing_service = TemplateProcessingService()
        question_template_service = QuestionTemplateVariableService()
        entity_set_service = get_entity_set_service()
        member_repo = EntitySetMemberRepository()

        # Validate template variables if question contains them
        if template_processing_service.has_template_variables(question.question_text):
            # Extract template variable IDs and validate they exist
            template_var_ids = (
                template_processing_service.extract_template_variable_ids(
                    question.question_text
                )
            )
            template_vars = (
                await template_processing_service.template_var_repo.get_by_matrix_id(
                    matrix_id
                )
            )
            existing_ids = {var.id for var in template_vars}

            missing_ids = template_var_ids - existing_ids
            if missing_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Question references undefined template variable IDs: {', '.join(map(str, missing_ids))}",
                )

        # Create question - convert schema to domain model
        question_domain = QuestionCreateModel(
            question_text=question.question_text,
            question_type_id=question.question_type_id,
            ai_model_id=question.ai_model_id,
            ai_config_override=question.ai_config_override,
            label=question.label,
            min_answers=question.min_answers,
            max_answers=question.max_answers,
            use_agent_qa=question.use_agent_qa,
            matrix_id=matrix_id,
            company_id=current_user.company_id,
        )
        logger.info(f"Raw question schema object: {question}")
        logger.info(
            f"Question data after model_copy: min_answers={question_domain.min_answers}, max_answers={question_domain.max_answers}"
        )
        db_question = await question_service.create_question(
            matrix_id, question_domain, current_user.company_id
        )

        # Validate the specified entity set exists and is a question type
        question_entity_set = await entity_set_service.get_entity_set(
            entity_set_id, current_user.company_id
        )
        if not question_entity_set:
            raise HTTPException(
                status_code=404, detail=f"Entity set {entity_set_id} not found"
            )

        if question_entity_set.entity_type != EntityType.QUESTION:
            raise HTTPException(
                status_code=400,
                detail=f"Entity set {entity_set_id} is not a question entity set (type: {question_entity_set.entity_type})",
            )

        if question_entity_set.matrix_id != matrix_id:
            raise HTTPException(
                status_code=400,
                detail=f"Entity set {entity_set_id} does not belong to matrix {matrix_id}",
            )

        # Add question to the specified question entity set
        await entity_set_service.add_members_batch(
            question_entity_set.id,
            [db_question.id],
            EntityType.QUESTION,
            current_user.company_id,
        )
        logger.info(
            f"Added question {db_question.id} to entity set {question_entity_set.id}"
        )

        # Sync template variable associations
        await question_template_service.sync_question_from_text(
            db_question.id, current_user.company_id
        )

        # Create matrix cells and QA jobs for the new question
        logger.info(
            f"Creating cells for question {db_question.id} in entity set {question_entity_set.id}"
        )
        await batch_processing_service.process_entity_added_to_set(
            matrix_id=matrix_id,
            entity_id=db_question.id,
            entity_set_id=question_entity_set.id,
            create_qa_jobs=True,  # Questions: create jobs immediately (docs already extracted)
        )

        return db_question


@router.get(
    "/questions/{questionId}",
    response_model=QuestionResponse,
    tags=["workflow-agent"],
    operation_id="get_question",
)
async def get_question(
    question_id: int = Path(alias="questionId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    question_service = get_question_service()

    question = await question_service.get_question(question_id, current_user.company_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    return question


def _needs_reprocessing(question_update: QuestionUpdate) -> bool:
    """Check if the question update requires reprocessing of cells."""
    update_data = question_update.model_dump(exclude_unset=True)

    # Fields that don't require reprocessing
    non_reprocessing_fields = {"label"}

    # Check if any field that requires reprocessing is being updated
    reprocessing_fields = set(update_data.keys()) - non_reprocessing_fields
    return len(reprocessing_fields) > 0


@router.patch("/questions/{questionId}", response_model=QuestionResponse)
async def update_question(
    question_id: Annotated[int, Path(alias="questionId")],
    question_update: QuestionUpdate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    async with transaction():
        question_service = get_question_service()
        reprocessing_service = get_reprocessing_service()
        template_processing_service = TemplateProcessingService()
        question_template_service = QuestionTemplateVariableService()

        # First, get the question to get the matrix_id
        existing_question = await question_service.get_question(
            question_id, current_user.company_id
        )
        if existing_question is None:
            raise HTTPException(status_code=404, detail="Question not found")

        # Validate template variables if question_text is being updated
        if question_update.question_text is not None:
            if template_processing_service.has_template_variables(
                question_update.question_text
            ):
                # Extract template variable IDs and validate they exist
                template_var_ids = (
                    template_processing_service.extract_template_variable_ids(
                        question_update.question_text
                    )
                )
                template_vars = await template_processing_service.template_var_repo.get_by_matrix_id(
                    existing_question.matrix_id
                )
                existing_ids = {var.id for var in template_vars}

                missing_ids = template_var_ids - existing_ids
                if missing_ids:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Question references undefined template variable IDs: {', '.join(map(str, missing_ids))}",
                    )

        # Update the question - convert schema to domain model preserving field set
        question_domain_update = map_preserving_fields_set(
            question_update, QuestionUpdateModel
        )
        print(question_domain_update.model_dump())
        question = await question_service.update_question(
            question_id, question_domain_update, current_user.company_id
        )
        if question is None:
            raise HTTPException(status_code=404, detail="Question not found")

        # Sync template variable associations if question text changed
        if question_update.question_text is not None:
            await question_template_service.sync_question_from_text(
                question_id, current_user.company_id
            )

        # Only reprocess if the update affects processing-relevant fields
        if _needs_reprocessing(question_update):
            reprocess_request = MatrixReprocessRequest(question_ids=[question_id])
            reprocessed_count = await reprocessing_service.reprocess_matrix_cells(
                existing_question.matrix_id, reprocess_request
            )
            logger.info(
                f"Updated question {question_id} and reprocessed {reprocessed_count} cells"
            )
        else:
            logger.info(
                f"Updated question {question_id} (label-only update, skipped reprocessing)"
            )

        return question


@router.patch("/questions/{questionId}/label", response_model=QuestionResponse)
async def update_question_label(
    question_id: Annotated[int, Path(alias="questionId")],
    label_update: QuestionLabelUpdate,
):
    """Update only the label of a question. This operation does not trigger reprocessing."""
    async with transaction():
        question_service = get_question_service()

        # Convert schema to domain model preserving field set
        label_domain_update = map_preserving_fields_set(
            label_update, QuestionUpdateModel
        )
        question = await question_service.update_question_label(
            question_id, label_domain_update
        )
        if question is None:
            raise HTTPException(status_code=404, detail="Question not found")

        logger.info(
            f"Updated label for question {question_id} (no reprocessing triggered)"
        )
        return question


@router.delete("/questions/{questionId}")
async def delete_question(
    question_id: int = Path(alias="questionId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    question_service = get_question_service()
    success = await question_service.delete_question(
        question_id, current_user.company_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"message": "Question deleted successfully"}


@router.get(
    "/matrices/{matrixId}/questions/",
    response_model=List[QuestionResponse],
    tags=["workflow-agent"],
    operation_id="get_questions_by_matrix",
)
@trace_span
async def get_questions_by_matrix(
    matrix_id: int = Path(alias="matrixId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Get all questions for a specific matrix."""
    question_service = get_question_service()

    questions = await question_service.get_questions_for_matrix(
        matrix_id, current_user.company_id
    )

    return questions


@router.post(
    "/matrices/{matrixId}/questions-with-options/", response_model=QuestionResponse
)
async def create_question_with_options(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    question_data: QuestionWithOptionsCreate,
    entity_set_id: Annotated[
        int,
        Query(
            alias="entitySetId", description="Question entity set ID to add question to"
        ),
    ],
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    # TODO: verify user company owns matrix
    """Create a question with options transactionally (for SINGLE_SELECT questions)."""
    async with transaction():
        question_service = get_question_service()
        document_service = get_document_service()
        batch_processing_service = get_batch_processing_service()
        template_processing_service = TemplateProcessingService()
        question_template_service = QuestionTemplateVariableService()
        entity_set_service = get_entity_set_service()
        member_repo = EntitySetMemberRepository()

        # Validate template variables if question contains them
        if template_processing_service.has_template_variables(
            question_data.question_text
        ):
            # Extract template variable IDs and validate they exist
            template_var_ids = (
                template_processing_service.extract_template_variable_ids(
                    question_data.question_text
                )
            )
            template_vars = (
                await template_processing_service.template_var_repo.get_by_matrix_id(
                    matrix_id
                )
            )
            existing_ids = {var.id for var in template_vars}

            missing_ids = template_var_ids - existing_ids
            if missing_ids:
                raise HTTPException(
                    status_code=400,
                    detail=f"Question references undefined template variable IDs: {', '.join(map(str, missing_ids))}",
                )

        # Create question with options transactionally - convert schema to domain model
        domain_options = [
            QuestionOptionCreateModel(value=opt.value) for opt in question_data.options
        ]
        question_domain = QuestionWithOptionsCreateModel(
            question_text=question_data.question_text,
            question_type_id=question_data.question_type_id,
            ai_model_id=question_data.ai_model_id,
            ai_config_override=question_data.ai_config_override,
            label=question_data.label,
            min_answers=question_data.min_answers,
            max_answers=question_data.max_answers,
            use_agent_qa=question_data.use_agent_qa,
            options=domain_options,
        )
        db_question = await question_service.create_question_with_options(
            matrix_id, question_domain, current_user.company_id
        )

        # Validate the specified entity set exists and is a question type
        question_entity_set = await entity_set_service.get_entity_set(
            entity_set_id, current_user.company_id
        )
        if not question_entity_set:
            raise HTTPException(
                status_code=404, detail=f"Entity set {entity_set_id} not found"
            )

        if question_entity_set.entity_type != EntityType.QUESTION:
            raise HTTPException(
                status_code=400,
                detail=f"Entity set {entity_set_id} is not a question entity set (type: {question_entity_set.entity_type})",
            )

        if question_entity_set.matrix_id != matrix_id:
            raise HTTPException(
                status_code=400,
                detail=f"Entity set {entity_set_id} does not belong to matrix {matrix_id}",
            )

        # Add question to the specified question entity set
        await entity_set_service.add_members_batch(
            question_entity_set.id,
            [db_question.id],
            EntityType.QUESTION,
            current_user.company_id,
        )
        logger.info(
            f"Added question {db_question.id} to entity set {question_entity_set.id}"
        )

        # Get all document IDs for this matrix through entity sets
        entity_sets_with_members = (
            await entity_set_service.get_entity_sets_with_members(
                matrix_id, current_user.company_id
            )
        )
        document_entity_set = next(
            (
                es
                for es, members in entity_sets_with_members
                if es.entity_type == EntityType.DOCUMENT
            ),
            None,
        )

        documents = []
        if document_entity_set:
            members = await member_repo.get_by_entity_set_id(
                document_entity_set.id, current_user.company_id
            )
            document_ids = [member.entity_id for member in members]
            # Get the actual document objects in bulk
            documents = await document_service.get_documents_by_ids(
                document_ids, current_user.company_id
            )
        # Sync template variable associations
        await question_template_service.sync_question_from_text(
            db_question.id, current_user.company_id
        )

        # Get all documents for this matrix
        logger.info(f"Found {len(documents)} existing documents for matrix {matrix_id}")
        logger.info(
            f"Creating cells for question {db_question.id} with documents: {[d.id for d in documents]}"
        )

        # Batch create matrix cells and QA jobs (after question and options are fully created)
        await batch_processing_service.process_entity_added_to_set(
            matrix_id=matrix_id,
            entity_id=db_question.id,
            entity_set_id=question_entity_set.id,
            create_qa_jobs=True,  # Questions: create jobs immediately (docs already extracted)
        )

        return db_question


@router.patch(
    "/matrices/{matrixId}/questions/{questionId}", response_model=QuestionResponse
)
async def update_question_with_options(
    matrix_id: Annotated[int, Path(alias="matrixId")],
    question_id: Annotated[int, Path(alias="questionId")],
    question_update: QuestionWithOptionsUpdate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Update a question with options and automatically reprocess affected cells."""
    async with transaction():
        question_service = get_question_service()
        template_processing_service = TemplateProcessingService()
        question_template_service = QuestionTemplateVariableService()

        # Validate template variables if question_text is being updated
        if (
            hasattr(question_update, "question_text")
            and question_update.question_text is not None
        ):
            if template_processing_service.has_template_variables(
                question_update.question_text
            ):
                # Extract template variable IDs and validate they exist
                template_var_ids = (
                    template_processing_service.extract_template_variable_ids(
                        question_update.question_text
                    )
                )
                template_vars = await template_processing_service.template_var_repo.get_by_matrix_id(
                    matrix_id
                )
                existing_ids = {var.id for var in template_vars}

                missing_ids = template_var_ids - existing_ids
                if missing_ids:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Question references undefined template variable IDs: {', '.join(map(str, missing_ids))}",
                    )

        # Update the question with options - convert schema to domain model preserving field set
        question_domain_update = map_preserving_fields_set(
            question_update, QuestionWithOptionsUpdateModel
        )

        updated_question = (
            await question_service.update_question_with_options_and_reprocess(
                matrix_id, question_id, question_domain_update, current_user.company_id
            )
        )

        # Sync template variable associations if question text changed
        if (
            hasattr(question_update, "question_text")
            and question_update.question_text is not None
        ):
            await question_template_service.sync_question_from_text(
                question_id, current_user.company_id
            )
            logger.info(
                f"Synced template variables for question {question_id} after update with options"
            )

        return updated_question


# Question Option Set endpoints
@router.post(
    "/questions/{questionId}/option-sets/", response_model=QuestionOptionSetResponse
)
async def create_question_option_set(
    question_id: Annotated[int, Path(alias="questionId")],
    option_set: QuestionOptionSetCreate,
):
    """Create an option set for a question."""
    # Convert schema to domain model
    domain_options = [
        QuestionOptionCreateModel(value=opt.value) for opt in option_set.options
    ]
    domain_option_set = QuestionOptionSetCreateModel(options=domain_options)

    question_option_service = get_question_option_service()
    return await question_option_service.create_option_set(
        question_id, domain_option_set
    )


@router.get(
    "/questions/{questionId}/option-sets/", response_model=QuestionOptionSetResponse
)
async def get_question_option_set(
    question_id: int = Path(alias="questionId"),
):
    """Get option set for a question."""
    question_option_service = get_question_option_service()
    option_set = await question_option_service.get_option_set_with_options(question_id)
    if option_set is None:
        raise HTTPException(status_code=404, detail="Option set not found")
    return option_set


@router.put(
    "/questions/{questionId}/option-sets/", response_model=QuestionOptionSetResponse
)
async def update_question_option_set(
    question_id: Annotated[int, Path(alias="questionId")],
    option_set_update: QuestionOptionSetUpdate,
):
    """Update option set for a question."""
    # Convert schema to domain model
    domain_options = None
    if option_set_update.options is not None:
        domain_options = [
            QuestionOptionCreateModel(value=opt.value)
            for opt in option_set_update.options
        ]
    domain_option_set_update = QuestionOptionSetUpdateModel(options=domain_options)

    question_option_service = get_question_option_service()
    option_set = await question_option_service.update_option_set(
        question_id, domain_option_set_update
    )
    if option_set is None:
        raise HTTPException(status_code=404, detail="Option set not found")
    return option_set


@router.delete("/questions/{questionId}/option-sets/")
async def delete_question_option_set(
    question_id: int = Path(alias="questionId"),
):
    """Delete option set for a question."""
    question_option_service = get_question_option_service()
    success = await question_option_service.delete_option_set(question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Option set not found")
    return {"message": "Option set deleted successfully"}


@router.post("/questions/{questionId}/options/", response_model=QuestionOptionResponse)
async def add_option_to_question(
    question_id: Annotated[int, Path(alias="questionId")],
    option: QuestionOptionCreateSchema,
):
    """Add a single option to a question's option set."""
    # Convert schema to domain model
    domain_option = QuestionOptionCreateModel(value=option.value)

    question_option_service = get_question_option_service()
    return await question_option_service.add_option_to_set(question_id, domain_option)


@router.get(
    "/questions/{questionId}/options/", response_model=List[QuestionOptionResponse]
)
async def get_question_options(
    question_id: int = Path(alias="questionId"),
):
    """Get all options for a question."""
    question_option_service = get_question_option_service()
    return await question_option_service.get_options_for_question(question_id)


@router.get(
    "/questions/{questionId}/template-validation",
    response_model=TemplateValidationResponse,
)
async def validate_question_template_variables(
    question_id: int = Path(alias="questionId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Validate template variables for a question."""
    question_template_service = QuestionTemplateVariableService()
    return await question_template_service.validate_question_template_variables(
        question_id, current_user.company_id
    )


@router.post("/questions/{questionId}/duplicate", response_model=QuestionResponse)
async def duplicate_question(
    question_id: int = Path(alias="questionId"),
    current_user: AuthenticatedUser = Depends(get_current_active_user),
):
    """Duplicate a question within the same matrix, including its options."""
    async with transaction():
        question_service = get_question_service()
        document_service = get_document_service()
        batch_processing_service = get_batch_processing_service()
        question_template_service = QuestionTemplateVariableService()
        entity_set_service = get_entity_set_service()
        member_repo = EntitySetMemberRepository()

        # Duplicate the question
        duplicated_question = await question_service.duplicate_question(
            question_id, current_user.company_id
        )

        # Add question to the question entity set immediately
        question_entity_set = await entity_set_service.get_entity_set_by_type(
            duplicated_question.matrix_id, EntityType.QUESTION, current_user.company_id
        )
        if question_entity_set:
            await entity_set_service.add_members_batch(
                question_entity_set.id,
                [duplicated_question.id],
                EntityType.QUESTION,
                current_user.company_id,
            )
            logger.info(
                f"Added duplicated question {duplicated_question.id} to entity set {question_entity_set.id}"
            )

        # Get all document IDs for this matrix through entity sets
        entity_sets_with_members = (
            await entity_set_service.get_entity_sets_with_members(
                duplicated_question.matrix_id, current_user.company_id
            )
        )
        document_entity_set = next(
            (
                es
                for es, members in entity_sets_with_members
                if es.entity_type == EntityType.DOCUMENT
            ),
            None,
        )

        documents = []
        if document_entity_set:
            members = await member_repo.get_by_entity_set_id(
                document_entity_set.id, current_user.company_id
            )
            document_ids = [member.entity_id for member in members]
            # Get the actual document objects in bulk
            documents = await document_service.get_documents_by_ids(
                document_ids, current_user.company_id
            )

        # Sync template variable associations
        await question_template_service.sync_question_from_text(
            duplicated_question.id, current_user.company_id
        )

        logger.info(
            f"Found {len(documents)} existing documents for matrix {duplicated_question.matrix_id}"
        )
        logger.info(
            f"Creating cells for duplicated question {duplicated_question.id} with documents: {[d.id for d in documents]}"
        )

        # Batch create matrix cells and QA jobs for the duplicated question
        await batch_processing_service.process_entity_added_to_set(
            matrix_id=duplicated_question.matrix_id,
            entity_id=duplicated_question.id,
            entity_set_id=question_entity_set.id,
            create_qa_jobs=True,  # Questions: create jobs immediately (docs already extracted)
        )

        return duplicated_question
