import pytest
from unittest.mock import patch
from fastapi import HTTPException

from packages.matrices.services.matrix_template_variable_service import (
    MatrixTemplateVariableService,
)
from packages.matrices.models.domain.matrix_template_variable import (
    MatrixTemplateVariableCreateModel,
    MatrixTemplateVariableUpdateModel,
)
from packages.questions.models.domain.question_template_variable import (
    QuestionTemplateVariableCreateModel,
)


@pytest.fixture
def matrix_template_variable_service(test_db):
    """Create a MatrixTemplateVariableService instance."""
    return MatrixTemplateVariableService()


@pytest.fixture
def sample_template_variable_data(sample_company):
    """Sample template variable data for testing."""
    return MatrixTemplateVariableCreateModel(
        template_string="company",
        value="Acme Corp",
        matrix_id=1,  # Will be overridden in tests
        company_id=sample_company.id,
    )


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
class TestMatrixTemplateVariableService:
    """Unit tests for MatrixTemplateVariableService."""

    @pytest.mark.asyncio
    async def test_create_template_variable_success(
        self,
        mock_start_span,
        matrix_template_variable_service,
        sample_matrix,
        sample_company,
        sample_template_variable_data,
    ):
        """Test successful creation of a template variable."""
        variable_data = MatrixTemplateVariableCreateModel(
            template_string="company",
            value="Acme Corp",
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        result = await matrix_template_variable_service.create_template_variable(
            sample_matrix.id, variable_data, sample_company.id
        )

        assert result is not None
        assert result.template_string == "company"
        assert result.value == "Acme Corp"
        assert result.matrix_id == sample_matrix.id

    @pytest.mark.asyncio
    async def test_create_template_variable_matrix_not_found(
        self,
        mock_start_span,
        matrix_template_variable_service,
        sample_company,
        sample_template_variable_data,
    ):
        """Test creating template variable for non-existent matrix."""
        variable_data = MatrixTemplateVariableCreateModel(
            template_string="company",
            value="Acme Corp",
            matrix_id=999,
            company_id=sample_company.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await matrix_template_variable_service.create_template_variable(
                999, variable_data, sample_company.id
            )

        assert exc_info.value.status_code == 404
        assert "Matrix not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_template_variable_duplicate_template_string(
        self,
        mock_start_span,
        matrix_template_variable_service,
        sample_matrix,
        sample_company,
    ):
        """Test creating template variable with duplicate template string."""
        variable_data = MatrixTemplateVariableCreateModel(
            template_string="company",
            value="Acme Corp",
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        # Create first variable
        await matrix_template_variable_service.create_template_variable(
            sample_matrix.id, variable_data, sample_company.id
        )

        # Try to create duplicate
        duplicate_data = MatrixTemplateVariableCreateModel(
            template_string="company",
            value="Different Corp",
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )

        with pytest.raises(HTTPException) as exc_info:
            await matrix_template_variable_service.create_template_variable(
                sample_matrix.id, duplicate_data, sample_company.id
            )

        assert exc_info.value.status_code == 400
        assert "already exists" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_template_variable_success(
        self,
        mock_start_span,
        matrix_template_variable_service,
        sample_matrix,
        sample_company,
    ):
        """Test successful retrieval of a template variable."""
        # Create a variable first
        variable_data = MatrixTemplateVariableCreateModel(
            template_string="company",
            value="Acme Corp",
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )
        created = await matrix_template_variable_service.create_template_variable(
            sample_matrix.id, variable_data, sample_company.id
        )

        result = await matrix_template_variable_service.get_template_variable(
            created.id, sample_company.id
        )

        assert result is not None
        assert result.id == created.id
        assert result.template_string == "company"

    @pytest.mark.asyncio
    async def test_get_template_variable_not_found(
        self, mock_start_span, matrix_template_variable_service
    ):
        """Test retrieval of non-existent template variable."""
        result = await matrix_template_variable_service.get_template_variable(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_matrix_template_variables(
        self,
        mock_start_span,
        matrix_template_variable_service,
        sample_matrix,
        sample_company,
    ):
        """Test getting all template variables for a matrix."""
        # Create multiple variables
        variables_data = [
            MatrixTemplateVariableCreateModel(
                template_string="company",
                value="Acme Corp",
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
            ),
            MatrixTemplateVariableCreateModel(
                template_string="department",
                value="Engineering",
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
            ),
            MatrixTemplateVariableCreateModel(
                template_string="location",
                value="San Francisco",
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
            ),
        ]

        for var_data in variables_data:
            await matrix_template_variable_service.create_template_variable(
                sample_matrix.id, var_data, sample_company.id
            )

        result = await matrix_template_variable_service.get_matrix_template_variables(
            sample_matrix.id, sample_company.id
        )

        assert len(result) == 3
        template_strings = {var.template_string for var in result}
        assert template_strings == {"company", "department", "location"}

    @pytest.mark.asyncio
    async def test_get_template_mappings(
        self,
        mock_start_span,
        matrix_template_variable_service,
        sample_matrix,
        sample_company,
    ):
        """Test getting template string to value mappings."""
        # Create variables
        variables_data = [
            MatrixTemplateVariableCreateModel(
                template_string="company",
                value="Acme Corp",
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
            ),
            MatrixTemplateVariableCreateModel(
                template_string="department",
                value="Engineering",
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
            ),
        ]

        for var_data in variables_data:
            await matrix_template_variable_service.create_template_variable(
                sample_matrix.id, var_data, sample_company.id
            )

        result = await matrix_template_variable_service.get_template_mappings(
            sample_matrix.id
        )

        assert result == {"company": "Acme Corp", "department": "Engineering"}

    @pytest.mark.asyncio
    async def test_update_template_variable_success(
        self,
        mock_start_span,
        matrix_template_variable_service,
        sample_matrix,
        sample_company,
    ):
        """Test successful update of a template variable."""
        # Create a variable
        variable_data = MatrixTemplateVariableCreateModel(
            template_string="company",
            value="Acme Corp",
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )
        created = await matrix_template_variable_service.create_template_variable(
            sample_matrix.id, variable_data, sample_company.id
        )

        # Update it
        update_data = MatrixTemplateVariableUpdateModel(value="Updated Corp")
        result = await matrix_template_variable_service.update_template_variable(
            created.id, update_data
        )

        assert result is not None
        assert result.value == "Updated Corp"
        assert result.template_string == "company"  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_update_template_variable_not_found(
        self, mock_start_span, matrix_template_variable_service
    ):
        """Test updating non-existent template variable."""
        update_data = MatrixTemplateVariableUpdateModel(value="New Value")

        with pytest.raises(HTTPException) as exc_info:
            await matrix_template_variable_service.update_template_variable(
                999, update_data
            )

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_template_variable_duplicate_string(
        self,
        mock_start_span,
        matrix_template_variable_service,
        sample_matrix,
        sample_company,
    ):
        """Test updating template variable with duplicate template string."""
        # Create two variables
        _ = await matrix_template_variable_service.create_template_variable(
            sample_matrix.id,
            MatrixTemplateVariableCreateModel(
                template_string="company",
                value="Acme Corp",
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
            ),
            sample_company.id,
        )
        var2 = await matrix_template_variable_service.create_template_variable(
            sample_matrix.id,
            MatrixTemplateVariableCreateModel(
                template_string="department",
                value="Engineering",
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
            ),
            sample_company.id,
        )

        # Try to update var2 to have same template_string as var1
        update_data = MatrixTemplateVariableUpdateModel(template_string="company")

        with pytest.raises(HTTPException) as exc_info:
            await matrix_template_variable_service.update_template_variable(
                var2.id, update_data
            )

        assert exc_info.value.status_code == 400
        assert "already exists" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_template_variable_success(
        self,
        mock_start_span,
        matrix_template_variable_service,
        sample_matrix,
        sample_company,
    ):
        """Test successful deletion of a template variable."""
        # Create a variable
        variable_data = MatrixTemplateVariableCreateModel(
            template_string="company",
            value="Acme Corp",
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )
        created = await matrix_template_variable_service.create_template_variable(
            sample_matrix.id, variable_data, sample_company.id
        )

        result = await matrix_template_variable_service.delete_template_variable(
            created.id
        )

        assert result is True

        # Verify it's deleted
        deleted_var = await matrix_template_variable_service.get_template_variable(
            created.id
        )
        assert deleted_var is None

    @pytest.mark.asyncio
    async def test_delete_template_variable_in_use(
        self,
        mock_start_span,
        matrix_template_variable_service,
        sample_matrix,
        sample_company,
    ):
        """Test deletion of template variable that's in use."""
        # Create a variable
        variable_data = MatrixTemplateVariableCreateModel(
            template_string="company",
            value="Acme Corp",
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )
        created = await matrix_template_variable_service.create_template_variable(
            sample_matrix.id, variable_data, sample_company.id
        )

        # Create a question template variable association
        association_data = QuestionTemplateVariableCreateModel(
            question_id=1,
            template_variable_id=created.id,
            company_id=sample_company.id,
        )
        await matrix_template_variable_service.question_template_var_repo.create(
            association_data
        )

        with pytest.raises(HTTPException) as exc_info:
            await matrix_template_variable_service.delete_template_variable(created.id)

        assert exc_info.value.status_code == 400
        assert "is used by" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_affected_questions(
        self,
        mock_start_span,
        matrix_template_variable_service,
        sample_matrix,
        sample_company,
    ):
        """Test getting questions affected by a template variable."""
        # Create a variable
        variable_data = MatrixTemplateVariableCreateModel(
            template_string="company",
            value="Acme Corp",
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
        )
        created = await matrix_template_variable_service.create_template_variable(
            sample_matrix.id, variable_data, sample_company.id
        )

        # Create question associations
        association_data_1 = QuestionTemplateVariableCreateModel(
            question_id=1,
            template_variable_id=created.id,
            company_id=sample_company.id,
        )
        await matrix_template_variable_service.question_template_var_repo.create(
            association_data_1
        )

        association_data_2 = QuestionTemplateVariableCreateModel(
            question_id=2,
            template_variable_id=created.id,
            company_id=sample_company.id,
        )
        await matrix_template_variable_service.question_template_var_repo.create(
            association_data_2
        )

        result = await matrix_template_variable_service.get_affected_questions(
            created.id
        )

        assert set(result) == {1, 2}
