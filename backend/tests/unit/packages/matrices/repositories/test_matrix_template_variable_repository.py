import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from packages.matrices.repositories.matrix_template_variable_repository import (
    MatrixTemplateVariableRepository,
)
from packages.matrices.models.database.matrix_template_variable import (
    MatrixTemplateVariableEntity,
)
from packages.matrices.models.domain.matrix_template_variable import (
    MatrixTemplateVariableCreateModel,
    MatrixTemplateVariableUpdateModel,
)
from packages.matrices.models.database.matrix import MatrixEntity


class TestMatrixTemplateVariableRepository:
    """Test MatrixTemplateVariableRepository methods."""

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return MatrixTemplateVariableRepository(test_db)

    async def test_create_template_variable(
        self, repository, sample_matrix, sample_company
    ):
        """Test creating a template variable."""
        create_model = MatrixTemplateVariableCreateModel(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            template_string="project_name",
            value="Project Alpha",
        )

        result = await repository.create(create_model)

        assert result.matrix_id == sample_matrix.id
        assert result.template_string == "project_name"
        assert result.value == "Project Alpha"

    async def test_get_template_variable_by_id(
        self, repository, sample_template_variable
    ):
        """Test getting template variable by ID."""
        result = await repository.get(sample_template_variable.id)

        assert result is not None
        assert result.id == sample_template_variable.id
        assert result.template_string == sample_template_variable.template_string
        assert result.value == sample_template_variable.value

    async def test_get_template_variable_not_found(self, repository):
        """Test getting non-existent template variable."""
        result = await repository.get(999)
        assert result is None

    async def test_get_by_matrix_id(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test getting all template variables for a matrix."""
        # Create multiple template variables
        variables_data = [
            MatrixTemplateVariableCreateModel(
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
                template_string="var1",
                value="value1",
            ),
            MatrixTemplateVariableCreateModel(
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
                template_string="var2",
                value="value2",
            ),
            MatrixTemplateVariableCreateModel(
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
                template_string="var3",
                value="value3",
            ),
        ]

        for create_model in variables_data:
            created_var = await repository.create(create_model)

        await test_db.commit()

        # Test retrieval
        results = await repository.get_by_matrix_id(sample_matrix.id)

        assert len(results) >= 3  # At least our created variables
        template_strings = [v.template_string for v in results]
        assert "var1" in template_strings
        assert "var2" in template_strings
        assert "var3" in template_strings

    async def test_get_by_matrix_id_excludes_deleted(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test that get_by_matrix_id excludes soft deleted variables."""
        # Create active variable
        active_create = MatrixTemplateVariableCreateModel(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            template_string="active_var",
            value="active_value",
        )
        active_var = await repository.create(active_create)

        # Create deleted variable directly as entity since we need to set deleted=True
        deleted_var = MatrixTemplateVariableEntity(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            template_string="deleted_var",
            value="deleted_value",
            deleted=True,
        )
        test_db.add(deleted_var)
        await test_db.commit()

        results = await repository.get_by_matrix_id(sample_matrix.id)

        template_strings = [v.template_string for v in results]
        assert "active_var" in template_strings
        assert "deleted_var" not in template_strings

    async def test_get_by_template_string(
        self, repository, sample_matrix, sample_template_variable
    ):
        """Test getting template variable by template string."""
        result = await repository.get_by_template_string(
            sample_matrix.id, sample_template_variable.template_string
        )

        assert result is not None
        assert result.id == sample_template_variable.id
        assert result.template_string == sample_template_variable.template_string
        assert result.value == sample_template_variable.value

    async def test_get_by_template_string_not_found(self, repository, sample_matrix):
        """Test getting template variable by non-existent template string."""
        result = await repository.get_by_template_string(
            sample_matrix.id, "nonexistent"
        )
        assert result is None

    async def test_get_by_template_string_excludes_deleted(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test that get_by_template_string excludes soft deleted variables."""
        deleted_var = MatrixTemplateVariableEntity(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            template_string="deleted_var",
            value="deleted_value",
            deleted=True,
        )
        test_db.add(deleted_var)
        await test_db.commit()

        result = await repository.get_by_template_string(
            sample_matrix.id, "deleted_var"
        )
        assert result is None

    async def test_get_template_mappings(
        self, repository, sample_matrix, sample_company, test_db
    ):
        """Test getting template string to value mappings."""
        # Create multiple variables
        variables_data = [
            MatrixTemplateVariableCreateModel(
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
                template_string="company",
                value="Acme Corp",
            ),
            MatrixTemplateVariableCreateModel(
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
                template_string="project",
                value="Project X",
            ),
            MatrixTemplateVariableCreateModel(
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
                template_string="year",
                value="2024",
            ),
        ]

        for create_model in variables_data:
            created_var = await repository.create(create_model)

        await test_db.commit()

        mappings = await repository.get_template_mappings(sample_matrix.id)

        assert isinstance(mappings, dict)
        assert "company" in mappings
        assert mappings["company"] == "Acme Corp"
        assert "project" in mappings
        assert mappings["project"] == "Project X"
        assert "year" in mappings
        assert mappings["year"] == "2024"

    async def test_get_template_mappings_empty(self, repository, sample_matrix):
        """Test getting template mappings for matrix with no variables."""
        mappings = await repository.get_template_mappings(sample_matrix.id)
        assert mappings == {}

    async def test_update_template_variable(self, repository, sample_template_variable):
        """Test updating a template variable."""
        update_model = MatrixTemplateVariableUpdateModel(value="Updated Corporation")

        result = await repository.update(sample_template_variable.id, update_model)

        assert result is not None
        assert result.value == "Updated Corporation"
        assert (
            result.template_string == sample_template_variable.template_string
        )  # Unchanged

    async def test_update_template_variable_not_found(self, repository):
        """Test updating non-existent template variable."""
        update_model = MatrixTemplateVariableUpdateModel(value="Updated")
        result = await repository.update(999, update_model)
        assert result is None

    async def test_soft_delete_template_variable(
        self, repository, sample_template_variable
    ):
        """Test soft deleting a template variable."""
        success = await repository.delete(sample_template_variable.id)
        assert success is True

        # Verify it's soft deleted (not returned in normal queries)
        result = await repository.get(sample_template_variable.id)
        assert result is None

    async def test_soft_delete_template_variable_not_found(self, repository):
        """Test soft deleting non-existent template variable."""
        success = await repository.delete(999)
        assert success is False

    async def test_different_matrices_isolation(
        self, repository, test_db, sample_workspace, sample_company
    ):
        """Test that template variables are isolated by matrix."""
        # Create two matrices
        matrix1 = MatrixEntity(
            name="Matrix 1",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        matrix2 = MatrixEntity(
            name="Matrix 2",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        test_db.add(matrix1)
        test_db.add(matrix2)
        await test_db.commit()
        await test_db.refresh(matrix1)
        await test_db.refresh(matrix2)

        # Create variables in each matrix
        var1 = MatrixTemplateVariableEntity(
            matrix_id=matrix1.id,
            company_id=sample_company.id,
            template_string="shared_name",
            value="value_for_matrix1",
        )
        var2 = MatrixTemplateVariableEntity(
            matrix_id=matrix2.id,
            company_id=sample_company.id,
            template_string="shared_name",
            value="value_for_matrix2",
        )
        test_db.add(var1)
        test_db.add(var2)
        await test_db.commit()

        # Test isolation
        matrix1_vars = await repository.get_by_matrix_id(matrix1.id)
        matrix2_vars = await repository.get_by_matrix_id(matrix2.id)

        matrix1_var = next(
            v for v in matrix1_vars if v.template_string == "shared_name"
        )
        matrix2_var = next(
            v for v in matrix2_vars if v.template_string == "shared_name"
        )

        assert matrix1_var.value == "value_for_matrix1"
        assert matrix2_var.value == "value_for_matrix2"
        assert matrix1_var.id != matrix2_var.id
