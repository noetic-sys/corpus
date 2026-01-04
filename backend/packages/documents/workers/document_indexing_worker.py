from __future__ import annotations

from datetime import datetime
import logging

from common.workers.base_worker import BaseWorker
from common.providers.messaging.messages import DocumentIndexingMessage
from common.providers.messaging.constants import QueueName
from packages.documents.services.document_service import get_document_service
from packages.documents.services.document_indexing_job_service import (
    DocumentIndexingJobService,
)
from packages.documents.models.domain.document_indexing_job import (
    DocumentIndexingJobStatus,
)
from packages.documents.providers.document_search.factory import (
    get_document_search_provider,
)
from packages.documents.models.database.document import ExtractionStatus

from common.core.otel_axiom_exporter import (
    trace_span,
)

logger = logging.getLogger(__name__)


class DocumentIndexingWorker(BaseWorker[DocumentIndexingMessage]):
    """Worker that processes document indexing jobs."""

    def __init__(self):
        super().__init__(QueueName.DOCUMENT_INDEXING, None, DocumentIndexingMessage)

    @trace_span
    async def process_message(self, message: DocumentIndexingMessage):
        """Process a document indexing job message."""
        logger.info(
            f"Document Indexing Worker received message: job_id={message.job_id}, document_id={message.document_id}"
        )

        job_id = message.job_id
        document_id = message.document_id

        # Initialize services
        document_service = get_document_service()
        indexing_job_service = DocumentIndexingJobService()
        search_provider = get_document_search_provider()

        try:
            logger.info(f"Processing indexing job {job_id} for document {document_id}")

            # Update job status to in progress
            await indexing_job_service.update_job_status(
                job_id, DocumentIndexingJobStatus.IN_PROGRESS
            )

            # Get the document
            document = await document_service.get_document(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")

            logger.info(
                f"Indexing document: {document.filename} (extraction_status: {document.extraction_status})"
            )

            # Index document in search provider
            # This will index basic metadata immediately, and content if extraction is complete
            await search_provider.index_document(document)
            logger.info(
                f"Successfully indexed document {document_id} in search provider"
            )

            # If document has extracted content, also index the content
            if (
                document.extraction_status == ExtractionStatus.COMPLETED
                and document.extracted_content_path
            ):
                logger.info(
                    f"Document {document_id} has extracted content, indexing full content"
                )
                # The search provider's index_document method should handle both metadata and content
                # based on the document's extraction status

            # Mark job as completed
            await indexing_job_service.update_job_status(
                job_id,
                DocumentIndexingJobStatus.COMPLETED,
                completed_at=datetime.utcnow(),
            )

            logger.info(
                f"Successfully completed indexing job {job_id} for document {document_id}"
            )

        except Exception as e:
            logger.error(f"Error processing indexing job {job_id}: {e}", exc_info=True)

            try:
                await indexing_job_service.update_job_status(
                    job_id, DocumentIndexingJobStatus.FAILED, error_message=str(e)
                )
                logger.info(f"Indexing job {job_id} marked as failed")
            except Exception as update_error:
                logger.error(f"Failed to update job status after error: {update_error}")

            raise
