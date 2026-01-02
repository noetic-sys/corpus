import pytest

from packages.agents.tools.base import ToolPermission
from packages.agents.tools.tools.get_matrix import GetMatrixTool, GetMatrixParameters
from packages.matrices.models.schemas.matrix import MatrixResponse
from packages.auth.models.domain.authenticated_user import AuthenticatedUser


class TestGetMatrixTool:
    """Test GetMatrixTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return GetMatrixTool()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    def test_tool_definition(self):
        """Test tool definition is correctly configured."""
        definition = GetMatrixTool.definition()

        assert definition.name == "get_matrix"
        assert definition.description == "Get details about a specific matrix by ID"
        assert "properties" in definition.parameters
        assert "matrix_id" in definition.parameters["properties"]

    def test_permissions(self):
        """Test tool has correct permissions."""

        permissions = GetMatrixTool.permissions()
        assert permissions == ToolPermission.READ

    def test_parameter_class(self):
        """Test parameter class is correctly configured."""
        param_class = GetMatrixTool.parameter_class()
        assert param_class == GetMatrixParameters

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Valid parameters
        params = GetMatrixParameters(matrix_id=1)
        assert params.matrix_id == 1

        # Invalid parameters should raise validation error
        with pytest.raises(ValueError):
            GetMatrixParameters()  # Missing required matrix_id

    def test_tool_schema_format(self):
        """Test that tool schema is in correct format for OpenAI function calling."""
        definition = GetMatrixTool.definition()

        # Check overall structure
        assert isinstance(definition.parameters, dict)
        assert "type" in definition.parameters
        assert definition.parameters["type"] == "object"
        assert "properties" in definition.parameters

        # Check matrix_id parameter
        matrix_id_param = definition.parameters["properties"]["matrix_id"]
        assert "type" in matrix_id_param
        assert "description" in matrix_id_param
        assert matrix_id_param["description"] == "the matrix id to retrieve"


class TestGetMatrixToolIntegration:
    """Integration tests that hit real DB without mocking."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return GetMatrixTool()

    async def test_execute_success(self, tool, test_db, test_user, sample_matrix):
        """Test successful tool execution."""
        params = GetMatrixParameters(matrix_id=sample_matrix.id)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert result.result.matrix is not None

        matrix = result.result.matrix
        assert isinstance(matrix, MatrixResponse)
        assert matrix.id == sample_matrix.id
        assert matrix.name == sample_matrix.name
        assert matrix.workspace_id == sample_matrix.workspace_id

    async def test_execute_matrix_not_found(self, tool, test_db, test_user):
        """Test tool execution when matrix is not found."""
        params = GetMatrixParameters(matrix_id=99999)
        result = await tool.execute(params, test_db, test_user)

        # Should return error for non-existent matrix
        assert result.error is not None
        assert "not found" in result.error.error.lower()
