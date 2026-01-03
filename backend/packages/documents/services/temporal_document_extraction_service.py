from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy

from common.core.config import settings
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
from packages.documents.models.domain.document_types import DocumentType
from packages.documents.models.database.document import ExtractionStatus
from packages.documents.workflows.document_extraction_workflow import (
    DocumentExtractionWorkflow,
)
from packages.documents.workflows.common import DocumentProcessingInput, TaskQueueType
from common.core.otel_axiom_exporter import trace_span, propagator, get_logger

logger = get_logger(__name__)


class TemporalDocumentExtractionService:
    """Service for handling document extraction using Temporal workflows."""

    def __init__(
        self, db_session: AsyncSession, temporal_client: Optional[Client] = None
    ):
        self.db_session = db_session
        self.extraction_job_repo = DocumentExtractionJobRepository()
        self.document_repo = DocumentRepository(db_session)
        self._temporal_client = temporal_client

    async def get_temporal_client(self) -> Client:
        """Get or create Temporal client."""
        if self._temporal_client is None:
            # Connect to Temporal server
            temporal_host = getattr(settings, "temporal_host", "localhost:7233")
            self._temporal_client = await Client.connect(temporal_host)
        return self._temporal_client

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
    async def start_temporal_workflow(
        self, document: DocumentModel, extraction_job: DocumentExtractionJobModel
    ) -> str:
        """Start the Temporal workflow for document extraction."""
        logger.info(f"Starting Temporal workflow for document {document.id}")

        try:
            temporal_client = await self.get_temporal_client()

            # Extract current trace context
            trace_headers = {}
            propagator.inject(trace_headers)

            # Create workflow input for any document type
            workflow_input = DocumentProcessingInput(
                document_id=document.id,
                # document_url=f"s3://{settings.s3_bucket_name}/{document.storage_key}",
                # file_type=self._get_file_type_from_document(document),
                matrix_id=None,  # Documents are now standalone, no matrix association needed for extraction
                extraction_job_id=extraction_job.id,
                trace_headers=trace_headers,
            )

            # Start the workflow with deterministic ID for deduplication
            workflow_id = f"document-extraction-{document.id}"

            _ = await temporal_client.start_workflow(
                DocumentExtractionWorkflow.run,
                workflow_input,
                id=workflow_id,
                task_queue=TaskQueueType.DOCUMENT_ROUTING.value,
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
            )

            logger.info(
                f"Started Temporal workflow {workflow_id} for document {document.id}"
            )

            # Update job with workflow ID
            update_model = DocumentExtractionJobUpdateModel(
                worker_message_id=workflow_id
            )
            await self.extraction_job_repo.update(extraction_job.id, update_model)

            return workflow_id

        except Exception as e:
            logger.error(
                f"Error starting Temporal workflow for document {document.id}: {e}"
            )
            raise

    @trace_span
    async def create_and_start_workflow(
        self, document: DocumentModel
    ) -> Optional[DocumentExtractionJobModel]:
        """Create an extraction job and start the Temporal workflow."""
        try:
            # Check if document type is supported for extraction
            if not self._is_extractable_document(document):
                logger.info(
                    f"Document {document.id} type not supported for extraction, skipping Temporal workflow"
                )
                return None

            # Create extraction job
            extraction_job = await self.create_extraction_job(document.id)

            # Update document extraction status to PROCESSING
            document_update = DocumentUpdateModel(
                extraction_status=ExtractionStatus.PROCESSING
            )
            await self.document_repo.update(document.id, document_update)

            # Start Temporal workflow
            workflow_id = await self.start_temporal_workflow(document, extraction_job)

            logger.info(
                f"Successfully created and started workflow {workflow_id} for document {document.id}"
            )
            return extraction_job

        except Exception as e:
            logger.error(
                f"Error creating and starting workflow for document {document.id}: {e}",
                exc_info=True,
            )
            # Mark job as failed if it was created
            if "extraction_job" in locals():
                await self.update_job_status(
                    extraction_job.id,
                    DocumentExtractionJobStatus.FAILED,
                    f"Failed to start workflow: {str(e)}",
                )
                # Revert document status
                document_update = DocumentUpdateModel(
                    extraction_status=ExtractionStatus.FAILED
                )
                await self.document_repo.update(document.id, document_update)
            return None

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
    async def get_workflow_status(self, workflow_id: str) -> Optional[str]:
        """Get the status of a Temporal workflow."""
        try:
            temporal_client = await self.get_temporal_client()

            workflow_handle = temporal_client.get_workflow_handle(workflow_id)

            # Check if workflow is running
            try:
                _ = await workflow_handle.result()
                return "completed"
            except Exception:
                # Workflow might still be running
                return "running"

        except Exception as e:
            logger.error(f"Error getting workflow status for {workflow_id}: {e}")
            return "unknown"

    @trace_span
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running Temporal workflow."""
        try:
            temporal_client = await self.get_temporal_client()

            workflow_handle = temporal_client.get_workflow_handle(workflow_id)
            await workflow_handle.cancel()

            logger.info(f"Cancelled workflow {workflow_id}")
            return True

        except Exception as e:
            logger.error(f"Error cancelling workflow {workflow_id}: {e}")
            return False

    def _is_extractable_document(self, document: DocumentModel) -> bool:
        """Check if document type is supported for extraction via Temporal."""
        # Try by MIME type first
        if document.content_type:
            doc_type = DocumentType.from_mime_type(document.content_type)
            if doc_type:
                return doc_type.value.is_extractable

        # Fallback to filename
        if document.filename:
            doc_type = DocumentType.from_filename(document.filename)
            if doc_type:
                return doc_type.value.is_extractable

        return False

    @trace_span
    async def get_document(self, document_id: int) -> Optional[DocumentModel]:
        """Get a document by ID."""
        return await self.document_repo.get(document_id)

    @trace_span
    async def retry_failed_jobs(self, limit: int = 100) -> dict[str, int]:
        """Retry failed document extractions by restarting their workflows.

        NOTE: Queries documents with extraction_status='failed', NOT extraction jobs.
        """
        logger.info(f"Retrying up to {limit} failed document extractions")

        # Get failed documents (not failed jobs)
        failed_documents = await self.document_repo.get_failed_extraction_documents(
            company_id=None, limit=limit
        )

        retried_count = 0
        failed_count = 0

        for document in failed_documents:
            try:
                # Create or get extraction job for this document
                job = await self.create_extraction_job(document.id)

                # Update document extraction status to PROCESSING
                document_update = DocumentUpdateModel(
                    extraction_status=ExtractionStatus.PROCESSING
                )
                await self.document_repo.update(document.id, document_update)

                # Start new workflow
                workflow_id = await self.start_temporal_workflow(document, job)

                if workflow_id:
                    retried_count += 1
                    logger.info(
                        f"Successfully retried extraction for document {document.id} with workflow {workflow_id}"
                    )
                else:
                    failed_count += 1
                    # Revert document status back to FAILED
                    document_update = DocumentUpdateModel(
                        extraction_status=ExtractionStatus.FAILED
                    )
                    await self.document_repo.update(document.id, document_update)

            except Exception as e:
                logger.error(
                    f"Error retrying extraction for document {document.id}: {e}",
                    exc_info=True,
                )
                failed_count += 1
                # Try to revert document status back to FAILED
                try:
                    document_update = DocumentUpdateModel(
                        extraction_status=ExtractionStatus.FAILED
                    )
                    await self.document_repo.update(document.id, document_update)
                except Exception as update_error:
                    logger.error(
                        f"Error reverting document status for document {document.id}: {update_error}"
                    )

        logger.info(f"Retry complete: {retried_count} retried, {failed_count} failed")

        return {
            "total_failed_jobs": len(failed_documents),
            "retried": retried_count,
            "failed": failed_count,
        }

    @trace_span
    async def ensure_document_extraction(self, document_id: int) -> str:
        """Ensure document extraction is running. Returns workflow ID.

        This method is idempotent - it will start extraction if not already running,
        or return the existing workflow ID if already in progress.
        """
        logger.info(f"Ensuring document {document_id} extraction is running")

        try:
            # Get the document
            document = await self.get_document(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")

            # Check if document type is supported for extraction
            if not self._is_extractable_document(document):
                logger.info(f"Document {document_id} type not supported for extraction")
                raise ValueError(
                    f"Document {document_id} type not supported for extraction"
                )

            # Check if already completed
            if document.extraction_status == ExtractionStatus.COMPLETED:
                logger.info(f"Document {document_id} already extracted")
                return (
                    f"document-extraction-{document_id}"  # Return expected workflow ID
                )

            # Create extraction job (this is safe to call multiple times)
            extraction_job = await self.create_extraction_job(document_id)

            # Start workflow with USE_EXISTING policy (deduplication handled by Temporal)
            workflow_id = await self.start_temporal_workflow(document, extraction_job)

            logger.info(
                f"Ensured extraction workflow {workflow_id} for document {document_id}"
            )
            return workflow_id

        except Exception as e:
            logger.error(f"Error ensuring extraction for document {document_id}: {e}")
            raise


def get_temporal_document_extraction_service(
    db_session: AsyncSession,
) -> TemporalDocumentExtractionService:
    """Get Temporal document extraction service instance."""
    return TemporalDocumentExtractionService(db_session)
