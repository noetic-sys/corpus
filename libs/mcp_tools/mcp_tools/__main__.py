"""CLI entrypoint: ``python -m mcp_tools`` or ``corpus-mcp``."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

from mcp_tools.http_server import create_http_mcp_server, run_http_mcp_server


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="corpus-mcp",
        description=(
            "Run an HTTP MCP server that exposes Corpus product APIs as tools. "
            "Proxies the bundled OpenAPI surface to CORPUS_API_ENDPOINT."
        ),
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("CORPUS_MCP_HOST", "0.0.0.0"),
        help="Bind host (default: CORPUS_MCP_HOST or 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("CORPUS_MCP_PORT", "8100")),
        help="Bind port (default: CORPUS_MCP_PORT or 8100)",
    )
    parser.add_argument(
        "--path",
        default=os.environ.get("CORPUS_MCP_PATH", "/mcp"),
        help="MCP HTTP path (default: CORPUS_MCP_PATH or /mcp)",
    )
    parser.add_argument(
        "--api-endpoint",
        default=None,
        help="Corpus API base URL (default: CORPUS_API_ENDPOINT or http://localhost:8000)",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Service-account API key for X-API-Key (default: CORPUS_API_KEY)",
    )
    parser.add_argument(
        "--bearer-token",
        default=None,
        help="SSO bearer token (default: CORPUS_BEARER_TOKEN); used if no API key",
    )
    parser.add_argument(
        "--workspace-id",
        type=int,
        default=None,
        help="Optional workspace scope (default: CORPUS_MCP_WORKSPACE_ID)",
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="Print generated tool names and exit (does not start the HTTP server)",
    )
    parser.add_argument(
        "--transport",
        choices=("http", "stdio"),
        default="http",
        help="MCP transport (default: http Streamable HTTP)",
    )
    return parser


async def _list_tools(**server_kwargs) -> int:
    from fastmcp import Client

    mcp = create_http_mcp_server(**server_kwargs)
    async with Client(mcp) as client:
        tools = await client.list_tools()
    for tool in sorted(tools, key=lambda t: t.name):
        description = (tool.description or "").splitlines()[0] if tool.description else ""
        print(f"{tool.name}\t{description}")
    print(f"\n{len(tools)} tools", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    server_kwargs = {
        "api_endpoint": args.api_endpoint,
        "api_key": args.api_key,
        "bearer_token": args.bearer_token,
        "workspace_id": args.workspace_id,
    }

    if args.list_tools:
        return asyncio.run(_list_tools(**server_kwargs))

    if args.transport == "stdio":
        mcp = create_http_mcp_server(**server_kwargs)
        mcp.run(transport="stdio")
        return 0

    run_http_mcp_server(
        host=args.host,
        port=args.port,
        path=args.path,
        **server_kwargs,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
