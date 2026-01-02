"""
Workflow configuration loading.

Handles fetching workflow config from API and loading prompt templates.
"""

from pathlib import Path
from typing import Any, Dict

import requests


def fetch_workflow(api_endpoint: str, workflow_id: str, api_key: str) -> Dict[str, Any]:
    """
    Fetch workflow configuration from API.

    Args:
        api_endpoint: API base URL
        workflow_id: Workflow ID to fetch
        api_key: API key for authentication

    Returns:
        Workflow configuration dict

    Raises:
        requests.HTTPError: If API request fails
    """
    response = requests.get(
        f"{api_endpoint}/api/v1/workflows/{workflow_id}",
        headers={"X-API-Key": api_key},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def load_task_prompt(workflow: Dict[str, Any]) -> str:
    """
    Load and format task prompt template.

    Args:
        workflow: Workflow configuration dict

    Returns:
        Formatted prompt string
    """
    prompt_path = Path("/app/prompts/workflow_agent_task.txt")
    template = prompt_path.read_text()

    return template.format(
        workflow_id=workflow.get("id", "unknown"),
        workflow_name=workflow.get("name", "Unnamed Workflow"),
        workflow_description=workflow.get("description", "No description"),
        output_type=workflow.get("output_type", "documents"),
        source_workspace_id=workflow.get("source_workspace_id", "not specified"),
    )
