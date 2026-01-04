from datetime import datetime

from temporalio import activity

from common.core.otel_axiom_exporter import create_span_with_context, get_logger
from common.db.session import get_db
from packages.documents.services.document_extraction_job_service import (
    get_document_extraction_job_service,
)
from packages.matrices.services.batch_processing_service import (
    get_batch_processing_service,
)
from packages.matrices.services.matrix_service import get_matrix_service
from packages.documents.repositories.document_repository import DocumentRepository
from packages.documents.models.database.document import ExtractionStatus
from packages.documents.models.domain.document import DocumentUpdateModel
from packages.documents.models.domain.document_extraction_job import (
    DocumentExtractionJobStatus,
)
from packages.documents.workflows.common import ExtractionStatusType
from packages.documents.services.document_service import get_document_service
from packages.matrices.repositories.entity_set_member_repository import (
    EntitySetMemberRepository,
)
from packages.matrices.repositories.entity_set_repository import EntitySetRepository
from packages.matrices.models.domain.matrix_enums import EntityType

logger = get_logger(__name__)


@activity.defn
async def update_extraction_status_activity(
    extraction_job_id: int,
    document_id: int,
    status: ExtractionStatusType,
    error_message: str = None,
    trace_headers: dict = None,
) -> None:
    """Update extraction job and document status.

    Note: status parameter uses StrEnum which is properly serialized by Temporal.
    """
    with create_span_with_context(
        "temporal::update_extraction_status_activity", trace_headers
    ):
        logger.info(
            f"Updating extraction status for job {extraction_job_id} to {status.value}"
        )

        async for db_session in get_db():
            try:
                extraction_job_service = get_document_extraction_job_service()
                document_repo = DocumentRepository()

                # Update job status
                if status == ExtractionStatusType.PROCESSING:
                    await extraction_job_service.update_job_status(
                        extraction_job_id, DocumentExtractionJobStatus.PROCESSING
                    )
                    document_update = DocumentUpdateModel(
                        extraction_status=ExtractionStatus.PROCESSING,
                        extraction_started_at=datetime.utcnow(),
                    )
                    await document_repo.update(document_id, document_update)
                elif status == ExtractionStatusType.FAILED:
                    await extraction_job_service.update_job_status(
                        extraction_job_id,
                        DocumentExtractionJobStatus.FAILED,
                        error_message=error_message,
                    )
                    document_update = DocumentUpdateModel(
                        extraction_status=ExtractionStatus.FAILED,
                    )
                    await document_repo.update(document_id, document_update)

                await db_session.commit()
                break

            except Exception as e:
                logger.error(f"Error updating extraction status: {e}")
                await db_session.rollback()
                raise


@activity.defn
async def update_document_content_path_activity(
    document_id: int, s3_key: str, trace_headers: dict = None
) -> None:
    """Update document with S3 content path (without marking complete).

    This allows chunking to download content via API before marking document complete.
    """
    with create_span_with_context(
        "temporal::update_document_content_path_activity", trace_headers
    ):
        logger.info(f"Updating content path for document {document_id} to {s3_key}")

        async for db_session in get_db():
            try:
                document_repo = DocumentRepository()

                # Update only the S3 path, keep status as PROCESSING
                document_update = DocumentUpdateModel(
                    extracted_content_path=s3_key,
                )
                await document_repo.update(document_id, document_update)
                await db_session.commit()

                logger.info(f"Updated content path for document {document_id}")
                break

            except Exception as e:
                logger.error(f"Error updating document content path: {e}")
                await db_session.rollback()
                raise


