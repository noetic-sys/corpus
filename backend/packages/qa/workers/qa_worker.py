from __future__ import annotations
from packages.matrices.strategies.factory import CellStrategyFactory
from common.workers.base_worker import BaseWorker
from packages.matrices.models.domain.matrix import MatrixCellStatus
from packages.qa.models.domain.qa_job import QAJobStatus
from common.providers.messaging.messages import QAJobMessage
from common.providers.messaging.constants import QueueName
from packages.qa.services.qa_job_service import get_qa_job_service
from packages.qa.services.qa_routing_service import get_qa_routing_service
from packages.questions.services.question_service import get_question_service
from packages.matrices.services.matrix_service import get_matrix_service
from packages.qa.temporal.agent_qa_workflow import AgentQAWorkflow
from common.providers.locking.factory import get_lock_provider
from common.temporal.client import get_temporal_client
from common.core.config import settings

from datetime import datetime

from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class QAWorker(BaseWorker[QAJobMessage]):
    """Worker that processes document Q&A jobs using strategy pattern."""

    def __init__(self):
        super().__init__(
            QueueName.QA_WORKER,
            None,
            QAJobMessage,
            max_concurrent_messages=settings.qa_worker_prefetch_count,
        )
        self.lock_provider = get_lock_provider()

    async def _acquire_processing_lock(
        self, matrix_cell_id: int, qa_job_service, job_id: int
    ) -> tuple[str, str]:
        """Acquire lock for matrix cell processing."""
        lock_key = f"matrix_cell:{matrix_cell_id}"
        lock_token = await self.lock_provider.acquire_lock(
            lock_key, timeout_seconds=300
        )  # 5 min timeout

        if not lock_token:
            logger.info(
                f"Could not acquire lock for matrix cell {matrix_cell_id} - another worker is processing it"
            )
            # Don't mark job as failed, just skip and ack the message
            await qa_job_service.update_job_status(
                job_id,
                QAJobStatus.COMPLETED,
                error_message="Cell being processed by another worker",
            )
            return None, None  # Signal to skip processing

        return lock_key, lock_token

    async def _validate_matrix_cell(
        self, matrix_cell_id: int, matrix_service, qa_job_service, job_id: int
    ) -> bool:
        """Validate matrix cell exists and is not already completed."""
        cell = await matrix_service.get_matrix_cell(matrix_cell_id)
        if not cell:
            logger.warning(f"Matrix cell {matrix_cell_id} not found")
            await qa_job_service.update_job_status(
                job_id,
                QAJobStatus.FAILED,
                error_message="Matrix cell not found",
            )
            return False

        if cell.status == MatrixCellStatus.COMPLETED:
            logger.info(
                f"Matrix cell {matrix_cell_id} already completed - skipping duplicate"
            )
            await qa_job_service.update_job_status(
                job_id,
                QAJobStatus.COMPLETED,
                error_message="Cell already completed",
            )
            return False

        return True

    async def _launch_agent_qa_workflow(
        self,
        job_id: int,
        matrix_cell_id: int,
        cell_data,
        question_model,
        matrix,
    ):
        """Launch Temporal workflow for agent-based QA."""
        logger.info(
            f"Launching agent QA workflow for job {job_id}, cell {matrix_cell_id}"
        )

        # Extract document IDs from cell data
        document_ids = [doc.document_id for doc in cell_data.documents]

        # Connect to Temporal
        temporal_client = await get_temporal_client()

        # Start workflow
        workflow_id = f"agent-qa-{job_id}-{matrix_cell_id}"
        await temporal_client.start_workflow(
            AgentQAWorkflow.run,
            args=[
                job_id,
                matrix_cell_id,
                document_ids,
                cell_data.question.question_text,
                matrix.matrix_type.value,
                question_model.question_type_id,
                question_model.id,
                matrix.company_id,
                question_model.min_answers,
                question_model.max_answers,
            ],
            id=workflow_id,
            task_queue="agent-qa-worker",
        )

        logger.info(f"Started agent QA workflow {workflow_id}")

    async def _handle_processing_error(
        self,
        e: Exception,
        job_id: int,
        matrix_cell_id: int,
        matrix_service,
        qa_job_service,
    ):
        """Handle processing errors and update job status."""
        logger.error(f"Error processing QA job {job_id}: {e}", exc_info=True)

        try:
            if job_id and matrix_cell_id:
                logger.info(f"Marking job {job_id} as failed due to error: {e}")
                await qa_job_service.update_job_status(
                    job_id, QAJobStatus.FAILED, error_message=str(e)
                )
                await matrix_service.update_matrix_cell_status(
                    matrix_cell_id, MatrixCellStatus.FAILED
                )
                logger.info(f"Job {job_id} marked as failed")
            else:
                logger.error(
                    "Could not mark job as failed - missing job_id or matrix_cell_id"
                )
        except Exception as update_error:
            logger.error(f"Failed to update job status after error: {update_error}")

    @trace_span
    async def process_message(self, message: QAJobMessage):
        """Process a QA job message using strategy pattern."""
        logger.info(
            f"QA Worker received message: job_id={message.job_id}, matrix_cell_id={message.matrix_cell_id}"
        )

        job_id = message.job_id
        matrix_cell_id = message.matrix_cell_id

        # Initialize services
        matrix_service = get_matrix_service()
        qa_job_service = get_qa_job_service()

        try:
            logger.info(f"Processing QA job {job_id} for cell {matrix_cell_id}")

            # Acquire processing lock
            lock_key, lock_token = await self._acquire_processing_lock(
                matrix_cell_id, qa_job_service, job_id
            )
            if not lock_token:  # Lock acquisition failed, skip processing
                return

            try:
                # Validate matrix cell state and get cell
                if not await self._validate_matrix_cell(
                    matrix_cell_id, matrix_service, qa_job_service, job_id
                ):
                    return

                # Get cell and matrix to determine strategy
                cell = await matrix_service.get_matrix_cell(matrix_cell_id)
                if not cell:
                    raise ValueError(f"Matrix cell {matrix_cell_id} not found")

                matrix = await matrix_service.get_matrix(cell.matrix_id)
                if not matrix:
                    raise ValueError(f"Matrix {cell.matrix_id} not found")

                logger.info(
                    f"Processing {matrix.matrix_type.value} matrix cell {matrix_cell_id}"
                )

                # Get strategy for this matrix type
                strategy = CellStrategyFactory.get_strategy(matrix.matrix_type)

                # Load cell data to get question info
                cell_data = await strategy.load_cell_data(
                    matrix_cell_id, matrix.company_id
                )

                # Load full question model for routing check
                question_service = get_question_service()
                question_model = await question_service.get_question(
                    cell_data.question.question_id, matrix.company_id
                )
                if not question_model:
                    raise ValueError(
                        f"Question {cell_data.question.question_id} not found"
                    )

                # Check if we should use agent QA
                routing_service = get_qa_routing_service()
                use_agent_qa = routing_service.should_use_agent_qa(
                    question_model.use_agent_qa
                )

                if use_agent_qa:
                    # Route to agent QA via Temporal workflow
                    logger.info(f"Routing cell {matrix_cell_id} to agent QA workflow")
                    await self._launch_agent_qa_workflow(
                        job_id,
                        matrix_cell_id,
                        cell_data,
                        question_model,
                        matrix,
                    )
                    # Mark job as completed (workflow will handle the rest)
                    await qa_job_service.update_job_status(
                        job_id, QAJobStatus.COMPLETED, completed_at=datetime.utcnow()
                    )
                    logger.info(f"Launched agent QA workflow for job {job_id}")
                    return  # Exit early, workflow handles the rest

                # Use regular QA strategy
                logger.info(f"Processing cell {matrix_cell_id} with regular QA")
                answer_set, question_type_id = (
                    await strategy.process_cell_to_completion(
                        matrix_cell_id, matrix.company_id
                    )
                )

                # Create answer set from AI response
                logger.info(
                    f"Creating answer set with {answer_set.answer_count} answer(s) for cell {matrix_cell_id}, "
                    f"found={answer_set.answer_found}"
                )
                success = await matrix_service.create_matrix_cell_answer_set_from_ai(
                    matrix_cell_id,
                    question_type_id,
                    answer_set,
                    set_as_current=True,
                )

                if not success:
                    raise Exception(
                        f"Failed to create answer set for cell {matrix_cell_id}"
                    )

                # Mark cell as completed
                await matrix_service.update_matrix_cell_status(
                    matrix_cell_id, MatrixCellStatus.COMPLETED
                )

                # Mark job as completed
                logger.info(f"Marking job {job_id} as completed")
                await qa_job_service.update_job_status(
                    job_id, QAJobStatus.COMPLETED, completed_at=datetime.utcnow()
                )

                logger.info(f"Successfully completed QA job {job_id}")

            finally:
                # Always release the lock
                logger.info(f"Releasing lock for matrix cell {matrix_cell_id}")
                await self.lock_provider.release_lock(lock_key, lock_token)

        except Exception as e:
            await self._handle_processing_error(
                e, job_id, matrix_cell_id, matrix_service, qa_job_service
            )
            raise
