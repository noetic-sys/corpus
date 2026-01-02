"""
Environment validation for agent QA execution.

Validates required environment variables for agent QA container.
"""

import json
import os
from typing import List, Optional, Tuple


def validate_environment() -> Tuple[
    int,
    int,
    List[int],
    str,
    str,
    int,
    int,
    int,
    int,
    Optional[int],
    List[str],
    str,
    str,
    str,
]:
    """
    Validate required environment variables for agent QA.

    Returns:
        Tuple of (qa_job_id, matrix_cell_id, document_ids, question, matrix_type,
                  question_type_id, question_id, company_id, min_answers, max_answers,
                  options, api_endpoint, api_key, anthropic_api_key)

    Raises:
        ValueError: If any required environment variable is missing
    """
    required_vars = [
        "QA_JOB_ID",
        "MATRIX_CELL_ID",
        "DOCUMENT_IDS",
        "QUESTION",
        "MATRIX_TYPE",
        "QUESTION_TYPE_ID",
        "QUESTION_ID",
        "COMPANY_ID",
        "MIN_ANSWERS",
        "MAX_ANSWERS",
        "QUESTION_OPTIONS",
        "API_ENDPOINT",
        "API_KEY",
        "ANTHROPIC_API_KEY",
    ]

    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    # Parse values
    qa_job_id = int(os.environ["QA_JOB_ID"])
    matrix_cell_id = int(os.environ["MATRIX_CELL_ID"])
    document_ids = json.loads(os.environ["DOCUMENT_IDS"])
    question = os.environ["QUESTION"]
    matrix_type = os.environ["MATRIX_TYPE"]
    question_type_id = int(os.environ["QUESTION_TYPE_ID"])
    question_id = int(os.environ["QUESTION_ID"])
    company_id = int(os.environ["COMPANY_ID"])
    min_answers = int(os.environ["MIN_ANSWERS"])

    # max_answers can be null (unlimited)
    max_answers_str = os.environ["MAX_ANSWERS"]
    max_answers = (
        None if max_answers_str in ("None", "null", "") else int(max_answers_str)
    )

    options = json.loads(os.environ["QUESTION_OPTIONS"])
    api_endpoint = os.environ["API_ENDPOINT"]
    api_key = os.environ["API_KEY"]
    anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]

    return (
        qa_job_id,
        matrix_cell_id,
        document_ids,
        question,
        matrix_type,
        question_type_id,
        question_id,
        company_id,
        min_answers,
        max_answers,
        options,
        api_endpoint,
        api_key,
        anthropic_api_key,
    )


def cleanup_sensitive_env_vars():
    """Remove sensitive environment variables before agent execution."""
    # Only remove API_KEY (service account key)
    # Keep ANTHROPIC_API_KEY since Claude Code CLI needs it
    sensitive_vars = ["API_KEY"]
    for var in sensitive_vars:
        if var in os.environ:
            del os.environ[var]
            print(f"Cleared {var} from environment")
