"""
Service for handling agent QA answer uploads from isolated containers.

Agents running in K8s jobs POST their answers directly to the API.
This service converts the uploaded answer data to AIAnswerSet and persists it.
"""

from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.qa.models.domain.answer_data import AIAnswerSet
from packages.qa.models.schemas.agent_qa_answer import AgentQAAnswerSetRequest
from packages.matrices.services.matrix_service import get_matrix_service
from packages.matrices.models.domain.matrix import MatrixCellStatus

logger = get_logger(__name__)


class AgentQAUploadService:
    """Service for processing agent QA answer uploads."""

    def __init__(self):
        self.matrix_service = get_matrix_service()

    @trace_span
    async def process_agent_answer_upload(
        self,
        qa_job_id: int,
        matrix_cell_id: int,
        question_type_id: int,
        answer_request: AgentQAAnswerSetRequest,
        company_id: int,
    ) -> bool:
        """
        Process an answer upload from an agent QA container.

        Converts the uploaded answer data to AIAnswerSet and persists it using
        the existing matrix_service flow.

        Args:
            qa_job_id: ID of the QA job
            matrix_cell_id: Matrix cell being processed
            question_type_id: Question type ID
            answer_request: Uploaded answer data from agent
            company_id: Company ID for access control

        Returns:
            True if answer set was successfully created
        """
        logger.info(
            f"Processing agent answer upload for QA job {qa_job_id}, "
            f"cell {matrix_cell_id}, found={answer_request.answer_found}, "
            f"answers={len(answer_request.answers)}"
        )

        # Convert request to AIAnswerSet domain object
        ai_answer_set = AIAnswerSet(
            answer_found=answer_request.answer_found, answers=answer_request.answers
        )

        # Use existing matrix service method to persist answer set
        success = await self.matrix_service.create_matrix_cell_answer_set_from_ai(
            cell_id=matrix_cell_id,
            question_type_id=question_type_id,
            ai_answer_set=ai_answer_set,
            set_as_current=True,
        )

        if not success:
            logger.error(
                f"Failed to create answer set for job {qa_job_id}, cell {matrix_cell_id}"
            )
            return False

        # Mark cell as completed (replicates qa_worker.py flow)
        await self.matrix_service.update_matrix_cell_status(
            matrix_cell_id, MatrixCellStatus.COMPLETED
        )

        logger.info(
            f"Successfully processed agent answer upload for job {qa_job_id}, "
            f"created answer set and marked cell {matrix_cell_id} as COMPLETED"
        )

        return True


def get_agent_qa_upload_service() -> AgentQAUploadService:
    """Get agent QA upload service instance.

    Returns:
        AgentQAUploadService instance
    """
    return AgentQAUploadService()
