from typing import Dict, Type, List
from packages.agents.tools.base import Tool, ToolDefinition, ToolContext, ToolPermission
from packages.agents.tools.tools.list_question_types import ListQuestionTypesTool
from packages.agents.tools.tools.list_questions import ListQuestionsTool
from packages.agents.tools.tools.get_matrix import GetMatrixTool
from packages.agents.tools.tools.list_matrices import ListMatricesTool
from packages.agents.tools.tools.list_documents import ListDocumentsTool
from packages.agents.tools.tools.get_matrix_documents import GetMatrixDocumentsTool
from packages.agents.tools.tools.list_workspaces import ListWorkspacesTool
from packages.agents.tools.tools.get_matrix_cells import GetMatrixCellsTool
from packages.agents.tools.tools.get_template_variables import GetTemplateVariablesTool
from packages.agents.tools.tools.create_matrix import CreateMatrixTool
from packages.agents.tools.tools.update_matrix import UpdateMatrixTool
from packages.agents.tools.tools.create_question import CreateQuestionTool
from packages.agents.tools.tools.update_question import UpdateQuestionTool
from packages.agents.tools.tools.get_matrix_entity_sets import GetMatrixEntitySetsTool
from packages.agents.tools.tools.get_matrix_cells_by_slice import (
    GetMatrixCellsBySliceTool,
)
from packages.agents.tools.tools.search import SearchTool
from packages.agents.tools.tools.get_page_content import GetPageContentTool
from packages.agents.tools.tools.add_urls_as_documents import AddUrlsAsDocumentsTool


class ToolRegistry:
    """Singleton registry for managing available tools."""

    _instance = None
    _tools: Dict[str, Type[Tool]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
        return cls._instance

    def register(self, tool_class: Type[Tool]) -> None:
        """Register a tool class in the registry."""
        tool_name = tool_class.definition().name
        self._tools[tool_name] = tool_class

    def get_tool(self, name: str) -> Type[Tool]:
        """Get a tool class by name."""
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found in registry")
        return self._tools[name]

    def get_tool_definitions(
        self,
        context: ToolContext = ToolContext.GENERAL_AGENT,
        permission: ToolPermission = ToolPermission.READ,
    ) -> List[ToolDefinition]:
        """Get tool definitions for a specific context and permission level.

        Args:
            context: The context to filter tools by.
                     GENERAL_AGENT: All tools (read + business write)
                     WORKFLOW_AGENT: Read tools + file operation tools only
            permission: Permission level for this request.
                        READ: Only include READ permission tools (safe default)
                        WRITE: Include both READ and WRITE permission tools
        """
        definitions = []
        for tool_class in self._tools.values():
            # Check if tool is allowed in this context
            if context not in tool_class.allowed_contexts():
                continue

            # Check permission level
            tool_permission = tool_class.permissions()
            # If permission is READ, only include READ tools
            # If permission is WRITE, include both READ and WRITE tools
            if (
                permission == ToolPermission.READ
                and tool_permission == ToolPermission.WRITE
            ):
                continue

            definitions.append(tool_class.definition())
        return definitions

    def list_tool_names(self) -> List[str]:
        """Get list of all registered tool names."""
        return list(self._tools.keys())


# Global registry instance
registry = ToolRegistry()

# Register built-in tools
registry.register(ListQuestionsTool)
registry.register(GetMatrixTool)
registry.register(ListMatricesTool)
registry.register(ListDocumentsTool)
registry.register(GetMatrixDocumentsTool)
registry.register(ListWorkspacesTool)
registry.register(GetMatrixCellsTool)
registry.register(GetTemplateVariablesTool)
registry.register(CreateMatrixTool)
registry.register(UpdateMatrixTool)
registry.register(CreateQuestionTool)
registry.register(UpdateQuestionTool)
registry.register(ListQuestionTypesTool)
registry.register(GetMatrixEntitySetsTool)
registry.register(GetMatrixCellsBySliceTool)
registry.register(SearchTool)
registry.register(GetPageContentTool)
registry.register(AddUrlsAsDocumentsTool)
