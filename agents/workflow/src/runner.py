"""
Claude Agent Runner for Workflow Execution

Minimal entry point that orchestrates agent execution using modular components.
"""

import asyncio
import sys

from workflows.execution_result import (
    ExecutionFiles,
    ExecutionMetadata,
)

from agent_config import create_agent_options
from agent_executor import execute_agent
from env_validator import (
    cleanup_sensitive_env_vars,
    debug_skills_availability,
    validate_environment,
)
from input_downloader import download_input_files
from output_uploader import upload_outputs_to_s3
from result_handler import (
    list_generated_files,
    write_manifest,
)
from workflow_loader import (
    fetch_workflow,
    load_task_prompt,
)


async def main():
    """Main entry point for agent execution."""
    # Validate environment
    try:
        execution_id, workflow_id, workspace_id, api_endpoint, api_key = (
            validate_environment()
        )
        print(f"Starting Claude Agent for execution {execution_id}")
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Fetch workflow configuration
    try:
        workflow = fetch_workflow(api_endpoint, workflow_id, api_key)
        print(f"Loaded workflow: {workflow.get('name')}")
    except Exception as e:
        print(f"ERROR: Failed to fetch workflow: {e}")
        sys.exit(1)

    # Download input files before agent starts
    try:
        download_input_files(api_endpoint, workflow_id, api_key)
    except Exception as e:
        print(f"ERROR: Failed to download input files: {e}")
        sys.exit(1)

    # Create agent options with MCP server
    try:
        # Scope MCP tools to the workflow's workspace (from environment)
        options, mcp_tool_names = create_agent_options(
            api_endpoint=api_endpoint,
            api_key=api_key,
            workspace_id=workspace_id,
        )
        print(f"Generated {len(mcp_tool_names)} MCP tools from OpenAPI spec")
    except Exception as e:
        print(f"ERROR: Failed to create MCP server: {e}")
        sys.exit(1)

    # Load task prompt
    task_prompt = load_task_prompt(workflow)

    # Debug: Check if skills are accessible
    debug_skills_availability()

    # Clear sensitive environment variables before agent execution
    cleanup_sensitive_env_vars()

    # Run agent
    try:
        result_message = await execute_agent(task_prompt, options)
    except Exception as e:
        print(f"ERROR: Agent execution failed: {e}")
        empty_files = ExecutionFiles(outputs=[], scratch=[])
        metadata = ExecutionMetadata(success=False, error=str(e))
        write_manifest(execution_id, empty_files, metadata)
        sys.exit(1)

    # Check ResultMessage for error state
    if result_message and result_message.is_error:
        print("ERROR: Agent execution failed (is_error=True)")
        files = list_generated_files()
        metadata = ExecutionMetadata(
            success=False,
            error=result_message.result or "Agent execution failed",
            cost_usd=result_message.total_cost_usd,
            duration_ms=result_message.duration_ms,
        )
        write_manifest(execution_id, files, metadata)
        sys.exit(1)

    # Write manifest of generated files
    files = list_generated_files()
    metadata = ExecutionMetadata(
        success=True,
        cost_usd=result_message.total_cost_usd if result_message else None,
        duration_ms=result_message.duration_ms if result_message else None,
    )
    write_manifest(execution_id, files, metadata)

    total_files = len(files.outputs) + len(files.scratch)
    print(
        f"Execution complete. Generated {len(files.outputs)} outputs and {len(files.scratch)} scratch files ({total_files} total)."
    )

    # Upload outputs to S3 using presigned URLs (api_key still in scope, not in env)
    try:
        upload_outputs_to_s3(
            api_endpoint=api_endpoint,
            workflow_id=int(workflow_id),
            execution_id=int(execution_id),
            api_key=api_key,
            output_files=files.outputs,
        )
    except Exception as e:
        print(f"ERROR: Failed to upload outputs to S3: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
