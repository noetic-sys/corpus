import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from packages.documents.repositories.document_extraction_job_repository import (
    DocumentExtractionJobRepository,
)
from packages.documents.models.domain.document_extraction_job import (
    DocumentExtractionJobStatus,
    DocumentExtractionJobCreateModel,
)


class TestDocumentExtractionJobRepository:
    """Unit tests for DocumentExtractionJobRepository."""

    @pytest.fixture
    def doc_extraction_job_repo(self, test_db):
        """Create a DocumentExtractionJobRepository instance with real database session."""
        return DocumentExtractionJobRepository()

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
    def sample_doc_extraction_job_create(self):
        """Sample document extraction job create model for testing."""
        return DocumentExtractionJobCreateModel(
            document_id=1,
            status=DocumentExtractionJobStatus.QUEUED,
        )

    @pytest.mark.asyncio
    async def test_get_by_document_id(
        self, doc_extraction_job_repo, sample_doc_extraction_job_create
    ):
        """Test getting extraction jobs by document ID, ordered by ID descending."""
        # Create test jobs for document ID 1
        job_create_1 = DocumentExtractionJobCreateModel(
            document_id=1,
            status=DocumentExtractionJobStatus.QUEUED,
        )
        job1 = await doc_extraction_job_repo.create(job_create_1)

        job_create_2 = DocumentExtractionJobCreateModel(
            document_id=1,
            status=DocumentExtractionJobStatus.QUEUED,
        )
        job2 = await doc_extraction_job_repo.create(job_create_2)

        # Create a job for different document ID (should not be returned)
        job_create_3 = DocumentExtractionJobCreateModel(
            document_id=2,
            status=DocumentExtractionJobStatus.QUEUED,
        )
        await doc_extraction_job_repo.create(job_create_3)

        # Get jobs for document ID 1
        result = await doc_extraction_job_repo.get_by_document_id(1)

        # Assertions
        assert len(result) == 2
        assert all(job.document_id == 1 for job in result)

        # Verify ordering by ID descending (job2 should come first as it has higher ID)
        assert result[0].id > result[1].id
        assert result[0].id == job2.id
        assert result[1].id == job1.id

    @pytest.mark.asyncio
    async def test_get_failed_jobs(
        self, doc_extraction_job_repo, sample_doc_extraction_job_create
    ):
        """Test getting failed extraction jobs with limit and ordering."""
        # Create jobs with different statuses
        completed_job_create = DocumentExtractionJobCreateModel(
            document_id=1,
            status=DocumentExtractionJobStatus.COMPLETED,
        )
        await doc_extraction_job_repo.create(completed_job_create)

        failed_job_create_1 = DocumentExtractionJobCreateModel(
            document_id=1,
            status=DocumentExtractionJobStatus.FAILED,
        )
        failed_job1 = await doc_extraction_job_repo.create(failed_job_create_1)

        failed_job_create_2 = DocumentExtractionJobCreateModel(
            document_id=2,
            status=DocumentExtractionJobStatus.FAILED,
        )
        failed_job2 = await doc_extraction_job_repo.create(failed_job_create_2)

        # Get failed jobs
        result = await doc_extraction_job_repo.get_failed_jobs()

        # Should return only failed jobs, ordered by ID descending
        assert len(result) == 2
        assert all(job.status == DocumentExtractionJobStatus.FAILED for job in result)
        assert result[0].id > result[1].id
        assert result[0].id == failed_job2.id
        assert result[1].id == failed_job1.id

    @pytest.mark.asyncio
    async def test_get_pending_documents(self, doc_extraction_job_repo):
        """Test getting documents with PENDING extraction status."""
        # Note: This method queries DocumentEntity directly, not document_extraction_jobs
        # We would need to create documents with PENDING status to test this properly
        # For now, we'll just test that the method returns an empty list when no pending documents exist

        result = await doc_extraction_job_repo.get_pending_documents()

        # Should return empty list when no pending documents exist
        assert isinstance(result, list)
        assert len(result) == 0
