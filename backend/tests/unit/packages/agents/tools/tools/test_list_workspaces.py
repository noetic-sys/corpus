import pytest

from packages.agents.tools.base import ToolPermission
from packages.agents.tools.tools.list_workspaces import (
    ListWorkspacesTool,
    ListWorkspacesParameters,
)
from packages.workspaces.models.schemas.workspace import WorkspaceResponse
from packages.workspaces.models.database.workspace import WorkspaceEntity


class TestListWorkspacesTool:
    """Test ListWorkspacesTool functionality."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return ListWorkspacesTool()

    def test_tool_definition(self):
        """Test tool definition is correctly configured."""
        definition = ListWorkspacesTool.definition()

        assert definition.name == "list_workspaces"
        assert definition.description == "List all workspaces in the system"
        assert "properties" in definition.parameters
        assert "limit" in definition.parameters["properties"]
        assert "skip" in definition.parameters["properties"]

    def test_permissions(self):
        """Test tool has correct permissions."""

        permissions = ListWorkspacesTool.permissions()
        assert permissions == ToolPermission.READ

    def test_parameter_class(self):
        """Test parameter class is correctly configured."""
        param_class = ListWorkspacesTool.parameter_class()
        assert param_class == ListWorkspacesParameters

    def test_parameters_validation(self):
        """Test parameter validation."""
        # Valid parameters with defaults
        params = ListWorkspacesParameters()
        assert params.limit == 50
        assert params.skip == 0

        # Valid parameters with custom values
        params_custom = ListWorkspacesParameters(limit=25, skip=10)
        assert params_custom.limit == 25
        assert params_custom.skip == 10

    def test_tool_schema_format(self):
        """Test that tool schema is in correct format for OpenAI function calling."""
        definition = ListWorkspacesTool.definition()

        # Check overall structure
        assert isinstance(definition.parameters, dict)
        assert "type" in definition.parameters
        assert definition.parameters["type"] == "object"
        assert "properties" in definition.parameters

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


class TestListWorkspacesToolIntegration:
    """Integration tests that hit real DB without mocking."""

    @pytest.fixture
    def tool(self):
        """Create tool instance."""
        return ListWorkspacesTool()

    async def test_execute_real_data(self, tool, test_db, test_user, sample_company):
        """Test successful tool execution with real database data."""
        # Create 3 workspaces in the database
        workspace1 = WorkspaceEntity(
            name="Test Workspace 1",
            description="First test workspace for integration",
            company_id=sample_company.id,
        )
        workspace2 = WorkspaceEntity(
            name="Test Workspace 2",
            description="Second test workspace",
            company_id=sample_company.id,
        )
        workspace3 = WorkspaceEntity(
            name="Test Workspace 3",
            description="Third test workspace",
            company_id=sample_company.id,
        )

        test_db.add_all([workspace1, workspace2, workspace3])
        await test_db.commit()
        await test_db.refresh(workspace1)
        await test_db.refresh(workspace2)
        await test_db.refresh(workspace3)

        # Execute tool without pagination - should get all 3
        params = ListWorkspacesParameters()
        result = await tool.execute(params, test_db, test_user)

        # Verify successful result
        assert result.error is None
        assert result.result is not None
        assert len(result.result.workspaces) == 3

        # Verify workspaces are WorkspaceResponse objects
        for workspace in result.result.workspaces:
            assert isinstance(workspace, WorkspaceResponse)
            assert workspace.company_id == sample_company.id
            assert workspace.name.startswith("Test Workspace")
            assert workspace.description is not None

        # Verify workspace names match what we created
        workspace_names = {ws.name for ws in result.result.workspaces}
        expected_names = {"Test Workspace 1", "Test Workspace 2", "Test Workspace 3"}
        assert workspace_names == expected_names

    async def test_execute_pagination(self, tool, test_db, test_user, sample_company):
        """Test tool execution with pagination parameters."""
        # Create 5 workspaces
        workspaces = []
        for i in range(1, 6):
            ws = WorkspaceEntity(
                name=f"Page Test Workspace {i}",
                description=f"Workspace for pagination test {i}",
                company_id=sample_company.id,
            )
            workspaces.append(ws)

        test_db.add_all(workspaces)
        await test_db.commit()

        # Test first page (limit=2, skip=0)
        params = ListWorkspacesParameters(limit=2, skip=0)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.workspaces) == 2

        # Test second page (skip=2, limit=2)
        params = ListWorkspacesParameters(limit=2, skip=2)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.workspaces) == 2

        # Test third page (skip=4, limit=2) - should get 1 workspace
        params = ListWorkspacesParameters(limit=2, skip=4)
        result = await tool.execute(params, test_db, test_user)

        assert result.error is None
        assert result.result is not None
        assert len(result.result.workspaces) == 1

    async def test_execute_empty_company(self, tool, test_db, test_user):
        """Test tool execution with user that has no workspaces."""
        # Don't create any workspaces, just execute
        params = ListWorkspacesParameters()
        result = await tool.execute(params, test_db, test_user)

        # Verify empty result but no error
        assert result.error is None
        assert result.result is not None
        assert len(result.result.workspaces) == 0
