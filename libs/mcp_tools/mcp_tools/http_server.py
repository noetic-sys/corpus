"""
HTTP MCP server for Corpus, generated from the bundled OpenAPI spec via FastMCP.

Exposes product API capabilities as MCP tools over Streamable HTTP so external
models can call the real Corpus REST API (auth forwarded as X-API-Key or Bearer).
"""

from __future__ import annotations

import os
from typing import Any, Iterable, Optional, Sequence, Set

import httpx2
from fastmcp import FastMCP
from fastmcp.server.providers.openapi import MCPType, RouteMap

from mcp_tools.openapi_mcp_generator import (
    _load_openapi_spec,
    _scope_spec_to_workspace,
)

# OpenAPI tags that represent meaningful product surface for model clients.
DEFAULT_INCLUDE_TAGS: Set[str] = {
    "workspaces",
    "documents",
    "chunks",
    "questions",
    "question-types",
    "matrices",
    "matrix-template-variables",
    "entity-sets",
    "workflows",
    "document-extraction",
    "ai-selection",
    "agents",
    "protected",
    "billing",
    # Endpoints tagged for in-product agents; still real product reads/writes.
    "workflow-agent",
    "workflow_agent",
}

# Internal / non-product routes that should never be model-callable.
DEFAULT_EXCLUDE_TAGS: Set[str] = {
    "webhooks",  # Stripe signature verification; not a client API
    "execution-uploads",  # Workflow agent service-account uploads
    "qa",  # Agent QA answer upload + internal queue triggers
    "health",  # Probe noise
    "ai-models-admin",  # Admin catalog, not end-user product
}


def _short_tool_name(operation_id: str) -> str:
    """Prefer the semantic prefix before FastAPI's `_api_v1_` suffix."""
    if "_api_v1_" in operation_id:
        return operation_id.split("_api_v1_", 1)[0]
    return operation_id


def _build_mcp_names(openapi_spec: dict[str, Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for path_item in openapi_spec.get("paths", {}).values():
        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            if not isinstance(operation, dict):
                continue
            operation_id = operation.get("operationId")
            if operation_id:
                names[operation_id] = _short_tool_name(operation_id)
    return names


def _make_route_map_fn(
    include_tags: Set[str],
    exclude_tags: Set[str],
    exclude_operation_ids: Set[str],
):
    def route_map_fn(route, mcp_type: MCPType) -> MCPType | None:
        tags = set(getattr(route, "tags", None) or [])
        operation_id = getattr(route, "operation_id", None) or ""

        if operation_id in exclude_operation_ids:
            return MCPType.EXCLUDE
        if tags & exclude_tags:
            return MCPType.EXCLUDE
        if not (tags & include_tags):
            return MCPType.EXCLUDE

        # Billing: expose read/status/usage tools only (checkout/portal need a browser).
        if "billing" in tags and str(getattr(route, "method", "")).upper() != "GET":
            return MCPType.EXCLUDE

        return MCPType.TOOL

    return route_map_fn


def create_http_mcp_server(
    *,
    api_endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    bearer_token: Optional[str] = None,
    workspace_id: Optional[int] = None,
    include_tags: Optional[Iterable[str]] = None,
    exclude_tags: Optional[Iterable[str]] = None,
    exclude_operation_ids: Optional[Sequence[str]] = None,
    openapi_spec: Optional[dict[str, Any]] = None,
    name: str = "Corpus",
    timeout: float = 60.0,
) -> FastMCP:
    """
    Build a FastMCP server that proxies curated Corpus OpenAPI routes as tools.

    Auth is forwarded to the Corpus API:
    - Prefer ``api_key`` → ``X-API-Key`` (service account ``sa_...`` keys)
    - Else ``bearer_token`` → ``Authorization: Bearer ...`` (Firebase SSO)

    Args:
        api_endpoint: Corpus API base URL (default ``CORPUS_API_ENDPOINT`` or
            ``http://localhost:8000``).
        api_key: Service-account API key (default ``CORPUS_API_KEY``).
        bearer_token: SSO bearer token (default ``CORPUS_BEARER_TOKEN``).
        workspace_id: If set, hardcodes ``{workspaceId}`` into OpenAPI paths
            (same scoping used by in-process agent MCP tools).
        include_tags / exclude_tags: Override the default product allow/deny lists.
        exclude_operation_ids: Extra operationIds to drop.
        openapi_spec: Optional preloaded OpenAPI dict; otherwise uses the bundled spec.
        name: MCP server name.
        timeout: HTTP timeout seconds for upstream Corpus calls.
    """
    api_endpoint = (
        api_endpoint
        or os.environ.get("CORPUS_API_ENDPOINT")
        or os.environ.get("API_ENDPOINT")
        or "http://localhost:8000"
    ).rstrip("/")
    api_key = api_key if api_key is not None else os.environ.get("CORPUS_API_KEY")
    bearer_token = (
        bearer_token
        if bearer_token is not None
        else os.environ.get("CORPUS_BEARER_TOKEN")
    )

    if workspace_id is None:
        raw_workspace = os.environ.get("CORPUS_MCP_WORKSPACE_ID")
        if raw_workspace:
            workspace_id = int(raw_workspace)

    headers: dict[str, str] = {"Accept": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    elif bearer_token:
        headers["Authorization"] = f"Bearer {bearer_token}"

    spec = openapi_spec or _load_openapi_spec()
    if workspace_id is not None:
        spec = _scope_spec_to_workspace(spec, workspace_id)

    include = set(include_tags) if include_tags is not None else set(DEFAULT_INCLUDE_TAGS)
    exclude = set(exclude_tags) if exclude_tags is not None else set(DEFAULT_EXCLUDE_TAGS)
    excluded_ops = set(exclude_operation_ids or ())

    client = httpx2.AsyncClient(
        base_url=api_endpoint,
        headers=headers,
        timeout=timeout,
    )

    return FastMCP.from_openapi(
        openapi_spec=spec,
        client=client,
        name=name,
        # Force explicit allowlisting; do not fall through to "all routes = tools".
        route_maps=[RouteMap(mcp_type=MCPType.EXCLUDE)],
        route_map_fn=_make_route_map_fn(include, exclude, excluded_ops),
        mcp_names=_build_mcp_names(spec),
        validate_output=False,
    )


def run_http_mcp_server(
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    path: Optional[str] = None,
    **server_kwargs: Any,
) -> None:
    """Create and run the Corpus MCP server over Streamable HTTP."""
    host = host or os.environ.get("CORPUS_MCP_HOST", "0.0.0.0")
    port = port if port is not None else int(os.environ.get("CORPUS_MCP_PORT", "8100"))
    path = path or os.environ.get("CORPUS_MCP_PATH", "/mcp")

    mcp = create_http_mcp_server(**server_kwargs)
    mcp.run(transport="http", host=host, port=port, path=path)