@activity.defn
async def update_document_completion_activity(
    document_id: int, extraction_job_id: int, s3_key: str, trace_headers: dict = None
) -> None:
    """Update document with completion status. Does NOT trigger QA jobs - use queue_qa_jobs_for_document_activity for that."""
    with create_span_with_context(
        "temporal::update_document_completion_activity", trace_headers
    ):
        logger.info(f"Completing document extraction for document {document_id}")

        async for db_session in get_db():
            try:
                extraction_job_service = get_document_extraction_job_service()
                document_repo = DocumentRepository()

                # Update document status
                document_update = DocumentUpdateModel(
                    extracted_content_path=s3_key,
                    extraction_status=ExtractionStatus.COMPLETED,
                    extraction_completed_at=datetime.utcnow(),
                )
                await document_repo.update(document_id, document_update)

                # Mark job as completed
                await extraction_job_service.update_job_status(
                    extraction_job_id,
                    DocumentExtractionJobStatus.COMPLETED,
                    completed_at=datetime.utcnow(),
                    extracted_content_path=s3_key,
                )

                # Commit the transaction so QA workers can see the updated document
                await db_session.commit()

                logger.info(
                    f"Successfully completed extraction for document {document_id}"
                )
                break

            except Exception as e:
                logger.error(f"Error completing document extraction: {e}")
                await db_session.rollback()
                raise


@activity.defn
async def queue_qa_jobs_for_document_activity(
    document_id: int, trace_headers: dict = None
) -> int:
    """
    Queue QA jobs for all matrices that use this document.

    This is separated from update_document_completion_activity to allow independent
    retry policies. The document status update should be fast and reliable, while
    QA job queueing can be slow due to matrix cell lookups and job creation.

    Returns the number of QA jobs queued.
    """
    with create_span_with_context(
        "temporal::queue_qa_jobs_for_document_activity", trace_headers
    ):
        logger.info(f"Queueing QA jobs for document {document_id}")

        async for db_session in get_db():
            try:
                matrix_service = get_matrix_service(db_session)
                batch_processing_service = get_batch_processing_service(db_session)
                member_repo = EntitySetMemberRepository()
                entity_set_repo = EntitySetRepository()

                # Get all entity set members for this document
                members = await member_repo.get_members_by_entity_id(
                    document_id, EntityType.DOCUMENT
                )
                logger.info(
                    f"Found {len(members)} entity set members for document {document_id}"
                )

                # Group by entity set to get unique entity sets and their matrices
                entity_set_ids = list(set(member.entity_set_id for member in members))
                entity_sets = await entity_set_repo.get_by_ids(entity_set_ids)
                logger.info(
                    f"Found {len(entity_sets)} entity sets: {[(es.id, es.matrix_id, es.name) for es in entity_sets]}"
                )

                # Get cells for each matrix
                all_matrix_cells = []
                for entity_set in entity_sets:
                    matrix_cells = await matrix_service.get_matrix_cells_by_document(
                        entity_set.matrix_id, document_id, entity_set.id
                    )
                    logger.info(
                        f"Found {len(matrix_cells)} cells for entity_set {entity_set.id} "
                        f"(matrix {entity_set.matrix_id}, name '{entity_set.name}')"
                    )
                    all_matrix_cells.extend(matrix_cells)

                matrix_ids = list(set(es.matrix_id for es in entity_sets))

                queued_count = 0
                if all_matrix_cells:
                    queued_count = (
                        await batch_processing_service.create_jobs_and_queue_for_cells(
                            all_matrix_cells
                        )
                    )
                    logger.info(
                        f"Queued {queued_count} QA jobs across {len(matrix_ids)} matrices for document {document_id}"
                    )
                else:
                    logger.info(
                        f"No matrix cells found for document {document_id}, skipping QA job queueing"
                    )

                return queued_count

            except Exception as e:
                logger.error(f"Error queueing QA jobs for document {document_id}: {e}")
                raise


@activity.defn
async def get_document_details_activity(
    document_id: int, trace_headers: dict = None
) -> dict:
    """Get document details including file_type and content_type."""
    with create_span_with_context(
        "temporal::get_document_details_activity", trace_headers
    ):
        logger.info(f"Getting document details for document {document_id}")

        async for db_session in get_db():
            try:
                document_service = get_document_service(db_session)
                document = await document_service.get_document(document_id)

                if not document:
                    raise ValueError(f"Document {document_id} not found")

                file_type = document_service.get_file_type_from_document(document)

                result = {
                    "file_type": file_type,
                    "content_type": document.content_type,
                    "company_id": document.company_id,
                }

                logger.info(
                    f"Document {document_id} details: file_type={file_type}, content_type={document.content_type}, company_id={document.company_id}"
                )
                return result

            except Exception as e:
                logger.error(f"Error getting document details: {e}")
                raise
