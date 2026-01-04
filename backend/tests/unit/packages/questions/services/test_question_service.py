import pytest
from packages.questions.services.question_option_service import QuestionOptionService
from unittest.mock import patch
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from packages.questions.services.question_service import QuestionService
from packages.questions.models.database.question import QuestionEntity
from packages.matrices.models.database.matrix import MatrixEntity
from packages.ai_model.models.database.ai_model import AIModelEntity
from packages.questions.models.domain.question_option import QuestionOptionCreateModel
from packages.questions.models.domain.question import (
    QuestionCreateModel,
    QuestionUpdateModel,
)
from packages.questions.models.domain.question_with_options import (
    QuestionWithOptionsCreateModel,
    QuestionWithOptionsUpdateModel,
)


class TestQuestionService:
    """Test QuestionService methods."""

    @pytest.fixture
    async def service(self, test_db: AsyncSession):
        """Create service instance."""
        return QuestionService(test_db)

    @pytest.fixture
    async def matrix_with_entity_sets(self, test_db, sample_matrix, sample_company):
        """Return sample_matrix which already has entity sets created."""
        # sample_matrix fixture now creates entity sets automatically
        return sample_matrix

    async def test_create_question_success(
        self, service, sample_matrix, sample_company
    ):
        """Test successful question creation."""
        question_data = QuestionCreateModel(
            question_text="What is the contract date?",
            question_type_id=3,  # DATE
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        result = await service.create_question(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "What is the contract date?"
        assert result.question_type_id == 3

    async def test_create_question_matrix_not_found(self, service, sample_company):
        """Test creating question for non-existent matrix."""
        question_data = QuestionCreateModel(
            question_text="Test question",
            question_type_id=1,
            matrix_id=999,
            company_id=sample_company.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_question(999, question_data, sample_company.id)

        assert exc_info.value.status_code == 404
        assert "Matrix not found" in str(exc_info.value.detail)

    async def test_get_question_exists(self, service, sample_question):
        """Test getting existing question."""
        result = await service.get_question(sample_question.id)

        assert result is not None
        assert result.id == sample_question.id
        assert result.question_text == sample_question.question_text
        assert result.matrix_id == sample_question.matrix_id

    async def test_get_question_not_exists(self, service):
        """Test getting non-existent question."""
        result = await service.get_question(999)
        assert result is None

    async def test_update_question_success(self, service, sample_question):
        """Test successful question update."""
        update_data = QuestionUpdateModel(question_text="Updated question text")

        result = await service.update_question(sample_question.id, update_data)

        assert result is not None
        assert result.question_text == "Updated question text"
        assert result.question_type_id == sample_question.question_type_id  # Unchanged

    async def test_update_question_partial(self, service, sample_question):
        """Test partial question update."""
        update_data = QuestionUpdateModel(question_text="Only text updated")

        result = await service.update_question(sample_question.id, update_data)

        assert result is not None
        assert result.question_text == "Only text updated"
        assert result.question_type_id == sample_question.question_type_id  # Unchanged

    async def test_update_question_not_found(self, service):
        """Test updating non-existent question."""
        update_data = QuestionUpdateModel(question_text="Updated")

        result = await service.update_question(999, update_data)
        assert result is None

    async def test_delete_question_success(self, service, sample_question):
        """Test successful question deletion."""
        success = await service.delete_question(sample_question.id)
        assert success is True

        # Verify deletion
        result = await service.get_question(sample_question.id)
        assert result is None

    async def test_delete_question_not_found(self, service):
        """Test deleting non-existent question."""
        success = await service.delete_question(999)
        assert success is False

    async def test_get_questions_for_matrix(
        self, service, sample_matrix, sample_company
    ):
        """Test getting all questions for a matrix."""
        # Create multiple questions
        questions_data = [
            {
                "matrix_id": sample_matrix.id,
                "question_text": "Question 1",
                "question_type_id": 1,
                "company_id": sample_company.id,
            },
            {
                "matrix_id": sample_matrix.id,
                "question_text": "Question 2",
                "question_type_id": 2,
                "company_id": sample_company.id,
            },
            {
                "matrix_id": sample_matrix.id,
                "question_text": "Question 3",
                "question_type_id": 3,
                "company_id": sample_company.id,
            },
        ]

        for data in questions_data:
            question = QuestionEntity(**data)
            service.db_session.add(question)

        await service.db_session.commit()

        # Get questions for matrix
        results = await service.get_questions_for_matrix(sample_matrix.id)

        assert len(results) >= 3  # At least our created questions
        question_texts = [q.question_text for q in results]
        assert "Question 1" in question_texts
        assert "Question 2" in question_texts
        assert "Question 3" in question_texts

    async def test_get_questions_for_matrix_empty(
        self, service, sample_matrix, sample_company
    ):
        """Test getting questions for matrix with no questions."""
        results = await service.get_questions_for_matrix(
            sample_matrix.id, sample_company.id
        )
        assert len(results) == 0

    async def test_create_question_with_options_success(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with options successfully."""
        options = [
            QuestionOptionCreateModel(value="Option 1"),
            QuestionOptionCreateModel(value="Option 2"),
            QuestionOptionCreateModel(value="Option 3"),
        ]

        question_data = QuestionWithOptionsCreateModel(
            question_text="Select an option",
            question_type_id=5,  # SINGLE_SELECT
            options=options,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        result = await service.create_question_with_options(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "Select an option"
        assert result.question_type_id == 5

        # Verify options were created by checking through option service

        option_service = QuestionOptionService()
        created_options = await option_service.get_options_for_question(result.id)

        assert len(created_options) == 3
        assert created_options[0].value == "Option 1"
        assert created_options[1].value == "Option 2"
        assert created_options[2].value == "Option 3"

    async def test_create_question_with_options_no_options(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question without options (using default empty list)."""
        question_data = QuestionWithOptionsCreateModel(
            question_text="Question without options",
            question_type_id=1,  # SHORT_ANSWER
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            # options will default to []
        )

        result = await service.create_question_with_options(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "Question without options"
        assert result.question_type_id == 1

        # Verify no options were created

        option_service = QuestionOptionService()
        created_options = await option_service.get_options_for_question(result.id)
        assert len(created_options) == 0

    async def test_create_question_with_options_matrix_not_found(
        self, service, sample_company
    ):
        """Test creating question with options for non-existent matrix."""
        question_data = QuestionWithOptionsCreateModel(
            question_text="Test question",
            question_type_id=5,
            options=[QuestionOptionCreateModel(value="Option 1")],
            matrix_id=999,
            company_id=sample_company.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_question_with_options(
                999, question_data, sample_company.id
            )

        assert exc_info.value.status_code == 404
        assert "Matrix not found" in str(exc_info.value.detail)

    async def test_create_question_with_options_rollback_on_failure(
        self, service, sample_matrix, sample_company
    ):
        """Test that question creation is rolled back if option creation fails."""
        options = [
            QuestionOptionCreateModel(value="Option 1"),
        ]

        question_data = QuestionWithOptionsCreateModel(
            question_text="Question that will fail",
            question_type_id=5,
            options=options,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        # Mock option set creation to fail
        with patch.object(
            service.option_set_repo,
            "create_for_question",
            side_effect=Exception("Option creation failed"),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.create_question_with_options(
                    sample_matrix.id, question_data, sample_company.id
                )

            assert exc_info.value.status_code == 500
            assert "Failed to create question with options" in str(
                exc_info.value.detail
            )

    async def test_service_initialization(self, test_db):
        """Test service properly initializes all repositories."""
        service = QuestionService(test_db)

        assert service.db_session == test_db
        assert service.question_repo is not None
        assert service.matrix_repo is not None
        assert service.option_set_repo is not None
        assert service.option_repo is not None

    async def test_create_question_with_minimal_data(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with minimal required data."""
        question_data = QuestionCreateModel(
            question_text="Minimal question",
            question_type_id=1,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        result = await service.create_question(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "Minimal question"
        assert result.question_type_id == 1

    async def test_create_question_with_options_different_types(
        self, service, sample_matrix, sample_company
    ):
        """Test creating questions with options for different question types."""
        # Create SINGLE_SELECT question with options
        select_options = [
            QuestionOptionCreateModel(value="Yes"),
            QuestionOptionCreateModel(value="No"),
        ]

        select_question_data = QuestionWithOptionsCreateModel(
            question_text="Do you agree?",
            question_type_id=5,  # SINGLE_SELECT
            options=select_options,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        select_result = await service.create_question_with_options(
            sample_matrix.id, select_question_data, sample_company.id
        )
        assert select_result.question_type_id == 5

        # Create non-select question without options
        text_question_data = QuestionWithOptionsCreateModel(
            question_text="What is your name?",
            question_type_id=1,  # SHORT_ANSWER
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            # options will default to []
        )

        text_result = await service.create_question_with_options(
            sample_matrix.id, text_question_data, sample_company.id
        )
        assert text_result.question_type_id == 1

    async def test_get_questions_for_matrix_different_types(
        self, service, sample_matrix, sample_company
    ):
        """Test getting questions of different types for a matrix."""
        # Create questions of different types
        question_types = [1, 2, 3, 4, 5]  # All question types

        for i, question_type in enumerate(question_types):
            question = QuestionEntity(
                matrix_id=sample_matrix.id,
                question_text=f"Question type {question_type}",
                question_type_id=question_type,
                company_id=sample_company.id,
            )
            service.db_session.add(question)

        await service.db_session.commit()

        # Get all questions
        results = await service.get_questions_for_matrix(sample_matrix.id)

        assert len(results) == 5
        result_types = [q.question_type_id for q in results]
        for question_type in question_types:
            assert question_type in result_types

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_and_reprocess_success(
        self,
        mock_get_message_queue,
        mock_tracer,
        service,
        matrix_with_entity_sets,
        sample_question,
        sample_company,
    ):
        """Test successful comprehensive question update with reprocessing."""
        # Setup mocks
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        update_data = QuestionWithOptionsUpdateModel(
            question_text="Updated comprehensive question",
            question_type_id=5,  # SINGLE_SELECT
            options=[
                QuestionOptionCreateModel(value="Option A"),
                QuestionOptionCreateModel(value="Option B"),
            ],
        )

        result = await service.update_question_with_options_and_reprocess(
            matrix_with_entity_sets.id,
            sample_question.id,
            update_data,
            sample_company.id,
        )

        assert result is not None
        assert result.question_text == "Updated comprehensive question"
        assert result.question_type_id == 5

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_and_reprocess_question_not_found(
        self,
        mock_get_message_queue,
        mock_tracer,
        service,
        sample_matrix,
        sample_company,
    ):
        """Test update with non-existent question."""
        # Setup mocks
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        update_data = QuestionWithOptionsUpdateModel(question_text="Updated text")

        with pytest.raises(HTTPException) as exc_info:
            await service.update_question_with_options_and_reprocess(
                sample_matrix.id, 999, update_data, sample_company.id
            )

        assert exc_info.value.status_code == 404
        assert "Question not found" in str(exc_info.value.detail)

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_and_reprocess_wrong_matrix(
        self,
        mock_get_message_queue,
        mock_tracer,
        service,
        sample_matrix,
        sample_question,
        sample_workspace,
        sample_company,
    ):
        """Test update with question from different matrix."""
        # Setup mocks
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create another matrix
        other_matrix = MatrixEntity(
            name="Other Matrix",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        service.db_session.add(other_matrix)
        await service.db_session.commit()
        await service.db_session.refresh(other_matrix)

        update_data = QuestionWithOptionsUpdateModel(question_text="Updated text")

        with pytest.raises(HTTPException) as exc_info:
            await service.update_question_with_options_and_reprocess(
                other_matrix.id, sample_question.id, update_data, sample_company.id
            )

        assert exc_info.value.status_code == 400
        assert "Question does not belong to this matrix" in str(exc_info.value.detail)

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_and_reprocess_partial_update(
        self,
        mock_get_message_queue,
        mock_tracer,
        service,
        matrix_with_entity_sets,
        sample_question,
        sample_company,
    ):
        """Test partial update (only question text)."""
        # Setup mocks
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        update_data = QuestionWithOptionsUpdateModel(question_text="Only text updated")

        result = await service.update_question_with_options_and_reprocess(
            matrix_with_entity_sets.id,
            sample_question.id,
            update_data,
            sample_company.id,
        )

        assert result is not None
        assert result.question_text == "Only text updated"
        # Other fields should remain unchanged
        assert result.question_type_id == sample_question.question_type_id

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_and_reprocess_options_only(
        self,
        mock_get_message_queue,
        mock_tracer,
        service,
        matrix_with_entity_sets,
        sample_company,
    ):
        """Test updating only options (no question fields)."""
        # Setup mocks
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create a SINGLE_SELECT question
        select_question = QuestionEntity(
            matrix_id=matrix_with_entity_sets.id,
            question_text="Select question",
            question_type_id=5,  # SINGLE_SELECT
            company_id=sample_company.id,
        )
        service.db_session.add(select_question)
        await service.db_session.commit()
        await service.db_session.refresh(select_question)

        update_data = QuestionWithOptionsUpdateModel(
            options=[
                QuestionOptionCreateModel(value="New Option 1"),
                QuestionOptionCreateModel(value="New Option 2"),
            ]
        )

        result = await service.update_question_with_options_and_reprocess(
            matrix_with_entity_sets.id,
            select_question.id,
            update_data,
            sample_company.id,
        )

        assert result is not None
        assert result.question_text == "Select question"  # Unchanged
        assert result.question_type_id == 5  # Unchanged

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_and_reprocess_clear_options(
        self,
        mock_get_message_queue,
        mock_tracer,
        service,
        matrix_with_entity_sets,
        sample_company,
    ):
        """Test clearing options (empty array)."""
        # Setup mocks
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create a SINGLE_SELECT question
        select_question = QuestionEntity(
            matrix_id=matrix_with_entity_sets.id,
            question_text="Select question",
            question_type_id=5,  # SINGLE_SELECT
            company_id=sample_company.id,
        )
        service.db_session.add(select_question)
        await service.db_session.commit()
        await service.db_session.refresh(select_question)

        update_data = QuestionWithOptionsUpdateModel(options=[])  # Clear options

        result = await service.update_question_with_options_and_reprocess(
            matrix_with_entity_sets.id,
            select_question.id,
            update_data,
            sample_company.id,
        )

        assert result is not None
        assert result.question_text == "Select question"

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_update_question_label_success(
        self, mock_tracer, service, sample_question
    ):
        """Test successful question label update."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        label_update = QuestionUpdateModel(label="Test Label")
        result = await service.update_question_label(sample_question.id, label_update)

        assert result is not None
        assert result.label == "Test Label"
        assert result.id == sample_question.id
        assert result.question_text == sample_question.question_text  # Unchanged

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_update_question_label_none(
        self, mock_tracer, service, test_db, sample_matrix, sample_company
    ):
        """Test setting question label to None."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create question with initial label
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Test question",
            question_type_id=1,
            label="Initial Label",
            company_id=sample_company.id,
        )
        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(question)

        # Update label to None
        label_update = QuestionUpdateModel(label=None)
        result = await service.update_question_label(question.id, label_update)

        assert result is not None
        assert result.label is None
        assert result.id == question.id

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_update_question_label_not_found(self, mock_tracer, service):
        """Test updating label for non-existent question."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        label_update = QuestionUpdateModel(label="Test Label")
        result = await service.update_question_label(999, label_update)

        assert result is None

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_question_success(
        self, mock_tracer, service, sample_question
    ):
        """Test successful question duplication without options."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        result = await service.duplicate_question(sample_question.id)

        assert result is not None
        assert result.id != sample_question.id  # Different ID
        assert result.question_text == sample_question.question_text
        assert result.question_type_id == sample_question.question_type_id
        assert result.matrix_id == sample_question.matrix_id
        expected_label = (
            f"{sample_question.label} (Copy)" if sample_question.label else None
        )
        assert result.label == expected_label

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_question_with_options(
        self, mock_tracer, service, sample_matrix, sample_company
    ):
        """Test duplicating question with options."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create a question with options
        options = [
            QuestionOptionCreateModel(value="Option 1"),
            QuestionOptionCreateModel(value="Option 2"),
        ]

        question_data = QuestionWithOptionsCreateModel(
            question_text="Select question",
            question_type_id=5,  # SINGLE_SELECT
            label="Original Question",
            options=options,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        original_question = await service.create_question_with_options(
            sample_matrix.id, question_data, sample_company.id
        )

        # Duplicate the question
        result = await service.duplicate_question(original_question.id)

        assert result is not None
        assert result.id != original_question.id
        assert result.question_text == original_question.question_text
        assert result.question_type_id == original_question.question_type_id
        assert result.matrix_id == original_question.matrix_id
        assert result.label == "Original Question (Copy)"

        # Verify options were duplicated

        option_service = QuestionOptionService()

        original_options = await option_service.get_options_for_question(
            original_question.id
        )
        duplicated_options = await option_service.get_options_for_question(result.id)

        assert len(duplicated_options) == len(original_options)
        assert duplicated_options[0].value == "Option 1"
        assert duplicated_options[1].value == "Option 2"

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_question_with_label_none(
        self, mock_tracer, service, sample_matrix, sample_company
    ):
        """Test duplicating question with no label."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create question without label
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Question without label",
            question_type_id=1,
            company_id=sample_company.id,
            label=None,
        )
        service.db_session.add(question)
        await service.db_session.commit()
        await service.db_session.refresh(question)

        result = await service.duplicate_question(question.id)

        assert result is not None
        assert result.label is None

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_question_not_found(self, mock_tracer, service):
        """Test duplicating non-existent question."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        with pytest.raises(HTTPException) as exc_info:
            await service.duplicate_question(999)

        assert exc_info.value.status_code == 404
        assert "Question not found" in str(exc_info.value.detail)

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_questions_to_matrix_success(
        self, mock_tracer, service, test_db, sample_workspace, sample_company
    ):
        """Test successfully duplicating questions from one matrix to another."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create workspace
        workspace = sample_workspace

        # Create source and target matrices
        source_matrix = MatrixEntity(
            name="Source Matrix",
            description="Source",
            workspace_id=workspace.id,
            company_id=sample_company.id,
        )
        target_matrix = MatrixEntity(
            name="Target Matrix",
            description="Target",
            workspace_id=workspace.id,
            company_id=sample_company.id,
        )
        test_db.add_all([source_matrix, target_matrix])
        await test_db.commit()
        await test_db.refresh(source_matrix)
        await test_db.refresh(target_matrix)

        # Create questions in source matrix
        question1 = QuestionEntity(
            matrix_id=source_matrix.id,
            question_text="What is the date?",
            question_type_id=1,
            label="Date Question",
            company_id=sample_company.id,
        )
        question2 = QuestionEntity(
            matrix_id=source_matrix.id,
            question_text="What is the amount?",
            question_type_id=2,
            label="Amount Question",
            company_id=sample_company.id,
        )
        test_db.add_all([question1, question2])
        await test_db.commit()
        await test_db.refresh(question1)
        await test_db.refresh(question2)

        # Duplicate questions to target matrix
        duplicated_questions = await service.duplicate_questions_to_matrix(
            source_matrix.id, target_matrix.id
        )

        assert len(duplicated_questions) == 2

        # Verify all questions are for target matrix
        for question in duplicated_questions:
            assert question.matrix_id == target_matrix.id

        # Verify question properties are preserved
        question_texts = [q.question_text for q in duplicated_questions]
        labels = [q.label for q in duplicated_questions]

        assert "What is the date?" in question_texts
        assert "What is the amount?" in question_texts
        assert "Date Question" in labels
        assert "Amount Question" in labels

        # Verify question was duplicated correctly
        amount_question = next(
            q for q in duplicated_questions if q.question_text == "What is the amount?"
        )

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_questions_to_matrix_with_options(
        self, mock_tracer, service, test_db, sample_workspace, sample_company
    ):
        """Test duplicating questions with options."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create workspace
        workspace = sample_workspace

        # Create source and target matrices
        source_matrix = MatrixEntity(
            name="Source Matrix",
            description="Source",
            workspace_id=workspace.id,
            company_id=sample_company.id,
        )
        target_matrix = MatrixEntity(
            name="Target Matrix",
            description="Target",
            workspace_id=workspace.id,
            company_id=sample_company.id,
        )
        test_db.add_all([source_matrix, target_matrix])
        await test_db.commit()
        await test_db.refresh(source_matrix)
        await test_db.refresh(target_matrix)

        # Create question with options in source matrix

        options = [
            QuestionOptionCreateModel(value="Yes"),
            QuestionOptionCreateModel(value="No"),
        ]

        question_data = QuestionWithOptionsCreateModel(
            question_text="Do you agree?",
            question_type_id=5,  # SINGLE_SELECT
            label="Agreement Question",
            options=options,
            matrix_id=source_matrix.id,
            company_id=sample_company.id,
        )

        original_question = await service.create_question_with_options(
            source_matrix.id, question_data, sample_company.id
        )

        # Duplicate questions to target matrix
        duplicated_questions = await service.duplicate_questions_to_matrix(
            source_matrix.id, target_matrix.id
        )

        assert len(duplicated_questions) == 1
        duplicated_question = duplicated_questions[0]

        assert duplicated_question.matrix_id == target_matrix.id
        assert duplicated_question.question_text == "Do you agree?"
        assert duplicated_question.label == "Agreement Question"

        # Verify options were duplicated

        option_service = QuestionOptionService()

        original_options = await option_service.get_options_for_question(
            original_question.id
        )
        duplicated_options = await option_service.get_options_for_question(
            duplicated_question.id
        )

        assert len(duplicated_options) == len(original_options)
        duplicated_values = [opt.value for opt in duplicated_options]
        assert "Yes" in duplicated_values
        assert "No" in duplicated_values

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_questions_to_matrix_empty_source(
        self, mock_tracer, service, test_db, sample_workspace, sample_company
    ):
        """Test duplicating questions from empty matrix."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create workspace
        workspace = sample_workspace

        # Create source and target matrices
        source_matrix = MatrixEntity(
            name="Empty Source",
            description="No questions",
            workspace_id=workspace.id,
            company_id=sample_company.id,
        )
        target_matrix = MatrixEntity(
            name="Target Matrix",
            description="Target",
            workspace_id=workspace.id,
            company_id=sample_company.id,
        )
        test_db.add_all([source_matrix, target_matrix])
        await test_db.commit()
        await test_db.refresh(source_matrix)
        await test_db.refresh(target_matrix)

        # Duplicate from empty source
        duplicated_questions = await service.duplicate_questions_to_matrix(
            source_matrix.id, target_matrix.id
        )

        assert len(duplicated_questions) == 0

        # Verify target matrix is still empty
        target_questions = await service.get_questions_for_matrix(target_matrix.id)
        assert len(target_questions) == 0

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_questions_to_matrix_with_null_labels(
        self, mock_tracer, service, test_db, sample_workspace, sample_company
    ):
        """Test duplicating questions that have null labels."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create workspace
        workspace = sample_workspace

        # Create source and target matrices
        source_matrix = MatrixEntity(
            name="Source Matrix",
            description="Source",
            workspace_id=workspace.id,
            company_id=sample_company.id,
        )
        target_matrix = MatrixEntity(
            name="Target Matrix",
            description="Target",
            workspace_id=workspace.id,
            company_id=sample_company.id,
        )
        test_db.add_all([source_matrix, target_matrix])
        await test_db.commit()
        await test_db.refresh(source_matrix)
        await test_db.refresh(target_matrix)

        # Create question without label in source matrix
        question = QuestionEntity(
            matrix_id=source_matrix.id,
            question_text="Question without label",
            question_type_id=1,
            label=None,
            company_id=sample_company.id,
        )
        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(question)

        # Duplicate questions to target matrix
        duplicated_questions = await service.duplicate_questions_to_matrix(
            source_matrix.id, target_matrix.id
        )

        assert len(duplicated_questions) == 1
        assert duplicated_questions[0].matrix_id == target_matrix.id
        assert duplicated_questions[0].question_text == "Question without label"
        assert duplicated_questions[0].label is None

    # AI Model Validation Tests
    async def test_create_question_with_valid_ai_model(
        self, service, sample_matrix, sample_ai_model, sample_company
    ):
        """Test creating question with valid AI model."""
        question_data = QuestionCreateModel(
            question_text="Question with AI model",
            question_type_id=1,
            ai_model_id=sample_ai_model.id,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        result = await service.create_question(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "Question with AI model"
        assert result.ai_model_id == sample_ai_model.id

    async def test_create_question_with_nonexistent_ai_model(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with non-existent AI model."""
        question_data = QuestionCreateModel(
            question_text="Question with invalid AI model",
            question_type_id=1,
            ai_model_id=999,  # Non-existent model
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_question(
                sample_matrix.id, question_data, sample_company.id
            )

        assert exc_info.value.status_code == 400
        assert "AI model with ID 999 not found" in str(exc_info.value.detail)

    async def test_create_question_with_disabled_ai_model(
        self, service, sample_matrix, disabled_ai_model, sample_company
    ):
        """Test creating question with disabled AI model."""
        question_data = QuestionCreateModel(
            question_text="Question with disabled AI model",
            question_type_id=1,
            ai_model_id=disabled_ai_model.id,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_question(
                sample_matrix.id, question_data, sample_company.id
            )

        assert exc_info.value.status_code == 400
        assert f"AI model '{disabled_ai_model.display_name}' is not enabled" in str(
            exc_info.value.detail
        )

    async def test_create_question_with_disabled_ai_provider(
        self, service, sample_matrix, test_db, disabled_ai_provider, sample_company
    ):
        """Test creating question with AI model from disabled provider."""
        # Create enabled model under disabled provider
        model = AIModelEntity(
            provider_id=disabled_ai_provider.id,
            model_name="model-disabled-provider",
            display_name="Model with Disabled Provider",
            enabled=True,
        )
        test_db.add(model)
        await test_db.commit()
        await test_db.refresh(model)

        question_data = QuestionCreateModel(
            question_text="Question with model from disabled provider",
            question_type_id=1,
            ai_model_id=model.id,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_question(
                sample_matrix.id, question_data, sample_company.id
            )

        assert exc_info.value.status_code == 400
        assert (
            f"AI provider '{disabled_ai_provider.display_name}' is not enabled"
            in str(exc_info.value.detail)
        )

    async def test_create_question_without_ai_model(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question without AI model (should use default)."""
        question_data = QuestionCreateModel(
            question_text="Question without AI model",
            question_type_id=1,
            ai_model_id=None,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        result = await service.create_question(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "Question without AI model"
        assert result.ai_model_id is None

    async def test_update_question_with_valid_ai_model(
        self, service, sample_question, sample_ai_model
    ):
        """Test updating question with valid AI model."""
        update_data = QuestionUpdateModel(ai_model_id=sample_ai_model.id)

        result = await service.update_question(sample_question.id, update_data)

        assert result is not None
        assert result.ai_model_id == sample_ai_model.id
        assert result.question_text == sample_question.question_text  # Unchanged

    async def test_update_question_with_nonexistent_ai_model(
        self, service, sample_question
    ):
        """Test updating question with non-existent AI model."""
        update_data = QuestionUpdateModel(ai_model_id=999)  # Non-existent model

        with pytest.raises(HTTPException) as exc_info:
            await service.update_question(sample_question.id, update_data)

        assert exc_info.value.status_code == 400
        assert "AI model with ID 999 not found" in str(exc_info.value.detail)

    async def test_update_question_with_disabled_ai_model(
        self, service, sample_question, disabled_ai_model
    ):
        """Test updating question with disabled AI model."""
        update_data = QuestionUpdateModel(ai_model_id=disabled_ai_model.id)

        with pytest.raises(HTTPException) as exc_info:
            await service.update_question(sample_question.id, update_data)

        assert exc_info.value.status_code == 400
        assert f"AI model '{disabled_ai_model.display_name}' is not enabled" in str(
            exc_info.value.detail
        )

    async def test_update_question_clear_ai_model(
        self, service, test_db, sample_matrix, sample_ai_model, sample_company
    ):
        """Test clearing AI model from question."""
        # Create question with AI model
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Question with AI model",
            question_type_id=1,
            ai_model_id=sample_ai_model.id,
            company_id=sample_company.id,
        )
        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(question)

        # Clear the AI model
        update_data = QuestionUpdateModel(ai_model_id=None)
        result = await service.update_question(question.id, update_data)

        assert result is not None
        assert result.ai_model_id is None

    async def test_create_question_with_options_and_ai_model(
        self, service, sample_matrix, sample_ai_model, sample_company
    ):
        """Test creating question with options and AI model."""
        options = [
            QuestionOptionCreateModel(value="Option 1"),
            QuestionOptionCreateModel(value="Option 2"),
        ]

        question_data = QuestionWithOptionsCreateModel(
            question_text="Select question with AI model",
            question_type_id=5,  # SINGLE_SELECT
            ai_model_id=sample_ai_model.id,
            options=options,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        result = await service.create_question_with_options(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "Select question with AI model"
        assert result.ai_model_id == sample_ai_model.id
        assert result.question_type_id == 5

    async def test_create_question_with_options_invalid_ai_model(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with options and invalid AI model."""
        options = [
            QuestionOptionCreateModel(value="Option 1"),
            QuestionOptionCreateModel(value="Option 2"),
        ]

        question_data = QuestionWithOptionsCreateModel(
            question_text="Select question with invalid AI model",
            question_type_id=5,  # SINGLE_SELECT
            ai_model_id=999,  # Non-existent model
            options=options,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_question_with_options(
                sample_matrix.id, question_data, sample_company.id
            )

        assert exc_info.value.status_code == 400
        assert "AI model with ID 999 not found" in str(exc_info.value.detail)

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_and_ai_model(
        self,
        mock_get_message_queue,
        mock_tracer,
        service,
        matrix_with_entity_sets,
        sample_question,
        sample_ai_model,
        sample_company,
    ):
        """Test updating question with options and AI model."""
        # Setup mocks
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        update_data = QuestionWithOptionsUpdateModel(
            question_text="Updated question with AI model",
            ai_model_id=sample_ai_model.id,
            options=[
                QuestionOptionCreateModel(value="New Option 1"),
                QuestionOptionCreateModel(value="New Option 2"),
            ],
        )

        result = await service.update_question_with_options_and_reprocess(
            matrix_with_entity_sets.id,
            sample_question.id,
            update_data,
            sample_company.id,
        )

        assert result is not None
        assert result.question_text == "Updated question with AI model"
        assert result.ai_model_id == sample_ai_model.id

    # Answer Count Configuration Tests
    async def test_create_question_with_custom_answer_counts(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with custom min/max answer counts."""
        question_data = QuestionCreateModel(
            question_text="Question with custom answer counts",
            question_type_id=1,
            min_answers=3,
            max_answers=5,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        result = await service.create_question(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "Question with custom answer counts"
        assert result.min_answers == 3
        assert result.max_answers == 5

    async def test_create_question_with_unlimited_max_answers(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with unlimited max answers (null)."""
        question_data = QuestionCreateModel(
            question_text="Question with unlimited answers",
            question_type_id=1,
            min_answers=2,
            max_answers=None,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        result = await service.create_question(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "Question with unlimited answers"
        assert result.min_answers == 2
        assert result.max_answers is None

    async def test_create_question_with_default_answer_counts(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with default answer counts."""
        question_data = QuestionCreateModel(
            question_text="Question with default counts",
            question_type_id=1,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            # min_answers and max_answers will use defaults
        )

        result = await service.create_question(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.min_answers == 1  # Default
        assert result.max_answers == 1

    async def test_create_question_invalid_min_answers(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with invalid min_answers (< 1)."""
        question_data = QuestionCreateModel(
            question_text="Invalid min answers",
            question_type_id=1,
            min_answers=0,  # Invalid
            max_answers=2,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_question(
                sample_matrix.id, question_data, sample_company.id
            )

        assert exc_info.value.status_code == 400
        assert "min_answers must be at least 1" in str(exc_info.value.detail)

    async def test_create_question_invalid_max_less_than_min(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with max_answers < min_answers."""
        question_data = QuestionCreateModel(
            question_text="Invalid max answers",
            question_type_id=1,
            min_answers=5,
            max_answers=3,  # Less than min_answers
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await service.create_question(
                sample_matrix.id, question_data, sample_company.id
            )

        assert exc_info.value.status_code == 400
        assert (
            "max_answers (3) must be greater than or equal to min_answers (5)"
            in str(exc_info.value.detail)
        )

    async def test_update_question_change_answer_counts(self, service, sample_question):
        """Test updating question to change answer counts."""
        update_data = QuestionUpdateModel(min_answers=2, max_answers=4)

        result = await service.update_question(sample_question.id, update_data)

        assert result is not None
        assert result.min_answers == 2
        assert result.max_answers == 4
        assert result.question_text == sample_question.question_text  # Unchanged

    async def test_update_question_set_max_answers_to_null(
        self, service, test_db, sample_matrix, sample_company
    ):
        """Test updating question to set max_answers to null (unlimited)."""
        # Create question with limited max answers
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Question with limited answers",
            question_type_id=1,
            min_answers=2,
            max_answers=5,
            company_id=sample_company.id,
        )
        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(question)

        # Update to unlimited
        update_data = QuestionUpdateModel(max_answers=None)
        result = await service.update_question(question.id, update_data)

        assert result is not None
        assert result.min_answers == 2  # Unchanged
        assert result.max_answers is None  # Now unlimited

    async def test_update_question_partial_answer_count_update(
        self, service, test_db, sample_matrix, sample_company
    ):
        """Test updating only min_answers or only max_answers."""
        # Create question with specific counts
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Question to update partially",
            question_type_id=1,
            min_answers=1,
            max_answers=3,
            company_id=sample_company.id,
        )
        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(question)

        # Update only min_answers
        update_data = QuestionUpdateModel(min_answers=2)
        result = await service.update_question(question.id, update_data)

        assert result is not None
        assert result.min_answers == 2  # Updated
        assert result.max_answers == 3  # Unchanged

        # Update only max_answers
        update_data = QuestionUpdateModel(max_answers=5)
        result = await service.update_question(question.id, update_data)

        assert result is not None
        assert result.min_answers == 2  # Unchanged from previous update
        assert result.max_answers == 5  # Updated

    async def test_update_question_invalid_answer_count_validation(
        self, service, sample_question
    ):
        """Test that updating question validates answer count constraints."""
        # Try to set min_answers to 0
        update_data = QuestionUpdateModel(min_answers=0)

        with pytest.raises(HTTPException) as exc_info:
            await service.update_question(sample_question.id, update_data)

        assert exc_info.value.status_code == 400
        assert "min_answers must be at least 1" in str(exc_info.value.detail)

        # Try to set max_answers less than existing min_answers
        # First set min_answers to 3
        await service.update_question(
            sample_question.id, QuestionUpdateModel(min_answers=3)
        )

        # Then try to set max_answers to 2 (less than current min_answers)
        update_data = QuestionUpdateModel(max_answers=2)

        with pytest.raises(HTTPException) as exc_info:
            await service.update_question(sample_question.id, update_data)

        assert exc_info.value.status_code == 400
        assert (
            "max_answers (2) must be greater than or equal to min_answers (3)"
            in str(exc_info.value.detail)
        )

    async def test_create_question_with_options_custom_answer_counts(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with options and custom answer counts."""
        options = [
            QuestionOptionCreateModel(value="Option 1"),
            QuestionOptionCreateModel(value="Option 2"),
            QuestionOptionCreateModel(value="Option 3"),
        ]

        question_data = QuestionWithOptionsCreateModel(
            question_text="Select question with custom counts",
            question_type_id=5,  # SINGLE_SELECT
            min_answers=2,
            max_answers=3,
            options=options,
        )

        result = await service.create_question_with_options(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "Select question with custom counts"
        assert result.min_answers == 2
        assert result.max_answers == 3
        assert result.question_type_id == 5

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_answer_counts(
        self,
        mock_get_message_queue,
        mock_tracer,
        service,
        matrix_with_entity_sets,
        sample_question,
        sample_company,
    ):
        """Test updating question with options including answer counts."""
        # Setup mocks
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        update_data = QuestionWithOptionsUpdateModel(
            question_text="Updated question with answer counts",
            min_answers=2,
            max_answers=4,
            options=[
                QuestionOptionCreateModel(value="Updated Option A"),
                QuestionOptionCreateModel(value="Updated Option B"),
            ],
        )

        result = await service.update_question_with_options_and_reprocess(
            matrix_with_entity_sets.id,
            sample_question.id,
            update_data,
            sample_company.id,
        )

        assert result is not None
        assert result.question_text == "Updated question with answer counts"
        assert result.min_answers == 2
        assert result.max_answers == 4

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_set_max_answers_null(
        self,
        mock_get_message_queue,
        mock_tracer,
        service,
        matrix_with_entity_sets,
        sample_company,
        test_db,
    ):
        """Test updating question with options to set max_answers to null."""
        # Setup mocks
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create question with limited max answers
        question = QuestionEntity(
            matrix_id=matrix_with_entity_sets.id,
            question_text="Question with limited max",
            question_type_id=1,
            min_answers=1,
            max_answers=3,
            company_id=sample_company.id,
        )
        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(question)

        # Update to set max_answers to None (unlimited)
        update_data = QuestionWithOptionsUpdateModel(max_answers=None)

        result = await service.update_question_with_options_and_reprocess(
            matrix_with_entity_sets.id, question.id, update_data, sample_company.id
        )

        assert result is not None
        assert result.min_answers == 1  # Unchanged
        assert result.max_answers is None  # Now unlimited

    async def test_duplicate_question_preserves_answer_counts(
        self, service, test_db, sample_matrix, sample_company
    ):
        """Test that duplicating question preserves answer count settings."""
        # Create question with custom answer counts
        original_question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Question to duplicate",
            question_type_id=1,
            min_answers=2,
            max_answers=5,
            label="Original",
            company_id=sample_company.id,
        )
        test_db.add(original_question)
        await test_db.commit()
        await test_db.refresh(original_question)

        # Duplicate the question
        result = await service.duplicate_question(original_question.id)

        assert result is not None
        assert result.id != original_question.id  # Different ID
        assert result.question_text == original_question.question_text
        assert result.min_answers == 2  # Preserved
        assert result.max_answers == 5  # Preserved
        assert result.label == "Original (Copy)"

    async def test_duplicate_questions_to_matrix_preserves_answer_counts(
        self, service, test_db, sample_workspace, sample_company
    ):
        """Test that duplicating questions to another matrix preserves answer counts."""
        # Create source and target matrices
        source_matrix = MatrixEntity(
            name="Source Matrix",
            description="Source",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        target_matrix = MatrixEntity(
            name="Target Matrix",
            description="Target",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        test_db.add_all([source_matrix, target_matrix])
        await test_db.commit()
        await test_db.refresh(source_matrix)
        await test_db.refresh(target_matrix)

        # Create question with custom answer counts in source matrix
        source_question = QuestionEntity(
            matrix_id=source_matrix.id,
            question_text="Question with custom counts",
            question_type_id=1,
            min_answers=3,
            max_answers=None,  # Unlimited
            label="Custom Counts",
            company_id=sample_company.id,
        )
        test_db.add(source_question)
        await test_db.commit()
        await test_db.refresh(source_question)

        # Duplicate questions to target matrix
        duplicated_questions = await service.duplicate_questions_to_matrix(
            source_matrix.id, target_matrix.id
        )

        assert len(duplicated_questions) == 1
        duplicated = duplicated_questions[0]

        assert duplicated.matrix_id == target_matrix.id
        assert duplicated.question_text == "Question with custom counts"
        assert duplicated.min_answers == 3  # Preserved
        assert duplicated.max_answers is None  # Preserved (unlimited)
        assert duplicated.label == "Custom Counts"

    # Agent QA Tests
    async def test_create_question_with_agent_qa_enabled(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with agent QA enabled."""
        question_data = QuestionCreateModel(
            question_text="Question with agent QA",
            question_type_id=1,
            use_agent_qa=True,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        result = await service.create_question(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "Question with agent QA"
        assert result.use_agent_qa is True

    async def test_create_question_with_agent_qa_disabled(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with agent QA explicitly disabled."""
        question_data = QuestionCreateModel(
            question_text="Question without agent QA",
            question_type_id=1,
            use_agent_qa=False,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        result = await service.create_question(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "Question without agent QA"
        assert result.use_agent_qa is False

    async def test_create_question_with_default_agent_qa(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with default agent QA (should be False)."""
        question_data = QuestionCreateModel(
            question_text="Question with default agent QA",
            question_type_id=1,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            # use_agent_qa not specified, should use default
        )

        result = await service.create_question(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.use_agent_qa is False  # Default value

    async def test_create_question_with_options_and_agent_qa(
        self, service, sample_matrix, sample_company
    ):
        """Test creating question with options and agent QA enabled."""
        options = [
            QuestionOptionCreateModel(value="Option 1"),
            QuestionOptionCreateModel(value="Option 2"),
        ]

        question_data = QuestionWithOptionsCreateModel(
            question_text="Select question with agent QA",
            question_type_id=5,  # SINGLE_SELECT
            use_agent_qa=True,
            options=options,
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        result = await service.create_question_with_options(
            sample_matrix.id, question_data, sample_company.id
        )

        assert result.matrix_id == sample_matrix.id
        assert result.question_text == "Select question with agent QA"
        assert result.use_agent_qa is True
        assert result.question_type_id == 5

    async def test_update_question_enable_agent_qa(
        self, service, test_db, sample_matrix, sample_company
    ):
        """Test updating question to enable agent QA."""
        # Create question with agent QA disabled
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Question to update",
            question_type_id=1,
            use_agent_qa=False,
            company_id=sample_company.id,
        )
        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(question)

        # Enable agent QA
        update_data = QuestionUpdateModel(use_agent_qa=True)
        result = await service.update_question(question.id, update_data)

        assert result is not None
        assert result.use_agent_qa is True
        assert result.question_text == "Question to update"  # Unchanged

    async def test_update_question_disable_agent_qa(
        self, service, test_db, sample_matrix, sample_company
    ):
        """Test updating question to disable agent QA."""
        # Create question with agent QA enabled
        question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Question with agent QA",
            question_type_id=1,
            use_agent_qa=True,
            company_id=sample_company.id,
        )
        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(question)

        # Disable agent QA
        update_data = QuestionUpdateModel(use_agent_qa=False)
        result = await service.update_question(question.id, update_data)

        assert result is not None
        assert result.use_agent_qa is False
        assert result.question_text == "Question with agent QA"  # Unchanged

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_update_question_with_options_toggle_agent_qa(
        self,
        mock_get_message_queue,
        mock_tracer,
        service,
        matrix_with_entity_sets,
        sample_question,
        sample_company,
        sample_subscription,
    ):
        """Test updating question with options to toggle agent QA."""
        # Setup mocks
        mock_get_message_queue.return_value = None
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        update_data = QuestionWithOptionsUpdateModel(
            use_agent_qa=True,
            options=[
                QuestionOptionCreateModel(value="New Option 1"),
                QuestionOptionCreateModel(value="New Option 2"),
            ],
        )

        result = await service.update_question_with_options_and_reprocess(
            matrix_with_entity_sets.id,
            sample_question.id,
            update_data,
            sample_company.id,
        )

        assert result is not None
        assert result.use_agent_qa is True

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_question_preserves_agent_qa(
        self, mock_tracer, service, test_db, sample_matrix, sample_company
    ):
        """Test that duplicating question preserves agent QA setting."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create question with agent QA enabled
        original_question = QuestionEntity(
            matrix_id=sample_matrix.id,
            question_text="Question to duplicate",
            question_type_id=1,
            use_agent_qa=True,
            label="Original",
            company_id=sample_company.id,
        )
        test_db.add(original_question)
        await test_db.commit()
        await test_db.refresh(original_question)

        # Duplicate the question
        result = await service.duplicate_question(original_question.id)

        assert result is not None
        assert result.id != original_question.id  # Different ID
        assert result.question_text == original_question.question_text
        assert result.use_agent_qa is True  # Preserved
        assert result.label == "Original (Copy)"

    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_questions_to_matrix_preserves_agent_qa(
        self, mock_tracer, service, test_db, sample_workspace, sample_company
    ):
        """Test that duplicating questions to another matrix preserves agent QA."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create source and target matrices
        source_matrix = MatrixEntity(
            name="Source Matrix",
            description="Source",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        target_matrix = MatrixEntity(
            name="Target Matrix",
            description="Target",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        test_db.add_all([source_matrix, target_matrix])
        await test_db.commit()
        await test_db.refresh(source_matrix)
        await test_db.refresh(target_matrix)

        # Create question with agent QA enabled in source matrix
        source_question = QuestionEntity(
            matrix_id=source_matrix.id,
            question_text="Question with agent QA",
            question_type_id=1,
            use_agent_qa=True,
            label="Agent QA Question",
            company_id=sample_company.id,
        )
        test_db.add(source_question)
        await test_db.commit()
        await test_db.refresh(source_question)

        # Duplicate questions to target matrix
        duplicated_questions = await service.duplicate_questions_to_matrix(
            source_matrix.id, target_matrix.id
        )

        assert len(duplicated_questions) == 1
        duplicated = duplicated_questions[0]

        assert duplicated.matrix_id == target_matrix.id
        assert duplicated.question_text == "Question with agent QA"
        assert duplicated.use_agent_qa is True  # Preserved
        assert duplicated.label == "Agent QA Question"
