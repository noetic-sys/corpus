"""
Root document extraction workflow.
Routes documents to appropriate child workflows based on file type.
"""

from temporalio import workflow
from temporalio.common import RetryPolicy
from datetime import timedelta
import logging

from .common import (
    DocumentProcessingInput,
    ExtractionStatusType,
    TaskQueueType,
    UPDATE_EXTRACTION_STATUS_ACTIVITY,
    UPDATE_DOCUMENT_CONTENT_PATH_ACTIVITY,
    UPDATE_DOCUMENT_COMPLETION_ACTIVITY,
    QUEUE_QA_JOBS_FOR_DOCUMENT_ACTIVITY,
    GET_DOCUMENT_DETAILS_ACTIVITY,
    INDEX_CHUNKS_ACTIVITY,
)
from .pdf_to_markdown_workflow import PDFToMarkdownWorkflow
from .generic_document_workflow import GenericDocumentWorkflow
from .chunking_workflow import DocumentChunkingWorkflow

logger = logging.getLogger(__name__)


@workflow.defn
class DocumentExtractionWorkflow:
    @workflow.run
    async def run(self, input_data: DocumentProcessingInput) -> str:
        """
        Root workflow that routes documents to appropriate child workflows:
        - PDF files: Use PDF-specific workflow (multi-page processing)
        - All other files: Use generic document workflow (single-pass extraction)
        """
        logger.info(
            f"Starting document extraction workflow for document {input_data.document_id}"
        )

        try:
            # Step 1: Get document details including file_type and content_type
            document_details = await workflow.execute_activity(
                GET_DOCUMENT_DETAILS_ACTIVITY,
                args=[input_data.document_id, input_data.trace_headers],
                start_to_close_timeout=timedelta(seconds=30),
            )

            file_type = document_details["file_type"]
            content_type = document_details["content_type"]

            logger.info(
                f"Document {input_data.document_id} details: file_type={file_type}, content_type={content_type}"
            )

            # Step 2: Update job status to processing
            await workflow.execute_activity(
                UPDATE_EXTRACTION_STATUS_ACTIVITY,
                args=[
                    input_data.extraction_job_id,
                    input_data.document_id,
                    ExtractionStatusType.PROCESSING,
                    None,
                    input_data.trace_headers,
                ],
                start_to_close_timeout=timedelta(seconds=30),
            )

            # Step 3: Route to appropriate child workflow based on file type
            if self._is_pdf_file(file_type, content_type):
                logger.info(
                    f"Routing document {input_data.document_id} to PDF workflow"
                )
                s3_key = await workflow.execute_child_workflow(
                    PDFToMarkdownWorkflow.run,
                    args=[input_data],
                    id=f"pdf-extraction-{input_data.document_id}",
                    task_queue=TaskQueueType.PDF_PROCESSING.value,
                )
            else:
                logger.info(
                    f"Routing document {input_data.document_id} to generic document workflow"
                )
                s3_key = await workflow.execute_child_workflow(
                    GenericDocumentWorkflow.run,
                    args=[input_data],
                    id=f"doc-extraction-{input_data.document_id}",
                    task_queue=TaskQueueType.GENERIC_EXTRACTION.value,
                )

            # Step 3.5: Update document with S3 content path (so chunking can download)
            await workflow.execute_activity(
                UPDATE_DOCUMENT_CONTENT_PATH_ACTIVITY,
                args=[input_data.document_id, s3_key, input_data.trace_headers],
                start_to_close_timeout=timedelta(seconds=30),
            )

            logger.info(
                f"Updated document {input_data.document_id} content path: {s3_key}"
            )

            # Step 3.6: Chunk document for agent-based retrieval
            company_id = document_details["company_id"]
            chunk_result = await workflow.execute_child_workflow(
                DocumentChunkingWorkflow.run,
                args=[
                    input_data.document_id,
                    company_id,
                ],
                id=f"chunk-document-{input_data.document_id}",
                task_queue=TaskQueueType.DOCUMENT_CHUNKING.value,
            )

            logger.info(
                f"Chunked document {input_data.document_id} into {chunk_result['chunk_count']} chunks at {chunk_result['s3_prefix']}"
            )

            # Step 3.7: Index chunks for hybrid search (keyword + vector)
            # Non-blocking with retries - shouldn't prevent downstream processing
            await workflow.execute_activity(
                INDEX_CHUNKS_ACTIVITY,
                args=[input_data.document_id, company_id],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=10),
                    maximum_interval=timedelta(minutes=1),
                    maximum_attempts=3,
                    non_retryable_error_types=[],
                ),
            )

            logger.info(
                f"Indexed chunks for document {input_data.document_id} for hybrid search"
            )

            # Step 4: Update document completion status (fast, should not fail)
            await workflow.execute_activity(
                UPDATE_DOCUMENT_COMPLETION_ACTIVITY,
                args=[
                    input_data.document_id,
                    input_data.extraction_job_id,
                    s3_key,
                    input_data.trace_headers,
                ],
                start_to_close_timeout=timedelta(seconds=30),
            )

            # Step 5: Queue QA jobs for all matrices using this document
            # This is separated because it can take 20+ seconds and may fail independently
            # We use a generous timeout and limited retries to avoid cascading failures
            await workflow.execute_activity(
                QUEUE_QA_JOBS_FOR_DOCUMENT_ACTIVITY,
                args=[
                    input_data.document_id,
                    input_data.trace_headers,
                ],
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=5),
                    maximum_interval=timedelta(seconds=30),
                    maximum_attempts=3,
                    non_retryable_error_types=[],
                ),
            )

            logger.info(
                f"Document extraction workflow completed successfully for document {input_data.document_id}"
            )
            return s3_key

        except Exception as e:
            logger.error(
                f"Document extraction workflow failed for document {input_data.document_id}: {e}"
            )

            # Mark job as failed
            await workflow.execute_activity(
                UPDATE_EXTRACTION_STATUS_ACTIVITY,
                args=[
                    input_data.extraction_job_id,
                    input_data.document_id,
                    ExtractionStatusType.FAILED,
                    str(e),
                    input_data.trace_headers,
                ],
                start_to_close_timeout=timedelta(seconds=30),
            )
            raise

    def _is_pdf_file(self, file_type: str, content_type: str = None) -> bool:
        """Check if the document is a PDF file requiring multi-page processing."""
        if not file_type and not content_type:
            return False

        pdf_indicators = ["pdf", "application/pdf"]

        return (file_type and file_type.lower() in pdf_indicators) or (
            content_type and content_type.lower() in pdf_indicators
        )
