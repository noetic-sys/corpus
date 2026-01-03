from typing import Dict, Optional, Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Path
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.session import get_db, get_db_readonly
from common.db.transaction_utils import transaction
from packages.documents.services.document_extraction_job_service import (
    get_document_extraction_job_service,
)
from packages.documents.services.temporal_document_extraction_service import (
    get_temporal_document_extraction_service,
)
from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.documents.repositories.document_extraction_job_repository import (
    DocumentExtractionJobRepository,
)

router = APIRouter()
logger = get_logger(__name__)


@router.post("/extraction/queue-pending", response_model=Dict[str, int])
@trace_span
async def queue_pending_documents(db: AsyncSession = Depends(get_db)):
    """Queue all pending documents for extraction processing."""
    async with transaction(db):
        extraction_job_service = get_document_extraction_job_service(db)
        result = await extraction_job_service.queue_pending_documents()
        return result


@router.post("/extraction/retry-failed", response_model=Dict[str, int])
@trace_span
async def retry_failed_extractions(
    limit: Optional[int] = 100, db: AsyncSession = Depends(get_db)
):
    """Retry failed extraction jobs by restarting Temporal workflows."""
    async with transaction(db):
        temporal_extraction_service = get_temporal_document_extraction_service(db)
        result = await temporal_extraction_service.retry_failed_jobs(limit)
        return result


@router.get("/extraction/jobs/{jobId}")
@trace_span
async def get_extraction_job(
    job_id: Annotated[int, Path(alias="jobId")],
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get extraction job details."""
    extraction_job_service = get_document_extraction_job_service(db)
    job = await extraction_job_service.get_extraction_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Extraction job not found")
    return job


@router.get("/documents/{documentId}/extraction-status")
@trace_span
async def get_document_extraction_status(
    document_id: Annotated[int, Path(alias="documentId")],
    db: AsyncSession = Depends(get_db_readonly),
):
    """Get extraction status for a document."""
    extraction_job_service = get_document_extraction_job_service(db)

    # Get document
    document = await extraction_job_service.get_document(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get extraction jobs

    job_repo = DocumentExtractionJobRepository()
    jobs = await job_repo.get_by_document_id(document_id)

    return {
        "document_id": document_id,
        "extraction_status": document.extraction_status,
        "extracted_content_path": document.extracted_content_path,
        "extraction_started_at": document.extraction_started_at,
        "extraction_completed_at": document.extraction_completed_at,
        "jobs": jobs,
    }
