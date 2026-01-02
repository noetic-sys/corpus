import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from packages.documents.repositories.document_indexing_job_repository import (
    DocumentIndexingJobRepository,
)
from packages.documents.models.domain.document_indexing_job import (
    DocumentIndexingJobStatus,
    DocumentIndexingJobCreateModel,
    DocumentIndexingJobUpdateModel,
)


class TestDocumentIndexingJobRepository:
    """Unit tests for DocumentIndexingJobRepository."""

    @pytest.fixture
    def doc_indexing_job_repo(self, test_db):
        """Create a DocumentIndexingJobRepository instance with real database session."""
        return DocumentIndexingJobRepository(test_db)

    @pytest.fixture(autouse=True)
    def setup_span_mock(self):
        """Set up the span mock to work properly with async methods."""
        # Create a mock context manager that works with async
        mock_span = MagicMock()
        mock_span.__aenter__ = AsyncMock(return_value=mock_span)
        mock_span.__aexit__ = AsyncMock(return_value=None)
        mock_span.__enter__ = MagicMock(return_value=mock_span)
        mock_span.__exit__ = MagicMock(return_value=None)

        with patch(
            "common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span",
            return_value=mock_span,
        ):
            yield

    @pytest.fixture
    def sample_doc_indexing_job_create(self):
        """Sample document indexing job create model for testing."""
        return DocumentIndexingJobCreateModel(
            document_id=1,
            status=DocumentIndexingJobStatus.QUEUED,
        )

    @pytest.mark.asyncio
    async def test_create_indexing_job(
        self, doc_indexing_job_repo, sample_doc_indexing_job_create
    ):
        """Test creating a new indexing job."""
        job = await doc_indexing_job_repo.create(sample_doc_indexing_job_create)

        assert job is not None
        assert job.document_id == 1
        assert job.status == DocumentIndexingJobStatus.QUEUED
        assert job.id > 0

    @pytest.mark.asyncio
    async def test_get_by_document_id(
        self, doc_indexing_job_repo, sample_doc_indexing_job_create
    ):
        """Test getting indexing jobs by document ID."""
        # Create test jobs for document ID 1
        job_create_1 = DocumentIndexingJobCreateModel(
            document_id=1,
            status=DocumentIndexingJobStatus.QUEUED,
        )
        job1 = await doc_indexing_job_repo.create(job_create_1)

        job_create_2 = DocumentIndexingJobCreateModel(
            document_id=1,
            status=DocumentIndexingJobStatus.COMPLETED,
        )
        job2 = await doc_indexing_job_repo.create(job_create_2)

        # Create a job for different document ID (should not be returned)
        job_create_3 = DocumentIndexingJobCreateModel(
            document_id=2,
            status=DocumentIndexingJobStatus.QUEUED,
        )
        await doc_indexing_job_repo.create(job_create_3)

        # Get jobs for document ID 1
        result = await doc_indexing_job_repo.get_by_document_id(1)

        # Assertions
        assert len(result) == 2
        assert all(job.document_id == 1 for job in result)

        # Verify ordering by ID descending (job2 should come first as it has higher ID)
        assert result[0].id > result[1].id
        assert result[0].id == job2.id
        assert result[1].id == job1.id

    @pytest.mark.asyncio
    async def test_get_by_document_id_empty(self, doc_indexing_job_repo):
        """Test getting indexing jobs for a document with no jobs."""
        result = await doc_indexing_job_repo.get_by_document_id(999)

        assert len(result) == 0
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_pending_jobs(
        self, doc_indexing_job_repo, sample_doc_indexing_job_create
    ):
        """Test getting pending indexing jobs with limit."""
        # Create jobs with different statuses
        queued_job_create_1 = DocumentIndexingJobCreateModel(
            document_id=1,
            status=DocumentIndexingJobStatus.QUEUED,
        )
        queued_job1 = await doc_indexing_job_repo.create(queued_job_create_1)

        in_progress_job_create = DocumentIndexingJobCreateModel(
            document_id=2,
            status=DocumentIndexingJobStatus.IN_PROGRESS,
        )
        await doc_indexing_job_repo.create(in_progress_job_create)

        queued_job_create_2 = DocumentIndexingJobCreateModel(
            document_id=3,
            status=DocumentIndexingJobStatus.QUEUED,
        )
        queued_job2 = await doc_indexing_job_repo.create(queued_job_create_2)

        completed_job_create = DocumentIndexingJobCreateModel(
            document_id=4,
            status=DocumentIndexingJobStatus.COMPLETED,
        )
        await doc_indexing_job_repo.create(completed_job_create)

        failed_job_create = DocumentIndexingJobCreateModel(
            document_id=5,
            status=DocumentIndexingJobStatus.FAILED,
        )
        await doc_indexing_job_repo.create(failed_job_create)

        # Get pending jobs
        result = await doc_indexing_job_repo.get_pending_jobs()

        # Should return only QUEUED jobs
        assert len(result) == 2
        assert all(job.status == DocumentIndexingJobStatus.QUEUED for job in result)

        job_ids = {job.id for job in result}
        assert queued_job1.id in job_ids
        assert queued_job2.id in job_ids

    @pytest.mark.asyncio
    async def test_get_pending_jobs_with_limit(
        self, doc_indexing_job_repo, sample_doc_indexing_job_create
    ):
        """Test getting pending jobs respects the limit parameter."""
        # Create 5 pending jobs
        for i in range(5):
            job_create = DocumentIndexingJobCreateModel(
                document_id=i + 1,
                status=DocumentIndexingJobStatus.QUEUED,
            )
            await doc_indexing_job_repo.create(job_create)

        # Get pending jobs with limit of 3
        result = await doc_indexing_job_repo.get_pending_jobs(limit=3)

        # Should return exactly 3 jobs
        assert len(result) == 3
        assert all(job.status == DocumentIndexingJobStatus.QUEUED for job in result)

    @pytest.mark.asyncio
    async def test_update_job_status(
        self, doc_indexing_job_repo, sample_doc_indexing_job_create
    ):
        """Test updating indexing job status."""
        # Create a job
        job = await doc_indexing_job_repo.create(sample_doc_indexing_job_create)
        assert job.status == DocumentIndexingJobStatus.QUEUED

        # Update status to IN_PROGRESS
        update_model = DocumentIndexingJobUpdateModel(
            status=DocumentIndexingJobStatus.IN_PROGRESS
        )
        updated_job = await doc_indexing_job_repo.update(job.id, update_model)

        assert updated_job.status == DocumentIndexingJobStatus.IN_PROGRESS
        assert updated_job.id == job.id

        # Update status to COMPLETED with completion time
        completion_time = datetime.utcnow()

        update_model = DocumentIndexingJobUpdateModel(
            status=DocumentIndexingJobStatus.COMPLETED,
            completed_at=completion_time,
        )
        updated_job = await doc_indexing_job_repo.update(job.id, update_model)

        assert updated_job.status == DocumentIndexingJobStatus.COMPLETED
        assert updated_job.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_job_with_error(
        self, doc_indexing_job_repo, sample_doc_indexing_job_create
    ):
        """Test updating job with error message."""
        # Create a job
        job = await doc_indexing_job_repo.create(sample_doc_indexing_job_create)

        # Update with error
        error_message = "Failed to connect to search index"
        update_model = DocumentIndexingJobUpdateModel(
            status=DocumentIndexingJobStatus.FAILED,
            error_message=error_message,
        )
        updated_job = await doc_indexing_job_repo.update(job.id, update_model)

        assert updated_job.status == DocumentIndexingJobStatus.FAILED
        assert updated_job.error_message == error_message

    @pytest.mark.asyncio
    async def test_get_job_by_id(
        self, doc_indexing_job_repo, sample_doc_indexing_job_create
    ):
        """Test getting a job by its ID."""
        # Create a job
        created_job = await doc_indexing_job_repo.create(sample_doc_indexing_job_create)

        # Get the job by ID
        retrieved_job = await doc_indexing_job_repo.get(created_job.id)

        assert retrieved_job is not None
        assert retrieved_job.id == created_job.id
        assert retrieved_job.document_id == created_job.document_id
        assert retrieved_job.status == created_job.status

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, doc_indexing_job_repo):
        """Test getting a job that doesn't exist."""
        result = await doc_indexing_job_repo.get(999999)
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_job(
        self, doc_indexing_job_repo, sample_doc_indexing_job_create
    ):
        """Test deleting an indexing job."""
        # Create a job
        job = await doc_indexing_job_repo.create(sample_doc_indexing_job_create)

        # Delete the job
        await doc_indexing_job_repo.delete(job.id)

        # Try to get the deleted job
        retrieved_job = await doc_indexing_job_repo.get(job.id)
        assert retrieved_job is None

    @pytest.mark.asyncio
    async def test_multiple_job_statuses_for_same_document(
        self, doc_indexing_job_repo, sample_doc_indexing_job_create
    ):
        """Test handling multiple indexing jobs for the same document."""
        document_id = 1

        # Create multiple jobs for the same document with different statuses
        job_create_1 = DocumentIndexingJobCreateModel(
            document_id=document_id,
            status=DocumentIndexingJobStatus.FAILED,
            error_message="First attempt failed",
        )
        job1 = await doc_indexing_job_repo.create(job_create_1)

        job_create_2 = DocumentIndexingJobCreateModel(
            document_id=document_id,
            status=DocumentIndexingJobStatus.QUEUED,
        )
        job2 = await doc_indexing_job_repo.create(job_create_2)

        # Get all jobs for the document
        jobs = await doc_indexing_job_repo.get_by_document_id(document_id)

        assert len(jobs) == 2

        # Check both jobs are present
        job_statuses = {job.status for job in jobs}
        assert DocumentIndexingJobStatus.FAILED in job_statuses
        assert DocumentIndexingJobStatus.QUEUED in job_statuses
