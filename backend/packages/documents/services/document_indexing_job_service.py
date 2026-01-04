from typing import Optional
from datetime import datetime

from common.providers.messaging.factory import get_message_queue
from common.providers.messaging.messages import DocumentIndexingMessage
from common.providers.messaging.constants import QueueName
from packages.documents.repositories.document_indexing_job_repository import (
    DocumentIndexingJobRepository,
)
from packages.documents.models.domain.document_indexing_job import (
    DocumentIndexingJobModel,
    DocumentIndexingJobCreateModel,
    DocumentIndexingJobUpdateModel,
    DocumentIndexingJobStatus,
)
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class DocumentIndexingJobService:
    """Service for handling document indexing job operations."""

    def __init__(self):
        self.indexing_job_repo = DocumentIndexingJobRepository()
        self.message_queue = get_message_queue()

    @trace_span
    async def create_indexing_job(self, document_id: int) -> DocumentIndexingJobModel:
        """Create an indexing job for a document."""
        logger.info(f"Creating indexing job for document {document_id}")

        job_create = DocumentIndexingJobCreateModel(
            document_id=document_id,
            status=DocumentIndexingJobStatus.QUEUED,
        )
        indexing_job = await self.indexing_job_repo.create(job_create)

        logger.info(f"Created indexing job with ID: {indexing_job.id}")
        return indexing_job

    @trace_span
    async def get_indexing_job(self, job_id: int) -> Optional[DocumentIndexingJobModel]:
        """Get an indexing job by ID."""
        return await self.indexing_job_repo.get(job_id)

    @trace_span
    async def update_job_status(
        self,
        job_id: int,
        status: DocumentIndexingJobStatus,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> bool:
        """Update indexing job status."""
        update_model = DocumentIndexingJobUpdateModel(
            status=status,
            error_message=error_message,
            completed_at=completed_at,
        )

        job = await self.indexing_job_repo.update(job_id, update_model)
        if job:
            logger.info(f"Updated indexing job {job_id} status to {status.value}")
            return True
        else:
            logger.warning(f"Indexing job {job_id} not found")
            return False

    @trace_span
    async def publish_job_message(self, indexing_job: DocumentIndexingJobModel) -> bool:
        """Send a message to the worker queue for processing."""
        try:
            await self.message_queue.declare_queue(QueueName.DOCUMENT_INDEXING)

            message = DocumentIndexingMessage(
                job_id=indexing_job.id,
                document_id=indexing_job.document_id,
            )

            logger.info(
                f"Publishing message to {QueueName.DOCUMENT_INDEXING} queue: {message}"
            )

            success = await self.message_queue.publish(
                QueueName.DOCUMENT_INDEXING, message.model_dump()
            )

            if success:
                update_model = DocumentIndexingJobUpdateModel(
                    worker_message_id=str(indexing_job.id)
                )
                await self.indexing_job_repo.update(indexing_job.id, update_model)
                logger.info(f"Published message for indexing job {indexing_job.id}")
                return True
            else:
                logger.error(
                    f"Failed to publish message for indexing job {indexing_job.id}"
                )
                return False

        except Exception as e:
            logger.error(
                f"Error publishing message for indexing job {indexing_job.id}: {e}",
                exc_info=True,
            )
            return False

    @trace_span
    async def create_and_queue_job(
        self, document_id: int
    ) -> Optional[DocumentIndexingJobModel]:
        """Create an indexing job and queue it for processing."""
        try:
            # Create the job
            indexing_job = await self.create_indexing_job(document_id)

            # Queue it for processing
            success = await self.publish_job_message(indexing_job)

            if not success:
                # Mark job as failed if we couldn't queue it
                await self.update_job_status(
                    indexing_job.id,
                    DocumentIndexingJobStatus.FAILED,
                    "Failed to queue job",
                )
                return None

            return indexing_job

        except Exception as e:
            logger.error(
                f"Error creating and queueing indexing job for document {document_id}: {e}",
                exc_info=True,
            )
            return None
