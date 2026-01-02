"""
Centralized S3 path construction for consistent filesystem locality.

All storage paths follow the pattern: company/{company_id}/{resource_type}/{resource_id}/...
This ensures filesystem locality and makes it easy to manage resources at the company level.
"""


def get_document_base_path(company_id: int, document_id: int) -> str:
    """
    Get base S3 path for a document and all its derived resources.

    Pattern: company/{company_id}/documents/{document_id}/

    Args:
        company_id: Company ID
        document_id: Document ID

    Returns:
        Base path for document resources
    """
    return f"company/{company_id}/documents/{document_id}"


def get_document_original_path(company_id: int, document_id: int, filename: str) -> str:
    """
    Get S3 path for original uploaded document.

    Pattern: company/{company_id}/documents/{document_id}/original.{ext}

    Args:
        company_id: Company ID
        document_id: Document ID
        filename: Original filename with extension

    Returns:
        S3 path for original document
    """
    return f"{get_document_base_path(company_id, document_id)}/original/{filename}"


def get_document_extracted_path(company_id: int, document_id: int) -> str:
    """
    Get S3 path for extracted document content.

    Pattern: company/{company_id}/documents/{document_id}/extracted.md

    Args:
        company_id: Company ID
        document_id: Document ID

    Returns:
        S3 path for extracted content
    """
    return f"{get_document_base_path(company_id, document_id)}/extracted.md"


def get_document_chunks_prefix(company_id: int, document_id: int) -> str:
    """
    Get S3 prefix for document chunks.

    Pattern: company/{company_id}/documents/{document_id}/chunks/

    Args:
        company_id: Company ID
        document_id: Document ID

    Returns:
        S3 prefix for all chunks
    """
    return f"{get_document_base_path(company_id, document_id)}/chunks"


def get_document_chunk_manifest_path(company_id: int, document_id: int) -> str:
    """
    Get S3 path for chunk manifest.

    Pattern: company/{company_id}/documents/{document_id}/chunks/manifest.json

    Args:
        company_id: Company ID
        document_id: Document ID

    Returns:
        S3 path for chunk manifest
    """
    return f"{get_document_chunks_prefix(company_id, document_id)}/manifest.json"


def get_workflow_base_path(company_id: int, workflow_id: int) -> str:
    """
    Get base S3 path for a workflow and all its executions.

    Pattern: company/{company_id}/workflows/{workflow_id}/

    Args:
        company_id: Company ID
        workflow_id: Workflow ID

    Returns:
        Base path for workflow resources
    """
    return f"company/{company_id}/workflows/{workflow_id}"


def get_workflow_execution_path(
    company_id: int, workflow_id: int, execution_id: int
) -> str:
    """
    Get S3 path for workflow execution outputs.

    Pattern: company/{company_id}/workflows/{workflow_id}/executions/{execution_id}/

    Args:
        company_id: Company ID
        workflow_id: Workflow ID
        execution_id: Execution ID

    Returns:
        Base path for execution outputs
    """
    return (
        f"{get_workflow_base_path(company_id, workflow_id)}/executions/{execution_id}"
    )
