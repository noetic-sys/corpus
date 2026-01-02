"""
Agent configuration setup.

Handles MCP server creation and ClaudeAgentOptions configuration.
"""

from typing import List, Tuple

from claude_agent_sdk import ClaudeAgentOptions
from mcp_tools.openapi_mcp_generator import create_mcp_tools_from_openapi

from database_tools import create_database_mcp_server


def create_agent_options(
    api_endpoint: str,
    api_key: str,
    workspace_id: int,
    tags_to_include: List[str] = None,
    whitelist_post_operations: List[str] = None,
) -> Tuple[ClaudeAgentOptions, List[str]]:
    """
    Create agent options with MCP server and tool configuration.

    Args:
        api_endpoint: API endpoint for platform
        api_key: Service account API key
        workspace_id: Workspace ID to scope all tools to
        tags_to_include: OpenAPI tags to include in MCP tools
        whitelist_post_operations: POST operations to allow (others are GET only)

    Returns:
        Tuple of (ClaudeAgentOptions, list of MCP tool names)

    Raises:
        Exception: If MCP server creation fails
    """
    # Auto-generate platform MCP server from OpenAPI spec
    platform_mcp_server, mcp_tool_names = create_mcp_tools_from_openapi(
        api_endpoint=api_endpoint,
        api_key=api_key,
        tags_to_include=tags_to_include or ["workflow-agent"],
        whitelist_post_operations=whitelist_post_operations
        or ["get_matrix_cells_batch"],
        workspace_id=workspace_id,
    )

    if not platform_mcp_server or not mcp_tool_names:
        raise ValueError("Failed to generate MCP tools from OpenAPI spec")

    # Create database MCP server (SQLite + Kuzu)
    database_mcp_server, database_tool_names = create_database_mcp_server()
    print(f"Generated {len(database_tool_names)} database tools (SQLite + Kuzu)")

    # Configure agent options
    base_tools = ["Read", "Write", "Edit", "Bash", "Glob"]
    all_mcp_tools = mcp_tool_names + database_tool_names

    options = ClaudeAgentOptions(
        allowed_tools=base_tools + all_mcp_tools,
        permission_mode="bypassPermissions",  # Bypass all permission checks for MCP tools
        cwd="/workspace",
        setting_sources=[
            "user",
            "local",
        ],  # Include "user" to load skills from ~/.claude/skills
        mcp_servers={
            "platform": platform_mcp_server,
            "databases": database_mcp_server,
        },
    )

    return options, all_mcp_tools
