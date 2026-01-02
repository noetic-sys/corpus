import pytest
from unittest.mock import patch
from fastapi import HTTPException

from packages.questions.services.question_template_variable_service import (
    QuestionTemplateVariableService,
)
from packages.questions.models.domain.question_template_variable import (
    QuestionTemplateVariableCreateModel,
)
from packages.questions.models.domain.question import QuestionCreateModel
from packages.matrices.models.domain.matrix_template_variable import (
    MatrixTemplateVariableCreateModel,
)
from packages.matrices.models.domain.matrix import MatrixCreateModel
from packages.matrices.repositories.matrix_repository import MatrixRepository
from packages.questions.repositories.question_repository import QuestionRepository
from packages.matrices.repositories.matrix_template_variable_repository import (
    MatrixTemplateVariableRepository,
)
from packages.workspaces.models.database.workspace import WorkspaceEntity


@pytest.fixture
def question_template_variable_service(test_db):
    """Create a QuestionTemplateVariableService instance."""
    return QuestionTemplateVariableService(test_db)


@pytest.fixture
def matrix_repo(test_db):
    """Create a MatrixRepository instance."""
    return MatrixRepository(test_db)


@pytest.fixture
def question_repo(test_db):
    """Create a QuestionRepository instance."""
    return QuestionRepository(test_db)


@pytest.fixture
def template_var_repo(test_db):
    """Create a MatrixTemplateVariableRepository instance."""
    return MatrixTemplateVariableRepository(test_db)


@pytest.fixture
async def sample_question(question_repo, sample_matrix, sample_company):
    """Create a sample question for testing."""
    question_data = QuestionCreateModel(
        matrix_id=sample_matrix.id,
        company_id=sample_company.id,
        question_text="What is the status of #{{1}} in #{{2}} department?",
        question_type_id=1,
    )
    question = await question_repo.create(question_data)
    return question


