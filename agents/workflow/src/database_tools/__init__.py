"""
Database tools package for workflow agents.

Provides SQLite (relational) and Kuzu (graph) database capabilities.
"""

from typing import List, Tuple

from claude_agent_sdk import create_sdk_mcp_server

from database_tools import kuzu_tools, sqlite_tools


def create_database_mcp_server() -> Tuple[dict, List[str]]:
    """
    Create MCP server with SQLite and Kuzu database tools.

    Returns:
        Tuple of (MCP server config, list of tool names for allowed_tools)
    """
    # Combine tools from both modules
    tools = sqlite_tools.get_tools() + kuzu_tools.get_tools()

    # Generate tool names with mcp__ prefix
    # The tool names are defined in the @tool decorator's first parameter
    tool_names = [
        "mcp__sqlite_execute",
        "mcp__sqlite_get_schema",
        "mcp__kuzu_execute",
        "mcp__kuzu_get_schema",
    ]

    # Create MCP server
    server = create_sdk_mcp_server(name="databases", version="1.0.0", tools=tools)

    return server, tool_names
