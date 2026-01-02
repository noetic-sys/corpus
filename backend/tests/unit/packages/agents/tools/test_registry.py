import pytest
from packages.agents.tools.base import ToolContext
from typing import Type

from packages.agents.tools.registry import ToolRegistry
from packages.agents.tools.base import (
    Tool,
    ToolDefinition,
    ToolPermission,
    ToolParameters,
    ToolResult,
    ToolSuccessResult,
)


class MockToolParameters(ToolParameters):
    """Mock tool parameters for testing."""

    test_param: str


class MockToolSuccessResult(ToolSuccessResult):
    """Mock tool success result."""

    result: str


class MockTool(Tool[MockToolParameters]):
    """Mock tool for testing."""

    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.READ

    @classmethod
    def allowed_contexts(cls):

        return [ToolContext.GENERAL_AGENT, ToolContext.WORKFLOW_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="mock_tool",
            description="A mock tool for testing",
            parameters=MockToolParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[MockToolParameters]:
        return MockToolParameters

    async def execute(self, parameters: MockToolParameters, session) -> ToolResult:
        return ToolResult.ok(
            MockToolSuccessResult(result=f"Mock result for {parameters.test_param}")
        )


class AnotherMockTool(Tool[MockToolParameters]):
    """Another mock tool for testing."""

    @classmethod
    def permissions(cls) -> ToolPermission:
        return ToolPermission.WRITE

    @classmethod
    def allowed_contexts(cls):

        return [ToolContext.GENERAL_AGENT]

    @classmethod
    def definition(cls) -> ToolDefinition:
        return ToolDefinition(
            name="another_mock_tool",
            description="Another mock tool for testing",
            parameters=MockToolParameters.model_json_schema(),
        )

    @classmethod
    def parameter_class(cls) -> Type[MockToolParameters]:
        return MockToolParameters

    async def execute(self, parameters: MockToolParameters, session) -> ToolResult:
        return ToolResult.ok(
            MockToolSuccessResult(
                result=f"Another mock result for {parameters.test_param}"
            )
        )


class TestToolRegistry:
    """Test ToolRegistry functionality."""

    def test_registry_singleton(self):
        """Test that ToolRegistry is a singleton."""
        registry1 = ToolRegistry()
        registry2 = ToolRegistry()

        assert registry1 is registry2

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        registry.register(MockTool)

        assert "mock_tool" in registry._tools
        assert registry._tools["mock_tool"] == MockTool

    def test_register_multiple_tools(self):
        """Test registering multiple tools."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        registry.register(MockTool)
        registry.register(AnotherMockTool)

        assert len(registry._tools) == 2
        assert "mock_tool" in registry._tools
        assert "another_mock_tool" in registry._tools

    def test_get_tool_success(self):
        """Test getting a registered tool."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        registry.register(MockTool)

        retrieved_tool = registry.get_tool("mock_tool")
        assert retrieved_tool == MockTool

    def test_get_tool_not_found(self):
        """Test getting a non-existent tool raises ValueError."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        with pytest.raises(
            ValueError, match="Tool 'nonexistent' not found in registry"
        ):
            registry.get_tool("nonexistent")

    def test_get_tool_definitions(self):
        """Test getting tool definitions with permission filtering."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        registry.register(MockTool)
        registry.register(AnotherMockTool)

        # Test READ permission mode (default) - should only get READ tools
        read_definitions = registry.get_tool_definitions(permission=ToolPermission.READ)
        assert len(read_definitions) == 1
        assert read_definitions[0].name == "mock_tool"

        # Test WRITE permission mode - should get both READ and WRITE tools
        write_definitions = registry.get_tool_definitions(
            permission=ToolPermission.WRITE
        )
        assert len(write_definitions) == 2

        # Check that we get proper ToolDefinition objects
        definition_names = [d.name for d in write_definitions]
        assert "mock_tool" in definition_names
        assert "another_mock_tool" in definition_names

        # Check structure of definitions
        for definition in write_definitions:
            assert isinstance(definition, ToolDefinition)
            assert definition.name
            assert definition.description
            assert definition.parameters

    def test_get_tool_definitions_empty_registry(self):
        """Test getting tool definitions from empty registry."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        # Should return empty list regardless of permission mode
        definitions = registry.get_tool_definitions(permission=ToolPermission.READ)
        assert definitions == []

        definitions = registry.get_tool_definitions(permission=ToolPermission.WRITE)
        assert definitions == []

    def test_list_tool_names(self):
        """Test listing all registered tool names."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        registry.register(MockTool)
        registry.register(AnotherMockTool)

        names = registry.list_tool_names()

        assert len(names) == 2
        assert "mock_tool" in names
        assert "another_mock_tool" in names

    def test_list_tool_names_empty_registry(self):
        """Test listing tool names from empty registry."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        names = registry.list_tool_names()

        assert names == []

    def test_register_tool_overwrites_existing(self):
        """Test that registering a tool with the same name overwrites the previous one."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        # Register first tool
        registry.register(MockTool)
        assert registry.get_tool("mock_tool") == MockTool

        # Create a different tool with the same name
        class OverwriteMockTool(Tool[MockToolParameters]):
            @classmethod
            def permissions(cls) -> ToolPermission:
                return ToolPermission.READ

            @classmethod
            def allowed_contexts(cls):

                return [ToolContext.GENERAL_AGENT]

            @classmethod
            def definition(cls) -> ToolDefinition:
                return ToolDefinition(
                    name="mock_tool",  # Same name
                    description="Overwrite mock tool",
                    parameters=MockToolParameters.model_json_schema(),
                )

            @classmethod
            def parameter_class(cls) -> Type[MockToolParameters]:
                return MockToolParameters

            async def execute(
                self, parameters: MockToolParameters, session
            ) -> ToolResult:
                return ToolResult.ok(MockToolSuccessResult(result="Overwritten"))

        # Register tool with same name
        registry.register(OverwriteMockTool)

        # Should now return the new tool
        assert registry.get_tool("mock_tool") == OverwriteMockTool
        assert len(registry._tools) == 1

    def test_tool_definition_structure(self):
        """Test that tool definitions have the correct structure."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        registry.register(MockTool)

        definitions = registry.get_tool_definitions(permission=ToolPermission.READ)
        definition = definitions[0]

        assert definition.name == "mock_tool"
        assert definition.description == "A mock tool for testing"
        assert "properties" in definition.parameters
        assert "test_param" in definition.parameters["properties"]

    def test_registry_preserves_tool_metadata(self):
        """Test that registry preserves tool metadata correctly."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        registry.register(MockTool)
        registry.register(AnotherMockTool)

        # Get tools and check their properties
        mock_tool = registry.get_tool("mock_tool")
        another_mock_tool = registry.get_tool("another_mock_tool")

        # Check permissions are preserved
        assert mock_tool.permissions() == ToolPermission.READ
        assert another_mock_tool.permissions() == ToolPermission.WRITE

        # Check definitions are preserved
        mock_def = mock_tool.definition()
        another_def = another_mock_tool.definition()

        assert mock_def.name == "mock_tool"
        assert mock_def.description == "A mock tool for testing"
        assert another_def.name == "another_mock_tool"
        assert another_def.description == "Another mock tool for testing"

    async def test_tool_execution_through_registry(self):
        """Test executing a tool retrieved from registry."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        registry.register(MockTool)

        # Get tool class from registry
        tool_class = registry.get_tool("mock_tool")

        # Create tool instance
        tool_instance = tool_class()

        # Execute tool
        parameters = MockToolParameters(test_param="test_value")
        result = await tool_instance.execute(parameters, None)

        assert result.error is None
        assert result.result is not None
        assert result.result.result == "Mock result for test_value"

    def test_registry_internal_state_isolation(self):
        """Test that registry internal state is properly isolated."""
        registry1 = ToolRegistry()
        registry2 = ToolRegistry()

        # Since it's a singleton, they should be the same object
        assert registry1 is registry2

        # Clear and add to one
        registry1._tools.clear()
        registry1.register(MockTool)

        # Should be visible in the other (same object)
        assert "mock_tool" in registry2._tools
        assert len(registry2.list_tool_names()) == 1

    def test_tool_name_extraction_from_definition(self):
        """Test that tool names are correctly extracted from definitions."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        # Create tool with specific name in definition
        class CustomNameTool(Tool[MockToolParameters]):
            @classmethod
            def permissions(cls) -> ToolPermission:
                return ToolPermission.READ

            @classmethod
            def allowed_contexts(cls):

                return [ToolContext.GENERAL_AGENT]

            @classmethod
            def definition(cls) -> ToolDefinition:
                return ToolDefinition(
                    name="custom_tool_name",
                    description="Tool with custom name",
                    parameters=MockToolParameters.model_json_schema(),
                )

            @classmethod
            def parameter_class(cls) -> Type[MockToolParameters]:
                return MockToolParameters

            async def execute(
                self, parameters: MockToolParameters, session
            ) -> ToolResult:
                return ToolResult.ok(MockToolSuccessResult(result="custom"))

        registry.register(CustomNameTool)

        # Tool should be registered under the name from its definition
        assert "custom_tool_name" in registry._tools
        assert registry.get_tool("custom_tool_name") == CustomNameTool

        # Should not be registered under the class name
        assert "CustomNameTool" not in registry._tools

    def test_permission_filtering(self):
        """Test that tool definitions are properly filtered by permission mode."""
        registry = ToolRegistry()

        # Clear registry first
        registry._tools.clear()

        # Register tools with different permissions
        registry.register(MockTool)  # READ permission
        registry.register(AnotherMockTool)  # WRITE permission

        # READ mode should only return READ tools
        read_only_defs = registry.get_tool_definitions(permission=ToolPermission.READ)
        assert len(read_only_defs) == 1
        assert read_only_defs[0].name == "mock_tool"

        # WRITE mode should return both READ and WRITE tools
        write_mode_defs = registry.get_tool_definitions(permission=ToolPermission.WRITE)
        assert len(write_mode_defs) == 2
        write_tool_names = {d.name for d in write_mode_defs}
        assert "mock_tool" in write_tool_names
        assert "another_mock_tool" in write_tool_names
