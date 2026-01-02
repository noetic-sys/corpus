"""
Auto-generate MCP tools from OpenAPI specification.

This allows dynamic creation of API tools without manual editing.
"""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from claude_agent_sdk import create_sdk_mcp_server, tool


def create_mcp_tools_from_openapi(
    api_endpoint: str,
    api_key: str,
    tags_to_include: List[str] = None,
    whitelist_post_operations: List[str] = None,
    workspace_id: Optional[int] = None,
) -> tuple[dict, List[str]]:
    """
    Fetch OpenAPI spec and auto-generate MCP tools for tagged endpoints.

    Only includes GET endpoints by default, plus whitelisted POST operations.

    Args:
        api_endpoint: Base URL for the API
        api_key: API key for authentication
        tags_to_include: List of OpenAPI tags to include (e.g., ["workflows", "matrices"])
                        If None, includes all endpoints
        whitelist_post_operations: List of operationIds to allow POST requests for
                                  (e.g., ["get_matrix_cells_batch"])
        workspace_id: Optional workspace ID to scope all tools to. If provided, hardcodes
                     workspace_id into paths and removes it from parameters.

    Returns:
        Tuple of (MCP server config, list of tool names for allowed_tools)
    """
    headers = {"X-API-Key": api_key}

    # Load OpenAPI spec from bundled file
    spec = _load_openapi_spec()

    # Transform spec to scope it to workspace if requested
    if workspace_id:
        spec = _scope_spec_to_workspace(spec, workspace_id)
        print(f"Scoped OpenAPI spec to workspace_id: {workspace_id}")

    tools = []
    tool_names = []
    whitelist_post_operations = whitelist_post_operations or []

    # Iterate through paths and generate tools
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in ["get", "post", "put", "delete", "patch"]:
                continue

            # Only allow GET and whitelisted POSTs
            operation_id = operation.get("operationId", "")
            if method == "post":
                if operation_id not in whitelist_post_operations:
                    continue
            elif method not in ["get"]:
                # Skip PUT, DELETE, PATCH entirely
                continue

            # Filter by tags if specified
            operation_tags = operation.get("tags", [])
            if tags_to_include and not any(
                tag in operation_tags for tag in tags_to_include
            ):
                continue

            # Generate tool
            tool_func = _create_tool_function(
                api_endpoint=api_endpoint,
                headers=headers,
                path=path,
                method=method.upper(),
                operation=operation,
            )

            if tool_func:
                tools.append(tool_func)
                # Shorter prefix to stay under 128 char limit
                tool_name = f"mcp__{tool_func.__name__}"
                tool_names.append(tool_name)
                print(f"✓ Generated tool: {tool_func.__name__} -> {tool_name}")

    if not tools:
        print("ERROR: No tools generated from OpenAPI spec")
        raise ValueError("No tools generated from OpenAPI spec")

    # Create MCP server with generated tools
    server = create_sdk_mcp_server(name="platform", version="1.0.0", tools=tools)

    print(f"Generated {len(tools)} MCP tools from OpenAPI spec")
    return server, tool_names


def _load_openapi_spec() -> Dict[str, Any]:
    """Load OpenAPI specification from bundled file.

    Returns:
        OpenAPI specification as dict

    Raises:
        FileNotFoundError: If bundled spec not found
    """
    bundled_spec_path = Path(__file__).parent / "openapi.json"
    if not bundled_spec_path.exists():
        raise FileNotFoundError(
            f"Bundled OpenAPI spec not found at {bundled_spec_path}. "
            "Run scripts/generate-client.sh to generate it."
        )

    print(f"Loading OpenAPI spec from bundled file: {bundled_spec_path}")
    with open(bundled_spec_path) as f:
        return json.load(f)


