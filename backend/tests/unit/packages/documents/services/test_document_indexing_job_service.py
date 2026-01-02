import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from packages.documents.services.document_indexing_job_service import (
    DocumentIndexingJobService,
)
from packages.documents.models.domain.document_indexing_job import (
    DocumentIndexingJobStatus,
)
from common.providers.messaging.constants import QueueName


@pytest.fixture
def indexing_job_service(test_db, mock_message_queue):
    """Create a DocumentIndexingJobService instance with mocked message queue."""
    with patch(
        "packages.documents.services.document_indexing_job_service.get_message_queue",
        return_value=mock_message_queue,
    ):
        return DocumentIndexingJobService(test_db)


class TestDocumentIndexingJobService:
    """Unit tests for DocumentIndexingJobService."""

    @pytest.mark.asyncio
    async def test_create_indexing_job(self, mock_start_span, indexing_job_service):
        """Test creating a document indexing job."""
        document_id = 1

        # Call the method
        job = await indexing_job_service.create_indexing_job(document_id)

        # Assertions
        assert job is not None
        assert job.document_id == document_id
        assert job.status == DocumentIndexingJobStatus.QUEUED.value
        assert job.id is not None

    @pytest.mark.asyncio
    async def test_get_indexing_job(self, mock_start_span, indexing_job_service):
        """Test getting an indexing job by ID."""
        # Create a job first
        job = await indexing_job_service.create_indexing_job(1)

        # Get the job
        retrieved_job = await indexing_job_service.get_indexing_job(job.id)

        # Assertions
        assert retrieved_job is not None
        assert retrieved_job.id == job.id
        assert retrieved_job.document_id == job.document_id

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, mock_start_span, indexing_job_service):
        """Test getting a non-existent job returns None."""
        result = await indexing_job_service.get_indexing_job(999999)
        assert result is None

    @pytest.mark.asyncio
    async def test_update_job_status_success(
        self, mock_start_span, indexing_job_service
    ):
        """Test updating indexing job status."""
        # Create a job first
        job = await indexing_job_service.create_indexing_job(1)

        # Update the job status to IN_PROGRESS
        success = await indexing_job_service.update_job_status(
            job.id,
            DocumentIndexingJobStatus.IN_PROGRESS,
        )

        # Assertions
        assert success is True

        # Verify the job was updated
        updated_job = await indexing_job_service.get_indexing_job(job.id)
        assert updated_job.status == DocumentIndexingJobStatus.IN_PROGRESS.value

    @pytest.mark.asyncio
    async def test_update_job_status_completed_with_timestamp(
        self, mock_start_span, indexing_job_service
    ):
        """Test updating job status to completed with completion timestamp."""
        # Create a job
        job = await indexing_job_service.create_indexing_job(1)
        completion_time = datetime.utcnow()

        # Update to completed with timestamp
        success = await indexing_job_service.update_job_status(
            job.id,
            DocumentIndexingJobStatus.COMPLETED,
            completed_at=completion_time,
        )

        # Assertions
        assert success is True

        # Verify the job was updated
        updated_job = await indexing_job_service.get_indexing_job(job.id)
        assert updated_job.status == DocumentIndexingJobStatus.COMPLETED.value
        assert updated_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_job_status_with_error_message(
        self, mock_start_span, indexing_job_service
    ):
        """Test updating job status with error message."""
        # Create a job
        job = await indexing_job_service.create_indexing_job(1)
        error_message = "Failed to connect to search index"

        # Update to failed with error message
        success = await indexing_job_service.update_job_status(
            job.id,
            DocumentIndexingJobStatus.FAILED,
            error_message=error_message,
        )

        # Assertions
        assert success is True

        # Verify the job was updated
        updated_job = await indexing_job_service.get_indexing_job(job.id)
        assert updated_job.status == DocumentIndexingJobStatus.FAILED.value
        assert updated_job.error_message == error_message

    @pytest.mark.asyncio
    async def test_update_job_status_not_found(
        self, mock_start_span, indexing_job_service
    ):
        """Test updating non-existent job returns False."""
        # Try to update non-existent job
        success = await indexing_job_service.update_job_status(
            999999, DocumentIndexingJobStatus.COMPLETED
        )

        # Assertions
        assert success is False

    @pytest.mark.asyncio
    async def test_publish_job_message_success(
        self, mock_start_span, indexing_job_service, mock_message_queue
    ):
        """Test successful message publishing."""
        # Create a job
        job = await indexing_job_service.create_indexing_job(1)

        # Call publish_job_message
        success = await indexing_job_service.publish_job_message(job)

        # Assertions
        assert success is True
        mock_message_queue.declare_queue.assert_called_once_with(
            QueueName.DOCUMENT_INDEXING
        )
        mock_message_queue.publish.assert_called_once()

        # Verify the message content
        call_args = mock_message_queue.publish.call_args
        assert call_args[0][0] == QueueName.DOCUMENT_INDEXING
        message = call_args[0][1]
        assert message["job_id"] == job.id
        assert message["document_id"] == job.document_id

        # Verify job was updated with worker_message_id
        updated_job = await indexing_job_service.get_indexing_job(job.id)
        assert updated_job.worker_message_id == str(job.id)

    @pytest.mark.asyncio
    async def test_publish_job_message_failure(
        self, mock_start_span, indexing_job_service
    ):
        """Test message publishing failure."""
        # Mock message queue to fail
        mock_failing_queue = AsyncMock()
        mock_failing_queue.declare_queue = AsyncMock(return_value=True)
        mock_failing_queue.publish = AsyncMock(return_value=False)

        with patch(
            "packages.documents.services.document_indexing_job_service.get_message_queue",
            return_value=mock_failing_queue,
        ):
            service = DocumentIndexingJobService(indexing_job_service.db_session)

            # Create a job
            job = await service.create_indexing_job(1)

            # Call publish_job_message
            success = await service.publish_job_message(job)

            # Assertions
            assert success is False

    @pytest.mark.asyncio
    async def test_publish_job_message_exception_handling(
        self, mock_start_span, indexing_job_service
    ):
        """Test message publishing handles exceptions gracefully."""
        # Mock message queue to raise exception
        mock_failing_queue = AsyncMock()
        mock_failing_queue.declare_queue = AsyncMock(
            side_effect=Exception("Queue connection failed")
        )

        with patch(
            "packages.documents.services.document_indexing_job_service.get_message_queue",
            return_value=mock_failing_queue,
        ):
            service = DocumentIndexingJobService(indexing_job_service.db_session)

            # Create a job
            job = await service.create_indexing_job(1)

            # Call publish_job_message - should not raise
            success = await service.publish_job_message(job)

            # Assertions
            assert success is False

    @pytest.mark.asyncio
    async def test_create_and_queue_job_success(
        self, mock_start_span, indexing_job_service, mock_message_queue
    ):
        """Test successful create and queue job."""
        document_id = 1

        # Call create_and_queue_job
        job = await indexing_job_service.create_and_queue_job(document_id)

        # Assertions
        assert job is not None
        assert job.document_id == document_id
        assert job.status == DocumentIndexingJobStatus.QUEUED.value

        # Verify message was published
        mock_message_queue.declare_queue.assert_called_once_with(
            QueueName.DOCUMENT_INDEXING
        )
        mock_message_queue.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_and_queue_job_publish_failure(
        self, mock_start_span, indexing_job_service
    ):
        """Test create and queue job when message publishing fails."""
        # Mock message queue to fail publishing
        mock_failing_queue = AsyncMock()
        mock_failing_queue.declare_queue = AsyncMock(return_value=True)
        mock_failing_queue.publish = AsyncMock(return_value=False)

        with patch(
            "packages.documents.services.document_indexing_job_service.get_message_queue",
            return_value=mock_failing_queue,
        ):
            service = DocumentIndexingJobService(indexing_job_service.db_session)

            # Call create_and_queue_job
            result = await service.create_and_queue_job(1)

            # Should return None due to publish failure
            assert result is None

            # Verify a job was created but marked as failed
            # We need to check if a failed job exists for this document
            jobs = await service.indexing_job_repo.get_by_document_id(1)
            assert len(jobs) == 1
            assert jobs[0].status == DocumentIndexingJobStatus.FAILED.value
            assert jobs[0].error_message == "Failed to queue job"

    @pytest.mark.asyncio
    async def test_create_and_queue_job_exception_handling(
        self, mock_start_span, indexing_job_service
    ):
        """Test create and queue job handles exceptions gracefully."""
        # Mock the repository to raise an exception
        with patch.object(
            indexing_job_service.indexing_job_repo,
            "create",
            side_effect=Exception("Database error"),
        ):
            # Call create_and_queue_job - should not raise
            result = await indexing_job_service.create_and_queue_job(1)

            # Should return None due to exception
            assert result is None

    @pytest.mark.asyncio
    async def test_multiple_jobs_for_same_document(
        self, mock_start_span, indexing_job_service, mock_message_queue
    ):
        """Test handling multiple indexing jobs for the same document."""
        document_id = 1

        # Create first job
        job1 = await indexing_job_service.create_and_queue_job(document_id)
        assert job1 is not None

        # Mark it as failed
        await indexing_job_service.update_job_status(
            job1.id,
            DocumentIndexingJobStatus.FAILED,
            error_message="First attempt failed",
        )

        # Create second job for the same document
        job2 = await indexing_job_service.create_and_queue_job(document_id)
        assert job2 is not None
        assert job2.id != job1.id

        # Verify both jobs exist
        jobs = await indexing_job_service.indexing_job_repo.get_by_document_id(
            document_id
        )
        assert len(jobs) == 2

        # Jobs should be ordered by ID descending (newest first)
        assert jobs[0].id == job2.id
        assert jobs[1].id == job1.id

    @pytest.mark.asyncio
    async def test_status_transitions(self, mock_start_span, indexing_job_service):
        """Test various status transitions for an indexing job."""
        # Create a job
        job = await indexing_job_service.create_indexing_job(1)
        assert job.status == DocumentIndexingJobStatus.QUEUED.value

        # Transition to IN_PROGRESS
        success = await indexing_job_service.update_job_status(
            job.id, DocumentIndexingJobStatus.IN_PROGRESS
        )
        assert success is True

        updated_job = await indexing_job_service.get_indexing_job(job.id)
        assert updated_job.status == DocumentIndexingJobStatus.IN_PROGRESS.value

        # Transition to COMPLETED
        completion_time = datetime.utcnow()
        success = await indexing_job_service.update_job_status(
            job.id,
            DocumentIndexingJobStatus.COMPLETED,
            completed_at=completion_time,
        )
        assert success is True

        final_job = await indexing_job_service.get_indexing_job(job.id)
        assert final_job.status == DocumentIndexingJobStatus.COMPLETED.value
        assert final_job.completed_at is not None
