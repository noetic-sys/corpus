from typing import Optional
from datetime import datetime

from common.providers.messaging.factory import get_message_queue
from common.providers.messaging.messages import QAJobMessage
from common.providers.messaging.constants import QueueName
from packages.qa.repositories.qa_job_repository import QAJobRepository
from packages.documents.repositories.document_repository import DocumentRepository
from packages.questions.repositories.question_repository import QuestionRepository
from packages.qa.models.domain.qa_job import (
    QAJobModel,
    QAJobCreateModel,
    QAJobUpdateModel,
    QAJobStatus,
    QueuePendingCellsResult,
)
from packages.matrices.models.domain.matrix import MatrixCellModel
from packages.documents.models.domain.document import DocumentModel
from packages.questions.models.domain.question import QuestionModel
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class QAJobService:
    """Service for handling QA job operations."""

    def __init__(self):
        self.qa_job_repo = QAJobRepository()
        self.document_repo = DocumentRepository()
        self.question_repo = QuestionRepository()
        self.message_queue = get_message_queue()

    @trace_span
    async def create_qa_job(self, matrix_cell_id: int) -> QAJobModel:
        """Create a QA job for a matrix cell."""
        logger.info(f"Creating QA job for matrix cell {matrix_cell_id}")

        job_data = QAJobCreateModel(
            matrix_cell_id=matrix_cell_id,
        )
        qa_job = await self.qa_job_repo.create(job_data)

        logger.info(f"Created QA job with ID: {qa_job.id}")
        return qa_job

    @trace_span
    async def get_qa_job(self, job_id: int) -> Optional[QAJobModel]:
        """Get a QA job by ID."""
        return await self.qa_job_repo.get(job_id)

    @trace_span
    async def update_job_status(
        self,
        job_id: int,
        status: QAJobStatus,
        error_message: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> bool:
        """Update QA job status."""
        update_data = QAJobUpdateModel(
            status=status.value if isinstance(status, QAJobStatus) else status,
            error_message=error_message,
            completed_at=completed_at,
        )

        job = await self.qa_job_repo.update(job_id, update_data)
        if job:
            logger.info(
                f"Updated job {job_id} status to {status.value if isinstance(status, QAJobStatus) else status}"
            )
            return True
        else:
            logger.warning(f"QA job {job_id} not found")
            return False

    @trace_span
    async def publish_job_message(
        self, qa_job: QAJobModel, matrix_cell: MatrixCellModel
    ) -> bool:
        """Send a message to the worker queue for processing."""
        try:
            await self.message_queue.declare_queue(QueueName.QA_WORKER)

            message = QAJobMessage(
                job_id=qa_job.id,
                matrix_cell_id=matrix_cell.id,
            )

            logger.info(f"Publishing message to {QueueName.QA_WORKER} queue: {message}")

            success = await self.message_queue.publish(
                QueueName.QA_WORKER, message.model_dump()
            )

            if success:
                update_data = QAJobUpdateModel(worker_message_id=str(qa_job.id))
                await self.qa_job_repo.update(qa_job.id, update_data)
                logger.info(f"Published message for job {qa_job.id}")
                return True
            else:
                logger.error(f"Failed to publish message for job {qa_job.id}")
                return False

        except Exception as e:
            logger.error(
                f"Error publishing message for job {qa_job.id}: {e}", exc_info=True
            )
            return False

    @trace_span
    async def create_and_queue_job(
        self, matrix_cell: MatrixCellModel
    ) -> Optional[QAJobModel]:
        """Create a QA job and queue it for processing."""
        try:
            # Always create a new job - the worker will handle coordination with locking
            qa_job = await self.create_qa_job(matrix_cell.id)

            # Queue it for processing
            success = await self.publish_job_message(qa_job, matrix_cell)

            if not success:
                # Mark job as failed if we couldn't queue it
                await self.update_job_status(
                    qa_job.id, QAJobStatus.FAILED.value, "Failed to queue job"
                )
                return None

            return qa_job

        except Exception as e:
            logger.error(
                f"Error creating and queueing job for cell {matrix_cell.id}: {e}",
                exc_info=True,
            )
            return None

    @trace_span
    async def queue_pending_cells(
        self, matrix_id: Optional[int] = None
    ) -> QueuePendingCellsResult:
        """Queue pending matrix cells for processing.

        Args:
            matrix_id: Optional matrix ID to filter cells. If provided, only queues cells for that matrix.
                      If not provided, queues all pending cells.
        """
        if matrix_id:
            logger.info(f"Queueing PENDING matrix cells for matrix {matrix_id}")
        else:
            logger.info("Queueing all PENDING matrix cells for processing")

        # Find PENDING matrix cells (optionally filtered by matrix_id)
        pending_cells = await self.qa_job_repo.get_pending_matrix_cells(matrix_id)

        logger.info(f"Found {len(pending_cells)} PENDING matrix cells")

        queued_count = 0
        failed_count = 0

        for cell in pending_cells:
            job = await self.create_and_queue_job(cell)
            if job:
                queued_count += 1
            else:
                failed_count += 1

        logger.info(f"Queueing complete: {queued_count} queued, {failed_count} failed")

        return QueuePendingCellsResult(
            total_pending_cells=len(pending_cells),
            queued=queued_count,
            failed=failed_count,
        )

    @trace_span
    async def get_document(self, document_id: int) -> Optional[DocumentModel]:
        """Get a document by ID."""
        return await self.document_repo.get(document_id)

    @trace_span
    async def get_question(self, question_id: int) -> Optional[QuestionModel]:
        """Get a question by ID."""
        return await self.question_repo.get(question_id)


def get_qa_job_service() -> QAJobService:
    """Get QA job service instance."""
    return QAJobService()
