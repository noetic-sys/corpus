import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from temporalio.common import WorkflowIDConflictPolicy
from packages.documents.services.temporal_document_extraction_service import (
    TemporalDocumentExtractionService,
)
from packages.documents.models.domain.document import (
    DocumentModel,
    DocumentCreateModel,
)
from packages.documents.models.domain.document_extraction_job import (
    DocumentExtractionJobModel,
    DocumentExtractionJobStatus,
)
from packages.documents.models.database.document import ExtractionStatus


@pytest.fixture
def mock_temporal_client():
    """Create a mocked Temporal client."""
    client = AsyncMock()

    # Mock workflow handle
    mock_workflow_handle = AsyncMock()
    mock_workflow_handle.result = AsyncMock()
    mock_workflow_handle.cancel = AsyncMock()

    client.start_workflow = AsyncMock(return_value=mock_workflow_handle)
    client.get_workflow_handle = AsyncMock(return_value=mock_workflow_handle)

    return client


@pytest.fixture
def temporal_service(test_db, mock_temporal_client):
    """Create a TemporalDocumentExtractionService instance with mocked Temporal client."""
    return TemporalDocumentExtractionService(
        test_db, temporal_client=mock_temporal_client
    )


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return DocumentModel(
        id=123,
        filename="test.pdf",
        storage_key="documents/123/test.pdf",
        content_type="application/pdf",
        checksum="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
        company_id=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def sample_extraction_job():
    """Sample extraction job for testing."""
    return DocumentExtractionJobModel(
        id=789,
        document_id=123,
        status=DocumentExtractionJobStatus.QUEUED,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
class TestTemporalDocumentExtractionService:
    """Unit tests for TemporalDocumentExtractionService."""

    @pytest.mark.asyncio
    async def test_create_extraction_job(self, mock_start_span, temporal_service):
        """Test successful creation of extraction job."""
        # Create extraction job
        result = await temporal_service.create_extraction_job(123)

        # Assertions
        assert result is not None
        assert result.document_id == 123
        assert result.status == DocumentExtractionJobStatus.QUEUED

    @pytest.mark.asyncio
    async def test_get_extraction_job(
        self, mock_start_span, temporal_service, sample_extraction_job
    ):
        """Test getting extraction job by ID."""
        # First create a job
        created_job = await temporal_service.create_extraction_job(123)

        # Get the job
        result = await temporal_service.get_extraction_job(created_job.id)

        # Assertions
        assert result is not None
        assert result.id == created_job.id
        assert result.document_id == 123

    @pytest.mark.asyncio
    async def test_get_nonexistent_extraction_job(
        self, mock_start_span, temporal_service
    ):
        """Test getting non-existent extraction job returns None."""
        # Try to get non-existent job
        result = await temporal_service.get_extraction_job(99999)

        # Assertions
        assert result is None

    @pytest.mark.asyncio
    @patch("common.core.otel_axiom_exporter.propagator.inject")
    async def test_start_temporal_workflow(
        self,
        mock_inject,
        mock_start_span,
        temporal_service,
        sample_document,
        sample_extraction_job,
        mock_temporal_client,
    ):
        """Test starting Temporal workflow."""

        mock_inject.return_value = None

        # Start workflow
        workflow_id = await temporal_service.start_temporal_workflow(
            sample_document, sample_extraction_job
        )

        # Assertions
        expected_workflow_id = f"document-extraction-{sample_document.id}"
        assert workflow_id == expected_workflow_id

        # Verify Temporal client was called
        mock_temporal_client.start_workflow.assert_called_once()
        call_args = mock_temporal_client.start_workflow.call_args

        # Check that USE_EXISTING policy was used
        assert (
            call_args.kwargs["id_conflict_policy"]
            == WorkflowIDConflictPolicy.USE_EXISTING
        )

        # Verify trace context injection was called
        mock_inject.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_job_status(
        self, mock_start_span, temporal_service, sample_extraction_job
    ):
        """Test updating job status."""
        # First create a job
        created_job = await temporal_service.create_extraction_job(123)

        # Update job status
        result = await temporal_service.update_job_status(
            created_job.id,
            DocumentExtractionJobStatus.PROCESSING,
            error_message="Test error",
        )

        # Assertions
        assert result is True

    @pytest.mark.asyncio
    async def test_update_nonexistent_job_status(
        self, mock_start_span, temporal_service
    ):
        """Test updating non-existent job status returns False."""
        # Try to update non-existent job
        result = await temporal_service.update_job_status(
            99999, DocumentExtractionJobStatus.FAILED
        )

        # Assertions
        assert result is False

    @pytest.mark.asyncio
    @pytest.mark.skip
    async def test_get_workflow_status_completed(
        self, mock_start_span, temporal_service
    ):
        """Test getting workflow status when workflow is completed."""
        # Create mock workflow handle that doesn't raise exception
        mock_workflow_handle = AsyncMock()
        mock_workflow_handle.result.return_value = "workflow_completed"

        # Create mock temporal client
        mock_temporal_client = AsyncMock()
        mock_temporal_client.get_workflow_handle.return_value = mock_workflow_handle

        # Mock the get_temporal_client method on the service
        temporal_service.get_temporal_client = AsyncMock(
            return_value=mock_temporal_client
        )

        # Get workflow status
        result = await temporal_service.get_workflow_status("test-workflow-id")

        # Assertions
        assert result == "completed"
        mock_temporal_client.get_workflow_handle.assert_called_once_with(
            "test-workflow-id"
        )

    @pytest.mark.asyncio
    async def test_get_workflow_status_running(self, mock_start_span, temporal_service):
        """Test getting workflow status when workflow is still running."""
        # Create mock workflow handle that raises exception
        mock_workflow_handle = AsyncMock()
        mock_workflow_handle.result.side_effect = Exception("Workflow still running")

        # Create mock temporal client
        mock_temporal_client = AsyncMock()
        mock_temporal_client.get_workflow_handle.return_value = mock_workflow_handle

        # Mock the get_temporal_client method on the service
        temporal_service.get_temporal_client = AsyncMock(
            return_value=mock_temporal_client
        )

        # Get workflow status
        result = await temporal_service.get_workflow_status("test-workflow-id")

        # Assertions
        assert result == "running"

    @pytest.mark.asyncio
    @pytest.mark.skip
    async def test_cancel_workflow_success(self, mock_start_span, temporal_service):
        """Test successful workflow cancellation."""
        # Create mock workflow handle
        mock_workflow_handle = AsyncMock()

        # Create mock temporal client
        mock_temporal_client = AsyncMock()
        mock_temporal_client.get_workflow_handle.return_value = mock_workflow_handle

        # Mock the get_temporal_client method on the service
        temporal_service.get_temporal_client = AsyncMock(
            return_value=mock_temporal_client
        )

        # Cancel workflow
        result = await temporal_service.cancel_workflow("test-workflow-id")

        # Assertions
        assert result is True
        mock_workflow_handle.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_workflow_failure(self, mock_start_span, temporal_service):
        """Test workflow cancellation failure."""
        # Create mock workflow handle that raises exception on cancel
        mock_workflow_handle = AsyncMock()
        mock_workflow_handle.cancel.side_effect = Exception("Cancel failed")

        # Create mock temporal client
        mock_temporal_client = AsyncMock()
        mock_temporal_client.get_workflow_handle.return_value = mock_workflow_handle

        # Mock the get_temporal_client method on the service
        temporal_service.get_temporal_client = AsyncMock(
            return_value=mock_temporal_client
        )

        # Cancel workflow
        result = await temporal_service.cancel_workflow("test-workflow-id")

        # Assertions
        assert result is False

    def test_is_extractable_document_pdf(self, mock_start_span, temporal_service):
        """Test document type validation for PDF."""
        document = DocumentModel(
            id=1,
            filename="test.pdf",
            storage_key="test/test.pdf",
            content_type="application/pdf",
            checksum="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            company_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        result = temporal_service._is_extractable_document(document)
        assert result is True

    def test_is_extractable_document_unsupported(
        self, mock_start_span, temporal_service
    ):
        """Test document type validation for unsupported type."""
        document = DocumentModel(
            id=1,
            filename="test.unknown",
            storage_key="test/test.unknown",
            content_type="application/unknown",
            checksum="b665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            company_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        result = temporal_service._is_extractable_document(document)
        assert result is False

    def test_is_extractable_document_no_content_type(
        self, mock_start_span, temporal_service
    ):
        """Test document type validation when no content type."""
        document = DocumentModel(
            id=1,
            filename="test",
            storage_key="test/test",
            content_type=None,
            checksum="c665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            company_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        result = temporal_service._is_extractable_document(document)
        assert result is False

    @pytest.mark.asyncio
    async def test_create_and_start_workflow_unsupported_document(
        self, mock_start_span, temporal_service
    ):
        """Test create_and_start_workflow with unsupported document type."""
        # Create document with unsupported content type
        document = DocumentModel(
            id=123,
            filename="test.unsupported",
            storage_key="test/test.unsupported",
            content_type="application/unsupported",
            checksum="g665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            company_id=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # Try to create and start workflow
        result = await temporal_service.create_and_start_workflow(document)

        # Assertions
        assert result is None  # Should return None for unsupported document types

    @pytest.mark.asyncio
    async def test_ensure_document_extraction(
        self, mock_start_span, temporal_service, sample_company
    ):
        """Test ensure_document_extraction method."""
        # Create a real document in the database first

        doc_data = DocumentCreateModel(
            filename="test.pdf",
            storage_key="test/test.pdf",
            content_type="application/pdf",
            checksum="abc123",
            company_id=sample_company.id,
        )
        document = await temporal_service.document_repo.create(doc_data)

        # Test ensure_document_extraction
        result = await temporal_service.ensure_document_extraction(document.id)

        # Should return a workflow ID
        assert result is not None
        assert isinstance(result, str)
        assert "document-extraction-" in result

    @pytest.mark.asyncio
    async def test_ensure_document_extraction_nonexistent_document(
        self, mock_start_span, temporal_service
    ):
        """Test ensure_document_extraction with non-existent document."""
        # Test with non-existent document ID
        with pytest.raises(ValueError, match="Document 99999 not found"):
            await temporal_service.ensure_document_extraction(99999)

    @pytest.mark.asyncio
    async def test_ensure_document_extraction_unsupported_type(
        self, mock_start_span, temporal_service, sample_company
    ):
        """Test ensure_document_extraction with unsupported document type."""
        # Create document with unsupported type

        doc_data = DocumentCreateModel(
            filename="test.xyz",
            storage_key="test/test.xyz",
            content_type="application/unsupported",
            checksum="abc123_unsupported",
            company_id=sample_company.id,
        )
        document = await temporal_service.document_repo.create(doc_data)

        # Test - should raise ValueError
        with pytest.raises(ValueError, match="type not supported for extraction"):
            await temporal_service.ensure_document_extraction(document.id)

    @pytest.mark.asyncio
    @patch("common.core.otel_axiom_exporter.propagator.inject")
    async def test_retry_failed_jobs(
        self,
        mock_inject,
        mock_start_span,
        temporal_service,
        sample_company,
        mock_temporal_client,
    ):
        """Test retrying failed document extractions restarts Temporal workflows."""
        mock_inject.return_value = None

        # Create a document with FAILED extraction status
        doc_data = DocumentCreateModel(
            filename="test.pdf",
            storage_key="test/test.pdf",
            content_type="application/pdf",
            checksum="retry_test_123",
            company_id=sample_company.id,
            extraction_status=ExtractionStatus.FAILED,
        )
        document = await temporal_service.document_repo.create(doc_data)

        # Call retry_failed_jobs
        result = await temporal_service.retry_failed_jobs(limit=10)

        # Assertions
        assert result["total_failed_jobs"] == 1
        assert result["retried"] == 1
        assert result["failed"] == 0

        # Verify document status was updated to PROCESSING
        updated_document = await temporal_service.get_document(document.id)
        assert updated_document.extraction_status == ExtractionStatus.PROCESSING

        # Verify Temporal workflow was started
        mock_temporal_client.start_workflow.assert_called_once()

        # Verify an extraction job was created
        jobs = await temporal_service.extraction_job_repo.get_by_document_id(
            document.id
        )
        assert len(jobs) > 0

    @pytest.mark.asyncio
    @patch("common.core.otel_axiom_exporter.propagator.inject")
    async def test_retry_failed_jobs_workflow_start_fails(
        self,
        mock_inject,
        mock_start_span,
        temporal_service,
        sample_company,
    ):
        """Test retry_failed_jobs handles workflow start failures gracefully."""
        mock_inject.return_value = None

        # Create a document with FAILED extraction status
        doc_data = DocumentCreateModel(
            filename="test.pdf",
            storage_key="test/test.pdf",
            content_type="application/pdf",
            checksum="workflow_fail_test",
            company_id=sample_company.id,
            extraction_status=ExtractionStatus.FAILED,
        )
        document = await temporal_service.document_repo.create(doc_data)

        # Mock start_temporal_workflow to return None (failure)
        original_start = temporal_service.start_temporal_workflow
        temporal_service.start_temporal_workflow = AsyncMock(return_value=None)

        # Call retry_failed_jobs
        result = await temporal_service.retry_failed_jobs(limit=10)

        # Should fail because workflow start returned None
        assert result["total_failed_jobs"] == 1
        assert result["retried"] == 0
        assert result["failed"] == 1

        # Verify document status was reverted back to FAILED
        updated_document = await temporal_service.get_document(document.id)
        assert updated_document.extraction_status == ExtractionStatus.FAILED

        # Restore original method
        temporal_service.start_temporal_workflow = original_start