@pytest.fixture
async def sample_template_variables(template_var_repo, sample_matrix, sample_company):
    """Create sample template variables for testing."""
    var1_data = MatrixTemplateVariableCreateModel(
        matrix_id=sample_matrix.id,
        company_id=sample_company.id,
        template_string="company",
        value="Acme Corp",
    )
    var2_data = MatrixTemplateVariableCreateModel(
        matrix_id=sample_matrix.id,
        company_id=sample_company.id,
        template_string="department",
        value="Engineering",
    )
    var1 = await template_var_repo.create(var1_data)
    var2 = await template_var_repo.create(var2_data)
    return [var1, var2]


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
class TestQuestionTemplateVariableService:
    """Unit tests for QuestionTemplateVariableService."""

    @pytest.mark.asyncio
    async def test_create_association_success(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_question,
        sample_template_variables,
    ):
        """Test successful creation of a question-template variable association."""
        association_data = QuestionTemplateVariableCreateModel(
            question_id=sample_question.id,
            template_variable_id=sample_template_variables[0].id,
            company_id=sample_question.company_id,
        )

        result = await question_template_variable_service.create_association(
            association_data
        )

        assert result is not None
        assert result.question_id == sample_question.id
        assert result.template_variable_id == sample_template_variables[0].id

    @pytest.mark.asyncio
    async def test_create_association_question_not_found(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_template_variables,
    ):
        """Test creating association for non-existent question."""
        association_data = QuestionTemplateVariableCreateModel(
            question_id=999,
            template_variable_id=sample_template_variables[0].id,
            company_id=sample_template_variables[0].company_id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await question_template_variable_service.create_association(
                association_data
            )

        assert exc_info.value.status_code == 404
        assert "Question not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_association_template_variable_not_found(
        self, mock_start_span, question_template_variable_service, sample_question
    ):
        """Test creating association for non-existent template variable."""
        association_data = QuestionTemplateVariableCreateModel(
            question_id=sample_question.id,
            template_variable_id=999,
            company_id=sample_question.company_id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await question_template_variable_service.create_association(
                association_data
            )

        assert exc_info.value.status_code == 404
        assert "Template variable not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_association_different_matrices(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_question,
        sample_company,
        matrix_repo,
        template_var_repo,
        test_db,
    ):
        """Test creating association between question and template variable from different matrices."""
        # Create another workspace and matrix
        other_workspace = WorkspaceEntity(
            name="Other Workspace",
            description="Other workspace",
            company_id=sample_company.id,
        )
        test_db.add(other_workspace)
        await test_db.commit()
        await test_db.refresh(other_workspace)

        # Create another matrix and template variable
        other_matrix_data = MatrixCreateModel(
            name="Other Matrix",
            description="Different matrix",
            workspace_id=other_workspace.id,
            company_id=sample_company.id,
        )
        other_matrix = await matrix_repo.create(other_matrix_data)
        other_template_var_data = MatrixTemplateVariableCreateModel(
            matrix_id=other_matrix.id,
            company_id=sample_company.id,
            template_string="other_var",
            value="Other Value",
        )
        other_template_var = await template_var_repo.create(other_template_var_data)

        association_data = QuestionTemplateVariableCreateModel(
            question_id=sample_question.id,
            template_variable_id=other_template_var.id,
            company_id=sample_question.company_id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await question_template_variable_service.create_association(
                association_data
            )

        assert exc_info.value.status_code == 400
        assert "same matrix" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_association_already_exists(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_question,
        sample_template_variables,
    ):
        """Test creating duplicate association."""
        association_data = QuestionTemplateVariableCreateModel(
            question_id=sample_question.id,
            template_variable_id=sample_template_variables[0].id,
            company_id=sample_question.company_id,
        )

        # Create first association
        await question_template_variable_service.create_association(association_data)

        # Try to create duplicate
        with pytest.raises(HTTPException) as exc_info:
            await question_template_variable_service.create_association(
                association_data
            )

        assert exc_info.value.status_code == 400
        assert "already exists" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_question_template_variables(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_question,
        sample_template_variables,
    ):
        """Test getting all template variable associations for a question."""
        # Create associations
        for template_var in sample_template_variables:
            association_data = QuestionTemplateVariableCreateModel(
                question_id=sample_question.id,
                template_variable_id=template_var.id,
                company_id=sample_question.company_id,
            )
            await question_template_variable_service.create_association(
                association_data
            )

        result = (
            await question_template_variable_service.get_question_template_variables(
                sample_question.id
            )
        )

        assert len(result) == 2
        template_var_ids = {assoc.template_variable_id for assoc in result}
        expected_ids = {var.id for var in sample_template_variables}
        assert template_var_ids == expected_ids

    @pytest.mark.asyncio
    async def test_get_questions_using_template_variable(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_question,
        sample_template_variables,
    ):
        """Test getting all questions using a specific template variable."""
        # Create association
        association_data = QuestionTemplateVariableCreateModel(
            question_id=sample_question.id,
            template_variable_id=sample_template_variables[0].id,
            company_id=sample_question.company_id,
        )
        await question_template_variable_service.create_association(association_data)

        result = await question_template_variable_service.get_questions_using_template_variable(
            sample_template_variables[0].id
        )

        assert len(result) == 1
        assert result[0].question_id == sample_question.id

    @pytest.mark.asyncio
    async def test_sync_question_from_text_success(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_question,
        sample_template_variables,
    ):
        """Test syncing template variables from question text."""
        result = await question_template_variable_service.sync_question_from_text(
            sample_question.id
        )

        # Should find template variables with IDs 1 and 2 in the question text
        assert set(result) == {1, 2}

    @pytest.mark.asyncio
    async def test_sync_question_from_text_question_not_found(
        self, mock_start_span, question_template_variable_service
    ):
        """Test syncing for non-existent question."""
        with pytest.raises(HTTPException) as exc_info:
            await question_template_variable_service.sync_question_from_text(999)

        assert exc_info.value.status_code == 404
        assert "Question not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_bulk_sync_questions_from_text(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_matrix,
        sample_template_variables,
        question_repo,
        sample_company,
    ):
        """Test bulk syncing multiple questions."""
        # Create multiple questions
        question1_data = QuestionCreateModel(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            question_text="Status of #{{1}}?",
            question_type_id=1,
        )
        question2_data = QuestionCreateModel(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            question_text="Info about #{{2}}?",
            question_type_id=1,
        )
        question1 = await question_repo.create(question1_data)
        question2 = await question_repo.create(question2_data)

        result = await question_template_variable_service.bulk_sync_questions_from_text(
            [question1.id, question2.id]
        )

        assert result == 2  # Both questions synced successfully

    @pytest.mark.asyncio
    async def test_remove_association_success(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_question,
        sample_template_variables,
    ):
        """Test successful removal of association."""
        # Create association
        association_data = QuestionTemplateVariableCreateModel(
            question_id=sample_question.id,
            template_variable_id=sample_template_variables[0].id,
            company_id=sample_question.company_id,
        )
        await question_template_variable_service.create_association(association_data)

        result = await question_template_variable_service.remove_association(
            sample_question.id, sample_template_variables[0].id
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_remove_association_not_found(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_question,
        sample_template_variables,
    ):
        """Test removing non-existent association."""
        result = await question_template_variable_service.remove_association(
            sample_question.id, sample_template_variables[0].id
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_all_question_associations(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_question,
        sample_template_variables,
    ):
        """Test removing all associations for a question."""
        # Create multiple associations
        for template_var in sample_template_variables:
            association_data = QuestionTemplateVariableCreateModel(
                question_id=sample_question.id,
                template_variable_id=template_var.id,
                company_id=sample_question.company_id,
            )
            await question_template_variable_service.create_association(
                association_data
            )

        result = (
            await question_template_variable_service.remove_all_question_associations(
                sample_question.id
            )
        )

        assert result == 2  # Two associations removed

    @pytest.mark.asyncio
    async def test_get_questions_affected_by_template_change(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_question,
        sample_template_variables,
    ):
        """Test getting questions affected by template variable change."""
        # Create association
        association_data = QuestionTemplateVariableCreateModel(
            question_id=sample_question.id,
            template_variable_id=sample_template_variables[0].id,
            company_id=sample_question.company_id,
        )
        await question_template_variable_service.create_association(association_data)

        result = await question_template_variable_service.get_questions_affected_by_template_change(
            sample_template_variables[0].id
        )

        assert result == [sample_question.id]

    @pytest.mark.asyncio
    async def test_validate_question_template_variables_valid(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_matrix,
        sample_template_variables,
        sample_company,
        question_repo,
    ):
        """Test validation when question template variables are properly associated."""
        # Create question that uses the actual template variable IDs from our fixtures
        var1_id = sample_template_variables[0].id
        var2_id = sample_template_variables[1].id
        question_data = QuestionCreateModel(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            question_text=f"Status of #{{{{{var1_id}}}}} in #{{{{{var2_id}}}}}?",
            question_type_id=1,
        )
        question = await question_repo.create(question_data)

        # Create associations for both variables found in text
        for template_var in sample_template_variables:
            association_data = QuestionTemplateVariableCreateModel(
                question_id=question.id,
                template_variable_id=template_var.id,
                company_id=question.company_id,
            )
            await question_template_variable_service.create_association(
                association_data
            )

        result = await question_template_variable_service.validate_question_template_variables(
            question.id
        )

        assert result.question_id == question.id
        assert result.is_valid is True
        assert len(result.missing_associations) == 0
        assert len(result.extra_associations) == 0

    @pytest.mark.asyncio
    async def test_validate_question_template_variables_invalid(
        self,
        mock_start_span,
        question_template_variable_service,
        sample_matrix,
        sample_template_variables,
        sample_company,
        question_repo,
    ):
        """Test validation when question template variables are not properly associated."""
        # Create question with template variables but only associate one
        var1_id = sample_template_variables[0].id
        var2_id = sample_template_variables[1].id
        question_data = QuestionCreateModel(
            company_id=sample_company.id,
            matrix_id=sample_matrix.id,
            question_text=f"Status of #{{{{{var1_id}}}}} in #{{{{{var2_id}}}}}?",
            question_type_id=1,
        )
        question = await question_repo.create(question_data)

        # Only create association for one variable (missing the other)
        association_data = QuestionTemplateVariableCreateModel(
            question_id=question.id,
            template_variable_id=sample_template_variables[0].id,
            company_id=question.company_id,
        )
        await question_template_variable_service.create_association(association_data)

        result = await question_template_variable_service.validate_question_template_variables(
            question.id
        )

        assert result.question_id == question.id
        assert result.is_valid is False

    @pytest.mark.asyncio
    async def test_validate_question_template_variables_question_not_found(
        self, mock_start_span, question_template_variable_service
    ):
        """Test validation for non-existent question."""
        with pytest.raises(HTTPException) as exc_info:
            await question_template_variable_service.validate_question_template_variables(
                999
            )

        assert exc_info.value.status_code == 404
        assert "Question not found" in str(exc_info.value.detail)
