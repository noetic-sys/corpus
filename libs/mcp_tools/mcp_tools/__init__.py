"""MCP tools generation from OpenAPI specs."""

from mcp_tools.openapi_mcp_generator import create_mcp_tools_from_openapi

__all__ = [
    "create_mcp_tools_from_openapi",
    "create_http_mcp_server",
]


def __getattr__(name: str):
    # Lazy import so agent runtimes that only need the Claude SDK generator
    # do not require FastMCP/httpx2 at import time.
    if name == "create_http_mcp_server":
        from mcp_tools.http_server import create_http_mcp_server

        return create_http_mcp_server
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
