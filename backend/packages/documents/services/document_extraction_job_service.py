from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from common.providers.messaging.factory import get_message_queue
from common.providers.messaging.messages import DocumentExtractionMessage
from common.providers.messaging.constants import QueueName
from packages.documents.repositories.document_extraction_job_repository import (
    DocumentExtractionJobRepository,
)
from packages.documents.repositories.document_repository import DocumentRepository
from packages.documents.models.domain.document_extraction_job import (
    DocumentExtractionJobModel,
    DocumentExtractionJobCreateModel,
    DocumentExtractionJobUpdateModel,
    DocumentExtractionJobStatus,
)
from packages.documents.models.domain.document import DocumentModel, DocumentUpdateModel
from packages.documents.models.database.document import ExtractionStatus
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class DocumentExtractionJobService:
    """Service for handling document extraction job operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.extraction_job_repo = DocumentExtractionJobRepository()
        self.document_repo = DocumentRepository(db_session)
        self.message_queue = get_message_queue()

    @trace_span
    async def create_extraction_job(
        self, document_id: int
    ) -> DocumentExtractionJobModel:
        """Create a document extraction job for a document."""
        logger.info(f"Creating extraction job for document {document_id}")

        job_create = DocumentExtractionJobCreateModel(
            document_id=document_id,
            status=DocumentExtractionJobStatus.QUEUED,
        )
        extraction_job = await self.extraction_job_repo.create(job_create)

        logger.info(f"Created extraction job with ID: {extraction_job.id}")
        return extraction_job

    @trace_span
    async def get_extraction_job(
        self, job_id: int
    ) -> Optional[DocumentExtractionJobModel]:
        """Get an extraction job by ID."""
        return await self.extraction_job_repo.get(job_id)

    @trace_span
    async def update_job_status(
        self,
        job_id: int,
        status: DocumentExtractionJobStatus,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
        extracted_content_path: Optional[str] = None,
    ) -> bool:
        """Update extraction job status."""
        update_model = DocumentExtractionJobUpdateModel(
            status=status,
            error_message=error_message,
            completed_at=completed_at,
            extracted_content_path=extracted_content_path,
        )

        job = await self.extraction_job_repo.update(job_id, update_model)
        if job is not None:
            logger.info(f"Updated extraction job {job_id} status to {status.value}")
            return True
        else:
            logger.warning(f"Extraction job {job_id} not found")
            return False

    @trace_span
    async def publish_job_message(
        self, extraction_job: DocumentExtractionJobModel
    ) -> bool:
        """Send a message to the worker queue for processing."""
        try:
            await self.message_queue.declare_queue(QueueName.DOCUMENT_EXTRACTION_WORKER)

            message = DocumentExtractionMessage(
                job_id=extraction_job.id,
                document_id=extraction_job.document_id,
            )

            logger.info(
                f"Publishing message to {QueueName.DOCUMENT_EXTRACTION_WORKER} queue: {message}"
            )

            success = await self.message_queue.publish(
                QueueName.DOCUMENT_EXTRACTION_WORKER, message.model_dump()
            )

            if success:
                update_model = DocumentExtractionJobUpdateModel(
                    worker_message_id=str(extraction_job.id)
                )
                await self.extraction_job_repo.update(extraction_job.id, update_model)
                logger.info(f"Published message for extraction job {extraction_job.id}")
                return True
            else:
                logger.error(
                    f"Failed to publish message for extraction job {extraction_job.id}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error publishing message for extraction job {extraction_job.id}: {e}",
                exc_info=True,
            )
            return False

    @trace_span
    async def create_and_queue_job(
        self, document: DocumentModel
    ) -> Optional[DocumentExtractionJobModel]:
        """Create an extraction job and queue it for processing."""
        try:
            # Always create a new job - the worker will handle coordination with locking
            extraction_job = await self.create_extraction_job(document.id)

            # Update document extraction status to PROCESSING
            document_update = DocumentUpdateModel(
                extraction_status=ExtractionStatus.PROCESSING
            )
            await self.document_repo.update(document.id, document_update)

            # Note: The caller is responsible for committing the transaction
            # before this method is called to ensure the document is visible

            # Queue it for processing
            success = await self.publish_job_message(extraction_job)

            if not success:
                # Mark job as failed if we couldn't queue it
                await self.update_job_status(
                    extraction_job.id,
                    DocumentExtractionJobStatus.FAILED,
                    "Failed to queue job",
                )
                # Revert document status
                document_update = DocumentUpdateModel(
                    extraction_status=ExtractionStatus.FAILED
                )
                await self.document_repo.update(document.id, document_update)
                return None

            return extraction_job

        except Exception as e:
            logger.error(
                f"Error creating and queueing extraction job for document {document.id}: {e}",
                exc_info=True,
            )
            return None

    @trace_span
    async def queue_pending_documents(self) -> Dict[str, int]:
        """Queue all pending documents for extraction processing."""
        logger.info("Queueing all PENDING documents for extraction processing")

        # Find all PENDING documents
        pending_documents = await self.extraction_job_repo.get_pending_documents()

        logger.info(f"Found {len(pending_documents)} PENDING documents")

        queued_count = 0
        failed_count = 0

        for document in pending_documents:
            # Documents are already domain models from the repository
            job = await self.create_and_queue_job(document)
            if job:
                queued_count += 1
            else:
                failed_count += 1

        logger.info(f"Queueing complete: {queued_count} queued, {failed_count} failed")

        return {
            "total_pending_documents": len(pending_documents),
            "queued": queued_count,
            "failed": failed_count,
        }

    @trace_span
    async def get_document(self, document_id: int) -> Optional[DocumentModel]:
        """Get a document by ID."""
        return await self.document_repo.get(document_id)

    @trace_span
    async def retry_failed_jobs(self, limit: int = 100) -> Dict[str, int]:
        """Retry failed extraction jobs."""
        logger.info(f"Retrying up to {limit} failed extraction jobs")

        failed_jobs = await self.extraction_job_repo.get_failed_jobs(limit)

        retried_count = 0
        failed_count = 0

        for job in failed_jobs:
            try:
                # Reset job status to QUEUED
                await self.update_job_status(
                    job.id, DocumentExtractionJobStatus.QUEUED, error_message=None
                )

                # Re-publish message
                success = await self.publish_job_message(job)

                if success:
                    retried_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                logger.error(f"Error retrying job {job.id}: {e}")
                failed_count += 1

        logger.info(f"Retry complete: {retried_count} retried, {failed_count} failed")

        return {
            "total_failed_jobs": len(failed_jobs),
            "retried": retried_count,
            "failed": failed_count,
        }


def get_document_extraction_job_service(
    db_session: AsyncSession,
) -> DocumentExtractionJobService:
    """Get document extraction job service instance."""
    return DocumentExtractionJobService(db_session)