def _scope_spec_to_workspace(spec: Dict[str, Any], workspace_id: int) -> Dict[str, Any]:
    """Transform OpenAPI spec to hardcode workspace_id in paths.

    This removes workspace_id parameters from the spec and bakes the value
    directly into the paths, making tools naturally workspace-scoped.

    Args:
        spec: Original OpenAPI specification
        workspace_id: Workspace ID to scope to

    Returns:
        Transformed OpenAPI spec with workspace_id hardcoded
    """
    scoped_spec = deepcopy(spec)
    scoped_paths = {}

    for path, path_item in spec.get("paths", {}).items():
        # Replace {workspaceId} in path with actual value
        if "{workspaceId}" in path:
            scoped_path = path.replace("{workspaceId}", str(workspace_id))

            # Remove workspaceId parameter from all operations
            scoped_path_item = deepcopy(path_item)
            for method in ["get", "post", "put", "delete", "patch"]:
                if method in scoped_path_item:
                    operation = scoped_path_item[method]
                    if "parameters" in operation:
                        operation["parameters"] = [
                            p
                            for p in operation["parameters"]
                            if not (
                                p.get("name") == "workspaceId" and p.get("in") == "path"
                            )
                        ]

            scoped_paths[scoped_path] = scoped_path_item
        else:
            # Keep paths without workspaceId as-is
            scoped_paths[path] = path_item

    scoped_spec["paths"] = scoped_paths
    return scoped_spec


def _create_tool_function(
    api_endpoint: str,
    headers: Dict[str, str],
    path: str,
    method: str,
    operation: Dict[str, Any],
):
    """Create a tool function for a specific API endpoint."""
    # Extract metadata
    operation_id = operation.get("operationId", "")
    summary = operation.get("summary", "")
    description = operation.get("description", summary)

    if not operation_id:
        # Skip endpoints without operationId
        return None

    # Parse parameters
    parameters = operation.get("parameters", [])
    path_params = [p for p in parameters if p.get("in") == "path"]
    query_params = [p for p in parameters if p.get("in") == "query"]
    request_body = operation.get("requestBody")

    # Build tool schema
    tool_schema = {}

    # Add path parameters
    for param in path_params:
        param_type = _map_openapi_type(param.get("schema", {}))
        tool_schema[param["name"]] = param_type

    # Add query parameters
    for param in query_params:
        param_type = _map_openapi_type(param.get("schema", {}))
        tool_schema[param["name"]] = param_type

    # Add request body if present
    if request_body and method in ["POST", "PUT", "PATCH"]:
        tool_schema["body"] = dict

    # Create the actual tool function
    @tool(operation_id, description, tool_schema)
    async def api_tool(args):
        """Auto-generated API tool."""
        try:
            # Build URL with path parameters
            url = f"{api_endpoint}{path}"
            for param in path_params:
                param_name = param["name"]
                if param_name in args:
                    url = url.replace(f"{{{param_name}}}", str(args[param_name]))

            # Build query parameters
            query_params_dict = {}
            for param in query_params:
                param_name = param["name"]
                if param_name in args:
                    query_params_dict[param_name] = args[param_name]

            # Make request
            if method == "GET":
                response = requests.get(
                    url, headers=headers, params=query_params_dict, timeout=30
                )
            elif method == "POST":
                body = args.get("body", {})
                response = requests.post(
                    url,
                    headers=headers,
                    json=body,
                    params=query_params_dict,
                    timeout=30,
                )
            elif method == "PUT":
                body = args.get("body", {})
                response = requests.put(
                    url,
                    headers=headers,
                    json=body,
                    params=query_params_dict,
                    timeout=30,
                )
            elif method == "DELETE":
                response = requests.delete(
                    url, headers=headers, params=query_params_dict, timeout=30
                )
            elif method == "PATCH":
                body = args.get("body", {})
                response = requests.patch(
                    url,
                    headers=headers,
                    json=body,
                    params=query_params_dict,
                    timeout=30,
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()

            # Return response
            try:
                data = response.json()
                return {
                    "content": [{"type": "text", "text": json.dumps(data, indent=2)}]
                }
            except Exception:
                # Non-JSON response
                return {"content": [{"type": "text", "text": response.text}]}

        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Error calling {method} {path}: {str(e)}"}
                ],
                "isError": True,
            }

    # Set function name for identification
    api_tool.__name__ = operation_id

    return api_tool


def _map_openapi_type(schema: Dict[str, Any]) -> type:
    """Map OpenAPI schema types to Python types."""
    openapi_type = schema.get("type", "string")

    type_mapping = {
        "string": str,
        "integer": int,
        "number": float,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    return type_mapping.get(openapi_type, str)
