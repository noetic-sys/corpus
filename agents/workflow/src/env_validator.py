"""
Environment validation and setup for workflow execution.

Handles environment variable validation, cleanup, and debug utilities.
"""

import os
from typing import Tuple


def validate_environment() -> Tuple[int, int, int, str, str]:
    """
    Validate that required environment variables are set.

    Returns:
        Tuple of (execution_id, workflow_id, workspace_id, api_endpoint, api_key)

    Raises:
        ValueError: If any required environment variable is missing
    """
    execution_id = os.getenv("EXECUTION_ID")
    workflow_id = os.getenv("WORKFLOW_ID")
    workspace_id = os.getenv("WORKSPACE_ID")
    api_endpoint = os.getenv("API_ENDPOINT")
    api_key = os.getenv("API_KEY")

    if not all([execution_id, workflow_id, workspace_id, api_endpoint, api_key]):
        raise ValueError("Missing required environment variables")

    return int(execution_id), int(workflow_id), int(workspace_id), api_endpoint, api_key


def cleanup_sensitive_env_vars() -> None:
    """
    Remove sensitive environment variables before agent execution.

    Clears API_KEY and API_ENDPOINT from environment.
    """
    if "API_KEY" in os.environ:
        del os.environ["API_KEY"]
    if "API_ENDPOINT" in os.environ:
        del os.environ["API_ENDPOINT"]


def debug_skills_availability() -> None:
    """
    Debug utility to check if skills are accessible in expected locations.

    Prints availability and contents of common skills directories.
    """
    print("Checking for skills...")
    skills_paths = [
        "/workspace/.claude/skills",
        "/home/agentuser/.claude/skills",
        f"{os.path.expanduser('~')}/.claude/skills",
    ]
    for path in skills_paths:
        if os.path.exists(path):
            print(f"✓ Found: {path}")
            try:
                contents = os.listdir(path)
                print(f"  Contents: {contents}")
                for item in contents:
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        print(f"    {item}/: {os.listdir(item_path)}")
            except Exception as e:
                print(f"  Error listing: {e}")
        else:
            print(f"✗ Missing: {path}")
