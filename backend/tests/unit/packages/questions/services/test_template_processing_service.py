import pytest
from packages.qa.utils.document_reference import DocumentReference
from unittest.mock import patch
from datetime import datetime

from packages.questions.services.template_processing_service import (
    TemplateProcessingService,
)
from packages.matrices.models.domain.matrix_template_variable import (
    MatrixTemplateVariableModel,
)
from packages.questions.models.domain.question_template_variable import (
    QuestionTemplateVariableModel,
    QuestionTemplateVariableCreateModel,
)
from packages.matrices.models.domain.matrix_template_variable import (
    MatrixTemplateVariableCreateModel,
)
from packages.matrices.models.domain.matrix_enums import EntityRole


@pytest.fixture
def template_processing_service(test_db):
    """Create a TemplateProcessingService instance."""
    return TemplateProcessingService()


@pytest.fixture
def sample_template_variables():
    """Sample template variables for testing."""
    return [
        MatrixTemplateVariableModel(
            id=1,
            matrix_id=1,
            company_id=1,
            template_string="company",
            value="Acme Corp",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        MatrixTemplateVariableModel(
            id=2,
            matrix_id=1,
            company_id=1,
            template_string="department",
            value="Engineering",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
        MatrixTemplateVariableModel(
            id=3,
            matrix_id=1,
            company_id=1,
            template_string="location",
            value="San Francisco",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ),
    ]


@pytest.fixture
def sample_question_template_associations():
    """Sample question template variable associations for testing."""
    return [
        QuestionTemplateVariableModel(
            id=1,
            company_id=1,
            question_id=1,
            template_variable_id=1,
            created_at=datetime.now(),
        ),
        QuestionTemplateVariableModel(
            id=2,
            company_id=1,
            question_id=1,
            template_variable_id=2,
            created_at=datetime.now(),
        ),
    ]


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
class TestTemplateProcessingService:
    """Unit tests for TemplateProcessingService."""

    def test_extract_template_variable_ids_success(
        self, mock_start_span, template_processing_service
    ):
        """Test successful extraction of template variable IDs."""
        text = "What is the status of #{{1}} in #{{2}} department?"

        result = template_processing_service.extract_template_variable_ids(text)

        assert result == {1, 2}

    def test_extract_template_variable_ids_no_variables(
        self, mock_start_span, template_processing_service
    ):
        """Test extraction when no template variables are present."""
        text = "What is the company status?"

        result = template_processing_service.extract_template_variable_ids(text)

        assert result == set()

    def test_extract_template_variable_ids_duplicate_variables(
        self, mock_start_span, template_processing_service
    ):
        """Test extraction with duplicate template variables."""
        text = "Status of #{{1}} and again #{{1}} in #{{2}}?"

        result = template_processing_service.extract_template_variable_ids(text)

        assert result == {1, 2}

    def test_extract_template_variable_ids_ignores_name_patterns(
        self, mock_start_span, template_processing_service
    ):
        """Test that name-based patterns are ignored."""
        text = "Status of ${{company}} and #{{1}} in #{{2}}?"

        result = template_processing_service.extract_template_variable_ids(text)

        assert result == {1, 2}

    @pytest.mark.asyncio
    async def test_resolve_template_variables_success(
        self,
        mock_start_span,
        template_processing_service,
        sample_template_variables,
        sample_company,
    ):
        """Test successful resolution of template variables."""
        # Create template variables in database
        for var in sample_template_variables:
            create_model = MatrixTemplateVariableCreateModel(
                matrix_id=var.matrix_id,
                company_id=var.company_id,
                template_string=var.template_string,
                value=var.value,
            )
            await template_processing_service.template_var_repo.create(create_model)

        text = "What is the status of #{{1}} in #{{2}} department?"

        result = await template_processing_service.resolve_template_variables(text, 1)

        assert result == "What is the status of Acme Corp in Engineering department?"

    @pytest.mark.asyncio
    async def test_resolve_template_variables_no_variables(
        self, mock_start_span, template_processing_service
    ):
        """Test resolution when no template variables are present."""
        text = "What is the company status?"

        result = await template_processing_service.resolve_template_variables(text, 1)

        assert result == "What is the company status?"

    @pytest.mark.asyncio
    async def test_resolve_template_variables_missing_variable(
        self,
        mock_start_span,
        template_processing_service,
        sample_template_variables,
        sample_company,
    ):
        """Test resolution when a template variable doesn't exist."""
        # Create only first template variable
        create_model = MatrixTemplateVariableCreateModel(
            matrix_id=1,
            company_id=sample_company.id,
            template_string="company",
            value="Acme Corp",
        )
        await template_processing_service.template_var_repo.create(create_model)

        text = "Status of #{{1}} in #{{999}} department?"

        result = await template_processing_service.resolve_template_variables(text, 1)

        # Should resolve existing variable but leave missing one unchanged
        assert result == "Status of Acme Corp in #{{999}} department?"

    @pytest.mark.asyncio
    async def test_validate_template_variables_all_exist(
        self, mock_start_span, template_processing_service, sample_template_variables
    ):
        """Test validation when all template variables exist."""
        # Create template variables in database
        for var in sample_template_variables:
            create_model = MatrixTemplateVariableCreateModel(
                matrix_id=var.matrix_id,
                company_id=var.company_id,
                template_string=var.template_string,
                value=var.value,
            )
            await template_processing_service.template_var_repo.create(create_model)

        text = "Status of #{{1}} in #{{2}} department?"

        result = await template_processing_service.validate_template_variables(text, 1)

        assert len(result.validations) == 2
        validation_dict = result.to_dict()
        assert validation_dict == {1: True, 2: True}

    @pytest.mark.asyncio
    async def test_validate_template_variables_some_missing(
        self,
        mock_start_span,
        template_processing_service,
        sample_template_variables,
        sample_company,
    ):
        """Test validation when some template variables are missing."""
        # Create only first template variable
        create_model = MatrixTemplateVariableCreateModel(
            matrix_id=1,
            company_id=sample_company.id,
            template_string="company",
            value="Acme Corp",
        )
        await template_processing_service.template_var_repo.create(create_model)

        text = "Status of #{{1}} in #{{999}} department?"

        result = await template_processing_service.validate_template_variables(text, 1)

        assert len(result.validations) == 2
        validation_dict = result.to_dict()
        assert validation_dict == {1: True, 999: False}

    @pytest.mark.asyncio
    async def test_get_missing_template_variables(
        self,
        mock_start_span,
        template_processing_service,
        sample_template_variables,
        sample_company,
    ):
        """Test getting list of missing template variables."""
        # Create only first template variable
        create_model = MatrixTemplateVariableCreateModel(
            matrix_id=1,
            company_id=sample_company.id,
            template_string="company",
            value="Acme Corp",
        )
        await template_processing_service.template_var_repo.create(create_model)

        text = "Status of #{{1}} in #{{999}} and #{{888}} departments?"

        result = await template_processing_service.get_missing_template_variables(
            text, 1
        )

        assert set(result) == {999, 888}

    def test_has_template_variables_true(
        self, mock_start_span, template_processing_service
    ):
        """Test has_template_variables returns True when variables are present."""
        text = "Status of #{{1}} in department?"

        result = template_processing_service.has_template_variables(text)

        assert result is True

    def test_has_template_variables_false(
        self, mock_start_span, template_processing_service
    ):
        """Test has_template_variables returns False when no variables are present."""
        text = "What is the company status?"

        result = template_processing_service.has_template_variables(text)

        assert result is False

    @pytest.mark.asyncio
    async def test_preview_resolved_text(
        self, mock_start_span, template_processing_service, sample_template_variables
    ):
        """Test preview of how text would look resolved."""
        # Create template variables in database
        for var in sample_template_variables:
            create_model = MatrixTemplateVariableCreateModel(
                matrix_id=var.matrix_id,
                company_id=var.company_id,
                template_string=var.template_string,
                value=var.value,
            )
            await template_processing_service.template_var_repo.create(create_model)

        text = "Status of #{{1}} in #{{2}} department?"

        result = await template_processing_service.preview_resolved_text(text, 1)

        assert result.original == text
        assert result.resolved == "Status of Acme Corp in Engineering department?"
        assert set(result.variables_used) == {1, 2}

    @pytest.mark.asyncio
    async def test_sync_question_template_variables_new_question(
        self, mock_start_span, template_processing_service, sample_template_variables
    ):
        """Test syncing template variables for a new question."""
        # Create template variables in database
        for var in sample_template_variables:
            create_model = MatrixTemplateVariableCreateModel(
                matrix_id=var.matrix_id,
                company_id=var.company_id,
                template_string=var.template_string,
                value=var.value,
            )
            await template_processing_service.template_var_repo.create(create_model)

        question_text = "Status of #{{1}} in #{{2}} department?"
        question_id = 1

        result = await template_processing_service.sync_question_template_variables(
            question_id, question_text, 1, 1  # matrix_id=1, company_id=1
        )

        assert set(result) == {1, 2}

        # Verify associations were created
        associations = await template_processing_service.question_template_var_repo.get_by_question_id(
            question_id
        )
        assert len(associations) == 2
        assert {assoc.template_variable_id for assoc in associations} == {1, 2}

    @pytest.mark.asyncio
    async def test_sync_question_template_variables_update_existing(
        self, mock_start_span, template_processing_service, sample_template_variables
    ):
        """Test syncing template variables when updating existing question."""
        # Create template variables in database
        for var in sample_template_variables:
            create_model = MatrixTemplateVariableCreateModel(
                matrix_id=var.matrix_id,
                company_id=var.company_id,
                template_string=var.template_string,
                value=var.value,
            )
            await template_processing_service.template_var_repo.create(create_model)

        question_id = 1

        # Create initial associations for variables 1 and 2
        create_model1 = QuestionTemplateVariableCreateModel(
            question_id=question_id,
            template_variable_id=1,
            company_id=1,
        )
        create_model2 = QuestionTemplateVariableCreateModel(
            question_id=question_id,
            template_variable_id=2,
            company_id=1,
        )
        await template_processing_service.question_template_var_repo.create(
            create_model1
        )
        await template_processing_service.question_template_var_repo.create(
            create_model2
        )

        # Update question to use variables 1 and 3 (removing 2, adding 3)
        question_text = "Status of #{{1}} in #{{3}} location?"

        result = await template_processing_service.sync_question_template_variables(
            question_id, question_text, 1, 1  # matrix_id=1, company_id=1
        )

        assert set(result) == {1, 3}

        # Verify final associations
        associations = await template_processing_service.question_template_var_repo.get_by_question_id(
            question_id
        )
        assert len(associations) == 2
        assert {assoc.template_variable_id for assoc in associations} == {1, 3}

    @pytest.mark.asyncio
    async def test_sync_question_template_variables_no_variables(
        self, mock_start_span, template_processing_service
    ):
        """Test syncing when question has no template variables."""
        question_id = 1
        question_text = "What is the company status?"

        result = await template_processing_service.sync_question_template_variables(
            question_id, question_text, 1, 1  # matrix_id=1, company_id=1
        )

        assert result == []

        # Verify no associations were created
        associations = await template_processing_service.question_template_var_repo.get_by_question_id(
            question_id
        )
        assert len(associations) == 0

    @pytest.mark.asyncio
    async def test_get_questions_using_template_variable(
        self, mock_start_span, template_processing_service
    ):
        """Test getting questions that use a specific template variable."""
        # Create associations
        create_model1 = QuestionTemplateVariableCreateModel(
            question_id=1,
            template_variable_id=1,
            company_id=1,
        )
        create_model2 = QuestionTemplateVariableCreateModel(
            question_id=2,
            template_variable_id=1,
            company_id=1,
        )
        create_model3 = QuestionTemplateVariableCreateModel(
            question_id=3,
            template_variable_id=2,
            company_id=1,
        )
        await template_processing_service.question_template_var_repo.create(
            create_model1
        )
        await template_processing_service.question_template_var_repo.create(
            create_model2
        )
        await template_processing_service.question_template_var_repo.create(
            create_model3
        )

        result = (
            await template_processing_service.get_questions_using_template_variable(1)
        )

        assert set(result) == {1, 2}

    @pytest.mark.asyncio
    async def test_get_questions_using_any_template_variables(
        self, mock_start_span, template_processing_service
    ):
        """Test getting questions that use any of the specified template variables."""
        # Create associations
        create_model1 = QuestionTemplateVariableCreateModel(
            question_id=1,
            template_variable_id=1,
            company_id=1,
        )
        create_model2 = QuestionTemplateVariableCreateModel(
            question_id=2,
            template_variable_id=2,
            company_id=1,
        )
        create_model3 = QuestionTemplateVariableCreateModel(
            question_id=3,
            template_variable_id=3,
            company_id=1,
        )
        await template_processing_service.question_template_var_repo.create(
            create_model1
        )
        await template_processing_service.question_template_var_repo.create(
            create_model2
        )
        await template_processing_service.question_template_var_repo.create(
            create_model3
        )

        result = await template_processing_service.get_questions_using_any_template_variables(
            [1, 2]
        )

        assert set(result) == {1, 2}

    def test_extract_document_placeholder_roles_both(
        self, mock_start_span, template_processing_service
    ):
        """Test extraction of document placeholder roles."""
        text = "How does @{{LEFT}} relate to @{{RIGHT}}?"

        result = template_processing_service.extract_document_placeholder_roles(text)

        assert result == {EntityRole.LEFT, EntityRole.RIGHT}

    def test_extract_document_placeholder_roles_none(
        self, mock_start_span, template_processing_service
    ):
        """Test extraction when no document placeholders are present."""
        text = "What is the status of #{{1}}?"

        result = template_processing_service.extract_document_placeholder_roles(text)

        assert result == set()

    def test_has_document_placeholders_true(
        self, mock_start_span, template_processing_service
    ):
        """Test has_document_placeholders returns True when placeholders are present."""
        text = "How does @{{LEFT}} relate to @{{RIGHT}}?"

        result = template_processing_service.has_document_placeholders(text)

        assert result is True

    def test_has_document_placeholders_false(
        self, mock_start_span, template_processing_service
    ):
        """Test has_document_placeholders returns False when no placeholders are present."""
        text = "What is the status of #{{1}}?"

        result = template_processing_service.has_document_placeholders(text)

        assert result is False

    def test_resolve_document_placeholders_success(
        self, mock_start_span, template_processing_service
    ):
        """Test successful resolution of document placeholders."""

        entity_refs = [
            DocumentReference(document_id=456, role=EntityRole.LEFT),
            DocumentReference(document_id=789, role=EntityRole.RIGHT),
        ]

        text = "How does @{{LEFT}} relate to @{{RIGHT}}?"

        result = template_processing_service.resolve_document_placeholders(
            text, entity_refs
        )

        assert result == "How does Document 456 relate to Document 789?"

    def test_resolve_document_placeholders_no_placeholders(
        self, mock_start_span, template_processing_service
    ):
        """Test resolution when no document placeholders are present."""
        entity_refs = []
        text = "What is the status?"

        result = template_processing_service.resolve_document_placeholders(
            text, entity_refs
        )

        assert result == "What is the status?"
