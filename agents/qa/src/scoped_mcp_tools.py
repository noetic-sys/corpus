"""
Scoped MCP tools for agent QA execution.

Creates document-scoped versions of MCP tools that automatically restrict
searches to only the documents the agent is allowed to access.
"""

import json
from typing import List, Dict, Any
import requests
from claude_agent_sdk import create_sdk_mcp_server, tool


def create_scoped_hybrid_search_tool(
    api_endpoint: str,
    api_key: str,
    allowed_document_ids: List[int],
):
    """
    Create a scoped version of hybrid_search_chunks that automatically
    restricts searches to allowed document IDs.

    Args:
        api_endpoint: API endpoint for platform
        api_key: API key for authentication
        allowed_document_ids: List of document IDs this agent can access

    Returns:
        Tool function for hybrid search scoped to allowed documents
    """
    headers = {"Authorization": f"Bearer {api_key}"}

    @tool(
        "hybrid_search_chunks",
        "Hybrid search across chunks using BM25 + vector search. "
        "Combines keyword matching with semantic similarity to find relevant content. "
        "Automatically scoped to the documents available for this question.",
        {
            "query": str,
            "document_ids": list,  # Optional - will be intersected with allowed_document_ids
            "limit": int,
            "skip": int,
            "use_vector": bool,
        },
    )
    async def scoped_hybrid_search(args):
        """Scoped hybrid search tool that enforces document access restrictions."""
        try:
            query = args.get("query")
            if not query:
                return {
                    "content": [
                        {"type": "text", "text": "Error: query parameter is required"}
                    ],
                    "isError": True,
                }

            # Get document_ids from args (optional)
            requested_doc_ids = args.get("document_ids")

            # Scope to allowed documents
            if requested_doc_ids:
                # Intersect requested IDs with allowed IDs
                scoped_doc_ids = [
                    doc_id
                    for doc_id in requested_doc_ids
                    if doc_id in allowed_document_ids
                ]
                if not scoped_doc_ids:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: None of the requested document IDs {requested_doc_ids} are available. "
                                f"Available documents: {allowed_document_ids}",
                            }
                        ],
                        "isError": True,
                    }
            else:
                # No specific docs requested - use all allowed docs
                scoped_doc_ids = allowed_document_ids

            # Build query parameters
            params = {
                "query": query,
                "document_ids": scoped_doc_ids,
                "limit": args.get("limit", 10),
                "skip": args.get("skip", 0),
                "use_vector": args.get("use_vector", True),
            }

            # Make request to hybrid search endpoint
            url = f"{api_endpoint}/api/v1/chunks/search"
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Format response for agent
            chunks = data.get("chunks", [])
            total_count = data.get("total_count", 0)
            has_more = data.get("has_more", False)

            result_text = f"Found {total_count} chunks matching '{query}'\n"
            result_text += (
                f"Searched in documents: {scoped_doc_ids}\n"
                if len(scoped_doc_ids) < len(allowed_document_ids)
                else f"Searched in all {len(allowed_document_ids)} available documents\n"
            )
            result_text += f"Showing {len(chunks)} results (has_more: {has_more})\n\n"

            for i, chunk in enumerate(chunks, 1):
                result_text += f"--- Result {i} (score: {chunk['score']:.3f}) ---\n"
                result_text += f"Document ID: {chunk['document_id']}\n"
                result_text += f"Chunk ID: {chunk['chunk_id']}\n"
                result_text += f"Content:\n{chunk['content']}\n"
                if chunk.get("metadata"):
                    result_text += f"Metadata: {json.dumps(chunk['metadata'], indent=2)}\n"
                result_text += "\n"

            return {"content": [{"type": "text", "text": result_text}]}

        except requests.HTTPError as e:
            error_msg = f"HTTP error calling hybrid search: {e.response.status_code}"
            if e.response.text:
                error_msg += f"\n{e.response.text}"
            return {
                "content": [{"type": "text", "text": error_msg}],
                "isError": True,
            }
        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error calling hybrid search: {str(e)}"}
                ],
                "isError": True,
            }

    return scoped_hybrid_search


def create_scoped_hybrid_search_server(
    api_endpoint: str,
    api_key: str,
    allowed_document_ids: List[int],
) -> tuple[Dict[str, Any], List[str]]:
    """
    Create MCP server with ONLY the scoped hybrid_search_chunks tool.

    Args:
        api_endpoint: API endpoint for platform
        api_key: API key for authentication
        allowed_document_ids: List of document IDs this agent can access

    Returns:
        Tuple of (MCP server config, list of tool names)
    """
    # Create scoped hybrid search tool
    scoped_search_tool = create_scoped_hybrid_search_tool(
        api_endpoint=api_endpoint,
        api_key=api_key,
        allowed_document_ids=allowed_document_ids,
    )

    # Create MCP server with just this one tool
    server = create_sdk_mcp_server(
        name="scoped_search", version="1.0.0", tools=[scoped_search_tool]
    )

    # Tool name is what we passed to @tool decorator
    tool_name = "mcp__hybrid_search_chunks"

    print(f"Created scoped hybrid search server")
    print(f"  - Tool: {tool_name}")
    print(f"  - Scoped to documents: {allowed_document_ids}")

    return server, [tool_name]
