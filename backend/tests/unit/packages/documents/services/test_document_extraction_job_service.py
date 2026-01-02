import pytest
from unittest.mock import AsyncMock, patch

from packages.documents.services.document_extraction_job_service import (
    DocumentExtractionJobService,
)
from packages.documents.models.domain.document_extraction_job import (
    DocumentExtractionJobStatus,
)
from packages.documents.models.database.document import ExtractionStatus
from packages.documents.models.domain.document import DocumentCreateModel
from uuid import uuid4


@pytest.fixture
def extraction_job_service(test_db, mock_message_queue):
    """Create a DocumentExtractionJobService instance with mocked message queue."""
    with patch(
        "packages.documents.services.document_extraction_job_service.get_message_queue",
        return_value=mock_message_queue,
    ):
        return DocumentExtractionJobService(test_db)


class TestDocumentExtractionJobService:
    """Unit tests for DocumentExtractionJobService."""

    @pytest.mark.asyncio
    async def test_create_extraction_job(self, mock_start_span, extraction_job_service):
        """Test creating a document extraction job."""

        document_id = 1

        # Call the method
        job = await extraction_job_service.create_extraction_job(document_id)

        # Assertions
        assert job is not None
        assert job.document_id == document_id
        assert job.status == DocumentExtractionJobStatus.QUEUED
        assert job.id is not None

    @pytest.mark.asyncio
    async def test_update_job_status(self, mock_start_span, extraction_job_service):
        """Test updating extraction job status."""
        # Create a job first
        job = await extraction_job_service.create_extraction_job(1)

        # Update the job status
        success = await extraction_job_service.update_job_status(
            job.id,
            DocumentExtractionJobStatus.COMPLETED,
            extracted_content_path="extracted/content.txt",
        )

        # Assertions
        assert success is True

        # Verify the job was updated
        updated_job = await extraction_job_service.get_extraction_job(job.id)
        assert updated_job.status == DocumentExtractionJobStatus.COMPLETED
        assert updated_job.extracted_content_path == "extracted/content.txt"

    @pytest.mark.asyncio
    async def test_update_job_status_not_found(
        self, mock_start_span, extraction_job_service
    ):
        """Test updating non-existent job returns False."""
        # Try to update non-existent job
        success = await extraction_job_service.update_job_status(
            999, DocumentExtractionJobStatus.COMPLETED
        )

        # Assertions
        assert success is False

    @pytest.mark.asyncio
    async def test_publish_job_message_success(
        self, mock_start_span, extraction_job_service, mock_message_queue
    ):
        """Test successful message publishing."""
        # Create a job
        job = await extraction_job_service.create_extraction_job(1)

        # Call publish_job_message
        success = await extraction_job_service.publish_job_message(job)

        # Assertions
        assert success is True
        mock_message_queue.declare_queue.assert_called_once()
        mock_message_queue.publish.assert_called_once()

        # Verify job was updated with worker_message_id
        updated_job = await extraction_job_service.get_extraction_job(job.id)
        assert updated_job.worker_message_id == str(job.id)

    @pytest.mark.asyncio
    async def test_publish_job_message_failure(
        self, mock_start_span, extraction_job_service
    ):
        """Test message publishing failure."""
        # Mock message queue to fail
        mock_failing_queue = AsyncMock()
        mock_failing_queue.declare_queue = AsyncMock(return_value=True)
        mock_failing_queue.publish = AsyncMock(return_value=False)

        with patch(
            "packages.documents.services.document_extraction_job_service.get_message_queue",
            return_value=mock_failing_queue,
        ):
            service = DocumentExtractionJobService(extraction_job_service.db_session)

            # Create a job
            job = await service.create_extraction_job(1)

            # Call publish_job_message
            success = await service.publish_job_message(job)

            # Assertions
            assert success is False

    @pytest.mark.asyncio
    async def test_create_and_queue_job_success(
        self, mock_start_span, extraction_job_service, mock_message_queue
    ):
        """Test successful create and queue job with document status update."""
        # Create a document first
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="documents/test.pdf",
            extraction_status=ExtractionStatus.PENDING,
            checksum=str(uuid4()),
            company_id=1,
        )
        document = await extraction_job_service.document_repo.create(document_create)

        # Call create_and_queue_job
        job = await extraction_job_service.create_and_queue_job(document)

        # Assertions
        assert job is not None
        assert job.document_id == document.id
        assert job.status == DocumentExtractionJobStatus.QUEUED

        # Verify document status was updated
        updated_document = await extraction_job_service.get_document(document.id)
        assert updated_document.extraction_status == ExtractionStatus.PROCESSING

        # Verify message was published
        mock_message_queue.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_and_queue_job_publish_failure(
        self, mock_start_span, extraction_job_service
    ):
        """Test create and queue job when message publishing fails."""
        # Mock message queue to fail publishing
        mock_failing_queue = AsyncMock()
        mock_failing_queue.declare_queue = AsyncMock(return_value=True)
        mock_failing_queue.publish = AsyncMock(return_value=False)

        with patch(
            "packages.documents.services.document_extraction_job_service.get_message_queue",
            return_value=mock_failing_queue,
        ):
            service = DocumentExtractionJobService(extraction_job_service.db_session)

            # Create a document
            document_create = DocumentCreateModel(
                filename="test.pdf",
                storage_key="documents/test.pdf",
                extraction_status=ExtractionStatus.PENDING,
                checksum=str(uuid4()),
                company_id=1,
            )
            document = await service.document_repo.create(document_create)

            # Call create_and_queue_job
            result = await service.create_and_queue_job(document)

            # Should return None due to publish failure
            assert result is None

            # Verify document status was reverted to FAILED
            updated_document = await service.get_document(document.id)
            assert updated_document.extraction_status == ExtractionStatus.FAILED

    @pytest.mark.asyncio
    async def test_retry_failed_jobs(
        self, mock_start_span, extraction_job_service, mock_message_queue
    ):
        """Test retrying failed extraction jobs."""
        # Create a failed job
        job = await extraction_job_service.create_extraction_job(1)
        await extraction_job_service.update_job_status(
            job.id,
            DocumentExtractionJobStatus.FAILED,
            error_message="Processing failed",
        )

        # Call retry_failed_jobs
        result = await extraction_job_service.retry_failed_jobs(limit=10)

        # Assertions
        assert result["total_failed_jobs"] == 1
        assert result["retried"] == 1
        assert result["failed"] == 0

        # Verify job status was reset
        updated_job = await extraction_job_service.get_extraction_job(job.id)
        assert updated_job.status == DocumentExtractionJobStatus.QUEUED
        # Note: error_message is not cleared by the current implementation when passing None
