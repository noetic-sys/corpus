# mcp-tools

Shared MCP utilities for Corpus.

1. **In-process Claude Agent SDK tools** (`openapi_mcp_generator`) — used by workflow/QA agents inside the product.
2. **HTTP MCP server** (`http_server`) — Streamable HTTP surface so external models can call Corpus product APIs.

## HTTP MCP server

Built with [FastMCP](https://gofastmcp.com/) (`FastMCP.from_openapi`) against the bundled OpenAPI spec (`mcp_tools/openapi.json`). Tools proxy the real Corpus REST API; they do not invent endpoints.

### What is exposed

Product tags are allowlisted as MCP tools (create/read/update/delete where the API supports it):

| Area | OpenAPI tags |
|------|----------------|
| Workspaces | `workspaces` |
| Documents & chunks | `documents`, `chunks` |
| Matrices / Q&A grid | `matrices`, `matrix-template-variables`, `entity-sets`, `questions`, `question-types` |
| Workflows | `workflows` |
| Extraction status | `document-extraction` |
| Model catalog | `ai-selection` |
| In-app agent chats | `agents` |
| Profile | `protected` |
| Billing (reads only) | `billing` GET |

**Excluded by design**

- `webhooks` (Stripe)
- `execution-uploads` (workflow agent service-account uploads)
- `qa` (agent answer upload / internal queue)
- `health`
- `ai-models-admin`
- Billing mutations (`checkout`, `portal`, `upgrade`, `cancel`) — browser/Stripe flows

Regenerate the bundled spec after API changes with `scripts/generate-client.sh`.

### Auth

The MCP server forwards credentials to Corpus:

| Env | Header |
|-----|--------|
| `CORPUS_API_KEY` | `X-API-Key` (service account `sa_...`) |
| `CORPUS_BEARER_TOKEN` | `Authorization: Bearer ...` (Firebase SSO) |

API key wins if both are set. Corpus still enforces subscription/auth on each call.

### Run

```bash
cd libs/mcp_tools
poetry install

export CORPUS_API_ENDPOINT=http://localhost:8000
export CORPUS_API_KEY=sa_your_key

# Streamable HTTP (default): http://localhost:8100/mcp
poetry run corpus-mcp

# Or
poetry run python -m mcp_tools --host 0.0.0.0 --port 8100 --path /mcp

# Inventory tools without serving
poetry run corpus-mcp --list-tools
```

Optional:

| Env / flag | Purpose |
|------------|---------|
| `CORPUS_MCP_HOST` / `--host` | Bind host (default `0.0.0.0`) |
| `CORPUS_MCP_PORT` / `--port` | Port (default `8100`) |
| `CORPUS_MCP_PATH` / `--path` | Path (default `/mcp`) |
| `CORPUS_MCP_WORKSPACE_ID` / `--workspace-id` | Hard-scope `{workspaceId}` paths |
| `--transport stdio` | Local STDIO instead of HTTP |

Docker Compose service `corpus-mcp` (when the stack is up):

```bash
docker-compose up corpus-mcp
```

### Connect a client

Point an MCP client at the Streamable HTTP endpoint:

```text
http://localhost:8100/mcp
```

Example with FastMCP's client:

```python
import asyncio
from fastmcp import Client

async def main():
    async with Client("http://localhost:8100/mcp") as client:
        for tool in await client.list_tools():
            print(tool.name)

asyncio.run(main())
```

Cursor / Claude Desktop style remote MCP config (illustrative):

```json
{
  "mcpServers": {
    "corpus": {
      "url": "http://localhost:8100/mcp"
    }
  }
}
```

Upstream Corpus auth is configured on the **server** via env (not per MCP client header) in this first cut.

## In-process generator (agents)

```python
from mcp_tools import create_mcp_tools_from_openapi

server, tool_names = create_mcp_tools_from_openapi(
    api_endpoint="http://backend:8000",
    api_key="sa_...",
    tags_to_include=["workflow-agent"],
    workspace_id=123,
)
```

Used by `agents/workflow` and `agents/qa` with the Claude Agent SDK.
