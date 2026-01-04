from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path

from packages.auth.dependencies import get_current_active_user
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.qa.services.qa_job_service import get_qa_job_service
from packages.qa.services.agent_qa_upload_service import get_agent_qa_upload_service
from packages.qa.models.schemas.qa_job import (
    QueuePendingCellsRequest,
    QueuePendingCellsResponse,
)
from packages.qa.models.schemas.agent_qa_answer import (
    AgentQAAnswerSetRequest,
    AgentQAAnswerUploadResponse,
)
from common.core.otel_axiom_exporter import get_logger, trace_span

router = APIRouter()
logger = get_logger(__name__)


# Queue processing endpoints
@router.post("/queue/process-pending", response_model=QueuePendingCellsResponse)
async def queue_pending_cells(
    request: QueuePendingCellsRequest,
) -> QueuePendingCellsResponse:
    """Queue matrix cells in PENDING state for processing.

    If matrix_id is provided in the request, only queues cells for that specific matrix.
    Otherwise, queues all pending cells across all matrices.
    """
    qa_job_service = get_qa_job_service()
    result = await qa_job_service.queue_pending_cells(matrix_id=request.matrix_id)

    # Convert domain result to schema response
    return QueuePendingCellsResponse(
        total_pending_cells=result.total_pending_cells,
        queued=result.queued,
        failed=result.failed,
    )


# Agent QA answer upload endpoints
@router.post(
    "/qa-jobs/{qaJobId}/answer",
    response_model=AgentQAAnswerUploadResponse,
)
@trace_span
async def upload_agent_qa_answer(
    qa_job_id: Annotated[int, Path(alias="qaJobId")],
    answer_request: AgentQAAnswerSetRequest,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
) -> AgentQAAnswerUploadResponse:
    """
    Upload answer from agent QA container.

    This endpoint is called by agent QA containers running in K8s jobs.
    The agent POSTs its answer directly after processing completes.
    """
    logger.info(
        f"Received agent answer upload for QA job {qa_job_id} from company {current_user.company_id}"
    )

    # Get QA job and validate
    qa_job_service = get_qa_job_service()
    qa_job = await qa_job_service.get_qa_job(qa_job_id)

    if not qa_job:
        raise HTTPException(status_code=404, detail="QA job not found")

    # Process the answer upload
    agent_upload_service = get_agent_qa_upload_service()
    success = await agent_upload_service.process_agent_answer_upload(
        qa_job_id=qa_job_id,
        matrix_cell_id=answer_request.matrix_cell_id,
        question_type_id=answer_request.question_type_id,
        answer_request=answer_request,
        company_id=current_user.company_id,
    )

    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to process agent answer upload"
        )

    return AgentQAAnswerUploadResponse(
        qa_job_id=qa_job_id,
        matrix_cell_id=qa_job.matrix_cell_id,
        answer_count=len(answer_request.answers),
    )
