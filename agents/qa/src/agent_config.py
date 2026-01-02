"""
Agent configuration for QA execution.

Configures MCP tools for chunk-based document reading.
"""

from typing import List, Tuple

from claude_agent_sdk import ClaudeAgentOptions
from mcp_tools.openapi_mcp_generator import create_mcp_tools_from_openapi
from scoped_mcp_tools import create_scoped_hybrid_search_server


def create_agent_options(
    api_endpoint: str,
    api_key: str,
    company_id: int,
    document_ids: List[int],
) -> Tuple[ClaudeAgentOptions, List[str]]:
    """
    Create agent options with MCP tools for chunk reading.

    Args:
        api_endpoint: API endpoint for platform
        api_key: Service account API key
        company_id: Company ID (used as scope instead of workspace_id)
        document_ids: List of document IDs to scope search tools to

    Returns:
        Tuple of (ClaudeAgentOptions, list of MCP tool names)

    Raises:
        Exception: If MCP server creation fails
    """
    # Auto-generate base MCP tools from OpenAPI spec
    # Use "workflow-agent" tag which includes chunk reading endpoints
    base_server, base_tool_names = create_mcp_tools_from_openapi(
        api_endpoint=api_endpoint,
        api_key=api_key,
        tags_to_include=["workflow-agent"],  # Chunk endpoints have this tag
        whitelist_post_operations=[],  # Agent QA only needs GET operations
        workspace_id=None,  # Not workspace-scoped
    )

    if not base_server:
        raise ValueError("Failed to generate base MCP tools from OpenAPI spec")

    # Create a second MCP server with just the scoped hybrid search tool
    scoped_server, scoped_tool_name = create_scoped_hybrid_search_server(
        api_endpoint=api_endpoint,
        api_key=api_key,
        allowed_document_ids=document_ids,
    )

    # Remove hybrid_search_chunks from base tools (if it exists) since we're replacing it
    filtered_tool_names = [
        name for name in base_tool_names if not name.endswith("hybrid_search_chunks")
    ]

    # Combine: base tools + scoped search tool
    all_tool_names = filtered_tool_names + scoped_tool_name

    # Configure agent options with BOTH servers
    options = ClaudeAgentOptions(
        allowed_tools=all_tool_names,
        permission_mode="bypassPermissions",  # Bypass all permission checks
        mcp_servers={
            "platform": base_server,
            "scoped": scoped_server,
        },
    )

    return options, all_tool_names
