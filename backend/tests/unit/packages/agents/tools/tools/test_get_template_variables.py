import pytest
from packages.matrices.models.database.matrix import MatrixEntity

from packages.agents.tools.base import ToolPermission
from packages.agents.tools.tools.get_template_variables import (
    GetTemplateVariablesTool,
    GetTemplateVariablesParameters,
)
from packages.matrices.models.schemas.matrix_template_variable import (
    MatrixTemplateVariableResponse,
)
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.matrices.models.database import MatrixTemplateVariableEntity


class TestGetTemplateVariablesTool:
    """Test GetTemplateVariablesTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return GetTemplateVariablesTool()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    def test_tool_definition(self):
        """Test tool definition is correctly configured."""
        definition = GetTemplateVariablesTool.definition()

        assert definition.name == "get_template_variables"
        assert (
            definition.description == "Get all template variables for a specific matrix"
        )
        assert "properties" in definition.parameters
        assert "matrix_id" in definition.parameters["properties"]

    def test_permissions(self):
        """Test tool has correct permissions."""

        permissions = GetTemplateVariablesTool.permissions()
        assert permissions == ToolPermission.READ

    def test_parameter_class(self):
        """Test parameter class is correctly configured."""
        param_class = GetTemplateVariablesTool.parameter_class()
        assert param_class == GetTemplateVariablesParameters

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Valid parameters
        params = GetTemplateVariablesParameters(matrix_id=123)
        assert params.matrix_id == 123

        # Invalid parameters should raise validation error
        with pytest.raises(ValueError):
            GetTemplateVariablesParameters()  # Missing required matrix_id

    def test_tool_schema_format(self):
        """Test that tool schema is in correct format for OpenAI function calling."""
        definition = GetTemplateVariablesTool.definition()

        # Check overall structure
        assert isinstance(definition.parameters, dict)
        assert "type" in definition.parameters
        assert definition.parameters["type"] == "object"
        assert "properties" in definition.parameters

        # Check matrix_id parameter
        matrix_id_param = definition.parameters["properties"]["matrix_id"]
        assert "type" in matrix_id_param
        assert "description" in matrix_id_param
        assert (
            matrix_id_param["description"]
            == "the matrix id to get template variables for"
        )


class TestGetTemplateVariablesToolIntegration:
    """Integration tests that hit real DB without mocking."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return GetTemplateVariablesTool()

    async def test_execute_with_template_variables(
        self, tool, test_db, test_user, sample_matrix, sample_company
    ):
        """Test successful tool execution with template variables in matrix."""
        # Create template variables
        var1 = MatrixTemplateVariableEntity(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            template_string="contract_date",
            value="2023-01-15",
        )
        var2 = MatrixTemplateVariableEntity(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            template_string="party_name",
            value="Acme Corporation",
        )
        var3 = MatrixTemplateVariableEntity(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            template_string="contract_value",
            value="$50,000",
        )
        test_db.add_all([var1, var2, var3])
        await test_db.commit()

        params = GetTemplateVariablesParameters(matrix_id=sample_matrix.id)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.template_variables) == 3

        for var in result.result.template_variables:
            assert isinstance(var, MatrixTemplateVariableResponse)
            assert var.matrix_id == sample_matrix.id

        template_strings = {v.template_string for v in result.result.template_variables}
        assert template_strings == {"contract_date", "party_name", "contract_value"}

        values = {v.value for v in result.result.template_variables}
        assert values == {"2023-01-15", "Acme Corporation", "$50,000"}

    async def test_execute_empty_matrix(self, tool, test_db, test_user, sample_matrix):
        """Test successful tool execution with empty matrix."""
        params = GetTemplateVariablesParameters(matrix_id=sample_matrix.id)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.template_variables) == 0

    async def test_execute_nonexistent_matrix(
        self, tool, test_db, test_user, sample_company
    ):
        """Test tool execution with nonexistent matrix returns empty result."""
        params = GetTemplateVariablesParameters(matrix_id=99999)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.template_variables) == 0

    async def test_execute_multiple_matrices(
        self, tool, test_db, test_user, sample_matrix, sample_workspace, sample_company
    ):
        """Test that each matrix has its own template variables."""

        # Create another matrix
        matrix2 = MatrixEntity(
            name="Matrix 2",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        test_db.add(matrix2)
        await test_db.commit()
        await test_db.refresh(matrix2)

        # Add variables to first matrix
        var1 = MatrixTemplateVariableEntity(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            template_string="var1",
            value="value1",
        )
        var2 = MatrixTemplateVariableEntity(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            template_string="var2",
            value="value2",
        )

        # Add different variables to second matrix
        var3 = MatrixTemplateVariableEntity(
            matrix_id=matrix2.id,
            company_id=sample_company.id,
            template_string="var3",
            value="value3",
        )

        test_db.add_all([var1, var2, var3])
        await test_db.commit()

        # Test first matrix
        params1 = GetTemplateVariablesParameters(matrix_id=sample_matrix.id)
        result1 = await tool.execute(params1, test_db, test_user)

        assert result1.error is None
        assert len(result1.result.template_variables) == 2
        template_strings = {
            v.template_string for v in result1.result.template_variables
        }
        assert template_strings == {"var1", "var2"}

        # Test second matrix
        params2 = GetTemplateVariablesParameters(matrix_id=matrix2.id)
        result2 = await tool.execute(params2, test_db, test_user)

        assert result2.error is None
        assert len(result2.result.template_variables) == 1
        assert result2.result.template_variables[0].template_string == "var3"
