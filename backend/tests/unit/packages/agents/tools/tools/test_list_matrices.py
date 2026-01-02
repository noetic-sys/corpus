import pytest
from packages.workspaces.models.database.workspace import WorkspaceEntity

from packages.agents.tools.base import ToolPermission
from packages.agents.tools.tools.list_matrices import (
    ListMatricesTool,
    ListMatricesParameters,
)
from packages.matrices.models.schemas.matrix import MatrixListResponse
from packages.matrices.models.database.matrix import MatrixEntity
from packages.auth.models.domain.authenticated_user import AuthenticatedUser


class TestListMatricesTool:
    """Test ListMatricesTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return ListMatricesTool()

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return AuthenticatedUser(company_id=1, user_id=1)

    def test_tool_definition(self):
        """Test tool definition is correctly configured."""
        definition = ListMatricesTool.definition()

        assert definition.name == "list_matrices"
        assert definition.description == "List matrices for a specific workspace"
        assert "properties" in definition.parameters
        assert "workspace_id" in definition.parameters["properties"]
        assert "limit" in definition.parameters["properties"]
        assert "skip" in definition.parameters["properties"]

    def test_permissions(self):
        """Test tool has correct permissions."""

        permissions = ListMatricesTool.permissions()
        assert permissions == ToolPermission.READ

    def test_parameter_class(self):
        """Test parameter class is correctly configured."""
        param_class = ListMatricesTool.parameter_class()
        assert param_class == ListMatricesParameters

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Valid parameters with all fields
        params = ListMatricesParameters(workspace_id=1, limit=10, skip=0)
        assert params.workspace_id == 1
        assert params.limit == 10
        assert params.skip == 0

        # Valid parameters with defaults
        params_default = ListMatricesParameters(workspace_id=1)
        assert params_default.workspace_id == 1
        assert params_default.limit == 50
        assert params_default.skip == 0

        # Invalid parameters should raise validation error
        with pytest.raises(ValueError):
            ListMatricesParameters()  # Missing required workspace_id

    def test_tool_schema_format(self):
        """Test that tool schema is in correct format for OpenAI function calling."""
        definition = ListMatricesTool.definition()

        # Check overall structure
        assert isinstance(definition.parameters, dict)
        assert "type" in definition.parameters
        assert definition.parameters["type"] == "object"
        assert "properties" in definition.parameters

        # Check workspace_id parameter (required)
        workspace_param = definition.parameters["properties"]["workspace_id"]
        assert "type" in workspace_param
        assert "description" in workspace_param
        assert workspace_param["description"] == "workspace id to get matrices for"

        # Check limit parameter
        limit_param = definition.parameters["properties"]["limit"]
        assert "type" in limit_param
        assert "description" in limit_param
        assert limit_param["default"] == 50

        # Check skip parameter
        skip_param = definition.parameters["properties"]["skip"]
        assert "type" in skip_param
        assert "description" in skip_param
        assert skip_param["default"] == 0


class TestListMatricesToolIntegration:
    """Integration tests that hit real DB without mocking."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return ListMatricesTool()

    async def test_execute_with_workspace_matrices(
        self, tool, test_db, test_user, sample_company
    ):
        """Test successful tool execution with matrices in workspace."""
        # Create workspace

        workspace_a = WorkspaceEntity(
            name="Workspace A",
            description="First workspace",
            company_id=sample_company.id,
        )
        test_db.add(workspace_a)
        await test_db.commit()
        await test_db.refresh(workspace_a)

        # Create 2 matrices in workspace A
        matrix1 = MatrixEntity(
            name="Matrix A1",
            description="First matrix in workspace A",
            workspace_id=workspace_a.id,
            company_id=sample_company.id,
        )
        matrix2 = MatrixEntity(
            name="Matrix A2",
            description="Second matrix in workspace A",
            workspace_id=workspace_a.id,
            company_id=sample_company.id,
        )
        test_db.add_all([matrix1, matrix2])
        await test_db.commit()

        # Execute tool with workspace_id - should get 2 matrices
        params = ListMatricesParameters(workspace_id=workspace_a.id)
        result = await tool.execute(params, test_db, test_user)

        # Verify successful result
        assert result.error is None
        assert result.result is not None
        assert len(result.result.matrices) == 2

        # Verify matrices are MatrixListResponse objects
        for matrix in result.result.matrices:
            assert isinstance(matrix, MatrixListResponse)
            assert matrix.company_id == sample_company.id
            assert matrix.workspace_id == workspace_a.id

        # Verify all matrix names are present
        matrix_names = {m.name for m in result.result.matrices}
        expected_names = {"Matrix A1", "Matrix A2"}
        assert matrix_names == expected_names

    async def test_execute_empty_workspace(
        self, tool, test_db, test_user, sample_company
    ):
        """Test successful tool execution with empty workspace."""
        # Create empty workspace

        empty_workspace = WorkspaceEntity(
            name="Empty Workspace",
            description="Workspace with no matrices",
            company_id=sample_company.id,
        )
        test_db.add(empty_workspace)
        await test_db.commit()
        await test_db.refresh(empty_workspace)

        # Execute tool with empty workspace_id
        params = ListMatricesParameters(workspace_id=empty_workspace.id)
        result = await tool.execute(params, test_db, test_user)

        # Verify empty result but no error
        assert result.error is None
        assert result.result is not None
        assert len(result.result.matrices) == 0
        assert result.result.total_count == 0

    async def test_execute_pagination(
        self, tool, test_db, test_user, sample_workspace, sample_company
    ):
        """Test tool execution with pagination parameters."""
        # Create 5 matrices in the same workspace
        matrices = []
        for i in range(1, 6):
            matrix = MatrixEntity(
                name=f"Pagination Matrix {i}",
                description=f"Matrix {i} for pagination test",
                workspace_id=sample_workspace.id,
                company_id=sample_company.id,
            )
            matrices.append(matrix)

        test_db.add_all(matrices)
        await test_db.commit()

        # Test first page (limit=2, skip=0)
        params = ListMatricesParameters(
            workspace_id=sample_workspace.id, limit=2, skip=0
        )
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.matrices) == 2
        assert result.result.total_count == 2

        # Test pagination with skip
        params = ListMatricesParameters(
            workspace_id=sample_workspace.id, limit=2, skip=2
        )
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.matrices) == 2
        assert result.result.total_count == 2

    async def test_execute_nonexistent_workspace(
        self, tool, test_db, test_user, sample_company
    ):
        """Test tool execution with nonexistent workspace returns empty result."""
        # Don't create any matrices, just test with nonexistent workspace ID
        params = ListMatricesParameters(workspace_id=99999)
        result = await tool.execute(params, test_db, test_user)

        # Verify empty result but no error
        assert result.error is None
        assert result.result is not None
        assert len(result.result.matrices) == 0
        assert result.result.total_count == 0
