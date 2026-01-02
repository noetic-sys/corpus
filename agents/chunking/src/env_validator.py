"""
Environment validation for document chunking execution.

Handles environment variable validation and cleanup.
"""

import os
from typing import Tuple


def validate_environment() -> Tuple[int, int, str, str]:
    """
    Validate that required environment variables are set.

    Returns:
        Tuple of (document_id, company_id, api_endpoint, api_key)

    Raises:
        ValueError: If any required environment variable is missing
    """
    document_id = os.getenv("DOCUMENT_ID")
    company_id = os.getenv("COMPANY_ID")
    api_endpoint = os.getenv("API_ENDPOINT")
    api_key = os.getenv("API_KEY")

    if not all([document_id, company_id, api_endpoint, api_key]):
        raise ValueError("Missing required environment variables")

    return int(document_id), int(company_id), api_endpoint, api_key


def cleanup_sensitive_env_vars() -> None:
    """
    Remove sensitive environment variables before agent execution.

    Clears API_KEY and API_ENDPOINT from environment.
    """
    if "API_KEY" in os.environ:
        del os.environ["API_KEY"]
    if "API_ENDPOINT" in os.environ:
        del os.environ["API_ENDPOINT"]
