from typing import Optional

from temporalio.client import Client
from temporalio.service import RetryConfig
from temporalio.worker import Worker

from common.temporal.client import get_temporal_client
from packages.documents.workflows import DocumentExtractionWorkflow
from packages.documents.workflows import PDFToMarkdownWorkflow
from packages.documents.workflows import GenericDocumentWorkflow
from packages.documents.workflows import ConvertPageWorkflow
from packages.documents.workflows import DocumentChunkingWorkflow
from packages.documents.workflows.activities import (
    split_pdf_activity,
    convert_page_to_markdown_activity,
    extract_document_content_activity,
    save_extracted_content_to_s3_activity,
    combine_markdown_activity,
    save_markdown_to_s3_activity,
    update_extraction_status_activity,
    update_document_content_path_activity,
    update_document_completion_activity,
    queue_qa_jobs_for_document_activity,
    get_document_details_activity,
    index_document_for_search_activity,
    # Chunking activities
    get_chunking_strategy_activity,
    launch_chunking_activity,
    check_chunking_status_activity,
    extract_chunking_results_activity,
    cleanup_chunking_activity,
    naive_chunking_activity,
    refund_agentic_chunking_credit_activity,
    update_agentic_chunking_metadata_activity,
)
from packages.documents.workflows.activities.chunk_indexing_activities import (
    index_chunks_activity,
)
from packages.documents.workflows.common import TaskQueueType
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class TemporalWorker:
    """Temporal worker for document extraction workflows."""

    def __init__(
        self,
        task_queue: str = "document-extraction-queue",
    ):
        self.task_queue = task_queue
        self.client: Optional[Client] = None
        self.worker: Optional[Worker] = None
        self.running = False

    async def connect(self):
        """Connect to Temporal server."""
        self.client = await get_temporal_client()

    async def create_worker(self):
        """Create Temporal worker with workflows and activities based on queue type."""
        if not self.client:
            await self.connect()

        logger.info(f"Creating Temporal worker for task queue: {self.task_queue}")

        # Define queue-specific configurations
        queue_configs = {
            TaskQueueType.DOCUMENT_ROUTING.value: {
                "workflows": [DocumentExtractionWorkflow],
                "activities": [
                    get_document_details_activity,
                    update_extraction_status_activity,
                    update_document_content_path_activity,
                    update_document_completion_activity,
                    queue_qa_jobs_for_document_activity,
                    index_chunks_activity,
                ],
            },
            TaskQueueType.PDF_PROCESSING.value: {
                "workflows": [PDFToMarkdownWorkflow],
                "activities": [
                    split_pdf_activity,
                    combine_markdown_activity,
                    save_markdown_to_s3_activity,
                    index_document_for_search_activity,
                ],
            },
            TaskQueueType.PAGE_CONVERSION.value: {
                "workflows": [ConvertPageWorkflow],
                "activities": [
                    convert_page_to_markdown_activity,
                ],
            },
            TaskQueueType.GENERIC_EXTRACTION.value: {
                "workflows": [GenericDocumentWorkflow],
                "activities": [
                    get_document_details_activity,
                    extract_document_content_activity,
                    save_extracted_content_to_s3_activity,
                    index_document_for_search_activity,
                    update_document_completion_activity,
                    queue_qa_jobs_for_document_activity,
                ],
            },
            TaskQueueType.DOCUMENT_CHUNKING.value: {
                "workflows": [DocumentChunkingWorkflow],
                "activities": [
                    get_chunking_strategy_activity,
                    launch_chunking_activity,
                    check_chunking_status_activity,
                    extract_chunking_results_activity,
                    cleanup_chunking_activity,
                    naive_chunking_activity,
                    refund_agentic_chunking_credit_activity,
                    update_agentic_chunking_metadata_activity,
                ],
            },
            "all": {  # Special case for development - handles all queues
                "workflows": [
                    DocumentExtractionWorkflow,
                    PDFToMarkdownWorkflow,
                    GenericDocumentWorkflow,
                    ConvertPageWorkflow,
                    DocumentChunkingWorkflow,
                ],
                "activities": [
                    split_pdf_activity,
                    convert_page_to_markdown_activity,
                    extract_document_content_activity,
                    save_extracted_content_to_s3_activity,
                    combine_markdown_activity,
                    save_markdown_to_s3_activity,
                    get_document_details_activity,
                    update_extraction_status_activity,
                    update_document_content_path_activity,
                    update_document_completion_activity,
                    queue_qa_jobs_for_document_activity,
                    index_document_for_search_activity,
                    # Chunking activities
                    get_chunking_strategy_activity,
                    launch_chunking_activity,
                    check_chunking_status_activity,
                    extract_chunking_results_activity,
                    cleanup_chunking_activity,
                    naive_chunking_activity,
                    refund_agentic_chunking_credit_activity,
                    update_agentic_chunking_metadata_activity,
                    index_chunks_activity,
                ],
            },
        }

        # Get configuration for this queue
        config = queue_configs.get(self.task_queue, queue_configs["all"])

        self.worker = Worker(
            self.client,
            task_queue=self.task_queue,
            workflows=config["workflows"],
            activities=config["activities"],
        )

        logger.info(
            f"Temporal worker created successfully with {len(config['workflows'])} workflows and {len(config['activities'])} activities"
        )

    async def start(self):
        """Start the Temporal worker."""
        if not self.worker:
            await self.create_worker()

        logger.info("Starting Temporal worker...")
        self.running = True

        try:
            await self.worker.run()
        except Exception as e:
            logger.error(f"Worker failed with error: {e}", exc_info=True)
            raise
        finally:
            self.running = False

    async def stop(self):
        """Stop the Temporal worker."""
        logger.info("Stopping Temporal worker...")
        self.running = False

        if self.worker:
            # Temporal worker will stop when the run() method exits
            pass

        if self.client:
            await self.client.close()

        logger.info("Temporal worker stopped")
