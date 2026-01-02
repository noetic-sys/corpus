"""
Common types, exceptions, and constants for PDF extraction workflows.
"""

from typing import Optional, Dict
from enum import StrEnum
from pydantic import BaseModel, Field


class ExtractionStatusType(StrEnum):
    """Status types for extraction workflow.

    Uses StrEnum instead of str, Enum to ensure proper Temporal serialization.
    See: https://github.com/temporalio/sdk-python/blob/d5edb71ac25f0d82582ec16f13410b0388addc10/temporalio/converter.py#L1226
    """

    PROCESSING = "processing"
    FAILED = "failed"


class TaskQueueType(StrEnum):
    """Task queue types for different workflow processing.

    Uses StrEnum for proper Temporal serialization.
    """

    DOCUMENT_ROUTING = "document-routing-queue"  # Main queue for document routing
    PDF_PROCESSING = "pdf-processing-queue"  # Queue for PDF-specific workflows
    PAGE_CONVERSION = "page-conversion-queue"  # Queue for individual page conversion
    GENERIC_EXTRACTION = "generic-extraction-queue"  # Queue for non-PDF documents
    DOCUMENT_CHUNKING = (
        "document-chunking-queue"  # Queue for document chunking workflows
    )


class MarkdownPage(BaseModel):
    """Represents a single PDF page with its extracted markdown content.

    Note: content can be empty string for blank pages.
    """

    page_number: int = Field(..., ge=0, description="Zero-based page number")
    content: str = Field(
        default="",
        description="Extracted markdown content (can be empty for blank pages)",
    )


class DocumentProcessingInput(BaseModel):
    """Input parameters for document processing workflow."""

    document_id: int = Field(
        ..., gt=0, description="ID of the document being processed"
    )
    matrix_id: Optional[int] = Field(
        None,
        gt=0,
        description="ID of the matrix containing the document (optional since documents are now standalone)",
    )
    extraction_job_id: int = Field(..., gt=0, description="ID of the extraction job")
    trace_headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="OpenTelemetry trace context headers"
    )


# For backward compatibility
PDFProcessingInput = DocumentProcessingInput


# Activity names using string names to avoid sandbox restrictions during workflow definition

# Generic document extraction activities
EXTRACT_DOCUMENT_CONTENT_ACTIVITY = "extract_document_content_activity"
SAVE_EXTRACTED_CONTENT_TO_S3_ACTIVITY = "save_extracted_content_to_s3_activity"
INDEX_DOCUMENT_FOR_SEARCH_ACTIVITY = "index_document_for_search_activity"
UPDATE_EXTRACTION_STATUS_ACTIVITY = "update_extraction_status_activity"
UPDATE_DOCUMENT_CONTENT_PATH_ACTIVITY = "update_document_content_path_activity"
UPDATE_DOCUMENT_COMPLETION_ACTIVITY = "update_document_completion_activity"
QUEUE_QA_JOBS_FOR_DOCUMENT_ACTIVITY = "queue_qa_jobs_for_document_activity"
GET_DOCUMENT_DETAILS_ACTIVITY = "get_document_details_activity"

# PDF-specific activities (for multi-page processing)
SPLIT_PDF_ACTIVITY = "split_pdf_activity"
CONVERT_PAGE_TO_MARKDOWN_ACTIVITY = "convert_page_to_markdown_activity"
COMBINE_MARKDOWN_ACTIVITY = "combine_markdown_activity"
SAVE_MARKDOWN_TO_S3_ACTIVITY = "save_markdown_to_s3_activity"

# Chunk indexing activities
INDEX_CHUNKS_ACTIVITY = "index_chunks_activity"
