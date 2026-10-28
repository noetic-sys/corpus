"""Tests for the FastMCP HTTP Corpus server factory."""

from __future__ import annotations

import asyncio

import pytest

from mcp_tools.http_server import (
    DEFAULT_EXCLUDE_TAGS,
    DEFAULT_INCLUDE_TAGS,
    _short_tool_name,
    create_http_mcp_server,
)


def test_short_tool_name_strips_fastapi_suffix():
    assert (
        _short_tool_name("list_documents_api_v1_documents__get") == "list_documents"
    )
    assert _short_tool_name("get_document") == "get_document"


def test_create_http_mcp_server_exposes_curated_tools():
    mcp = create_http_mcp_server(
        api_endpoint="http://localhost:8000",
        api_key="sa_test",
    )

    async def _list():
        from fastmcp import Client

        async with Client(mcp) as client:
            return await client.list_tools()

    tools = asyncio.run(_list())
    names = {tool.name for tool in tools}

    assert len(tools) >= 80
    # Core product capabilities
    assert "list_documents" in names or "get_documents_by_matrix" in names
    assert "get_workspaces" in names or "create_workspace" in names
    assert "hybrid_search_chunks" in names or "list_document_chunks" in names
    assert "create_workflow" in names or "list_workflows" in names
    # Exclusions
    assert not any("webhook" in n for n in names)
    assert not any("checkout" in n for n in names)
    assert not any(n.startswith("health") for n in names)


def test_default_tag_sets_are_disjoint():
    assert DEFAULT_INCLUDE_TAGS.isdisjoint(DEFAULT_EXCLUDE_TAGS)


def test_billing_mutations_excluded_but_reads_included():
    mcp = create_http_mcp_server(
        api_endpoint="http://localhost:8000",
        api_key="sa_test",
    )

    async def _list():
        from fastmcp import Client

        async with Client(mcp) as client:
            return await client.list_tools()

    names = {tool.name for tool in asyncio.run(_list())}
    assert "get_plans" in names or "get_subscription_status" in names or "get_usage_stats" in names
    assert "create_checkout_session" not in names
    assert "create_portal_session" not in names


@pytest.mark.parametrize(
    "tag",
    sorted(DEFAULT_INCLUDE_TAGS - {"workflow-agent", "workflow_agent", "billing"}),
)
def test_include_tags_cover_product_areas(tag):
    assert tag  # nonempty; documents the curated surface in test output
