import pytest
from unittest.mock import patch, MagicMock

from packages.documents.workflows.activities.database_operations import (
    update_extraction_status_activity,
    update_document_completion_activity,
)
from packages.documents.workflows.common import ExtractionStatusType
from packages.documents.repositories.document_repository import DocumentRepository
from packages.documents.repositories.document_extraction_job_repository import (
    DocumentExtractionJobRepository,
)
from packages.documents.models.domain.document import DocumentCreateModel
from packages.documents.models.domain.document_extraction_job import (
    DocumentExtractionJobCreateModel,
    DocumentExtractionJobStatus,
)
from packages.matrices.repositories.matrix_repository import MatrixRepository
from packages.documents.models.database.document import ExtractionStatus


@patch(
    "packages.documents.workflows.activities.database_operations.create_span_with_context"
)
@patch("packages.documents.workflows.activities.database_operations.get_db")
class TestUpdateExtractionStatusActivity:
    """Unit tests for update_extraction_status_activity."""

    @pytest.mark.asyncio
    async def test_update_extraction_status_processing(
        self,
        mock_get_db,
        mock_create_span,
        test_db,
        sample_company,
    ):
        """Test updating extraction status to PROCESSING."""

        # Mock get_db to yield our test database session
        async def mock_db_generator():
            yield test_db

        mock_get_db.return_value = mock_db_generator()

        # Create test data in the database
        document_repo = DocumentRepository()
        job_repo = DocumentExtractionJobRepository()

        # Create a document
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="docs/test.pdf",
            content_type="application/pdf",
            extraction_status=ExtractionStatus.PENDING,
            checksum="1234567890",
            company_id=sample_company.id,
        )
        document = await document_repo.create(document_create)

        # Create an extraction job
        job_create = DocumentExtractionJobCreateModel(
            document_id=document.id, status=DocumentExtractionJobStatus.QUEUED
        )
        job = await job_repo.create(job_create)

        await test_db.commit()

        # Call the activity with real database operations
        await update_extraction_status_activity(
            extraction_job_id=job.id,
            document_id=document.id,
            status=ExtractionStatusType.PROCESSING,
            trace_headers={"trace-id": "12345"},
        )

        # Verify span was created with correct parameters
        mock_create_span.assert_called_once_with(
            "temporal::update_extraction_status_activity", {"trace-id": "12345"}
        )

        # Verify database changes by fetching fresh from DB
        updated_document = await document_repo.get(document.id)
        updated_job = await job_repo.get(job.id)

        assert updated_document.extraction_status == ExtractionStatus.PROCESSING
        assert updated_document.extraction_started_at is not None
        assert updated_job.status == DocumentExtractionJobStatus.PROCESSING

    @pytest.mark.asyncio
    async def test_update_extraction_status_failed(
        self,
        mock_get_db,
        mock_create_span,
        test_db,
        sample_company,
    ):
        """Test updating extraction status to FAILED."""

        # Mock get_db to yield our test database session
        async def mock_db_generator():
            yield test_db

        mock_get_db.return_value = mock_db_generator()

        # Create test data in the database
        document_repo = DocumentRepository()
        job_repo = DocumentExtractionJobRepository()

        # Create a document
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="docs/test.pdf",
            content_type="application/pdf",
            extraction_status=ExtractionStatus.PROCESSING,
            checksum="1234567890",
            company_id=sample_company.id,
        )
        document = await document_repo.create(document_create)

        # Create an extraction job
        job_create = DocumentExtractionJobCreateModel(
            document_id=document.id, status=DocumentExtractionJobStatus.PROCESSING
        )
        job = await job_repo.create(job_create)

        await test_db.commit()

        # Call the activity with real database operations
        await update_extraction_status_activity(
            extraction_job_id=job.id,
            document_id=document.id,
            status=ExtractionStatusType.FAILED,
            error_message="Extraction failed",
        )

        # Verify span was created with correct parameters
        mock_create_span.assert_called_once_with(
            "temporal::update_extraction_status_activity", None
        )

        # Verify database changes by fetching fresh from DB
        updated_document = await document_repo.get(document.id)
        updated_job = await job_repo.get(job.id)

        assert updated_document.extraction_status == ExtractionStatus.FAILED
        assert updated_job.status == DocumentExtractionJobStatus.FAILED
        assert updated_job.error_message == "Extraction failed"

    @pytest.mark.asyncio
    async def test_update_extraction_status_no_trace_headers(
        self,
        mock_get_db,
        mock_create_span,
        test_db,
        sample_company,
    ):
        """Test updating extraction status without trace headers."""

        # Mock get_db to yield our test database session
        async def mock_db_generator():
            yield test_db

        mock_get_db.return_value = mock_db_generator()

        # Create test data in the database
        document_repo = DocumentRepository()
        job_repo = DocumentExtractionJobRepository()

        # Create a document
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="docs/test.pdf",
            content_type="application/pdf",
            extraction_status=ExtractionStatus.PENDING,
            checksum="1234567890",
            company_id=sample_company.id,
        )
        document = await document_repo.create(document_create)

        # Create an extraction job
        job_create = DocumentExtractionJobCreateModel(
            document_id=document.id, status=DocumentExtractionJobStatus.QUEUED
        )
        job = await job_repo.create(job_create)

        await test_db.commit()

        # Call the activity without trace headers
        await update_extraction_status_activity(
            extraction_job_id=job.id,
            document_id=document.id,
            status=ExtractionStatusType.PROCESSING,
        )

        # Verify span was created with None trace headers
        mock_create_span.assert_called_once_with(
            "temporal::update_extraction_status_activity", None
        )

        # Verify database changes by fetching fresh from DB
        updated_document = await document_repo.get(document.id)
        updated_job = await job_repo.get(job.id)

        assert updated_document.extraction_status == ExtractionStatus.PROCESSING
        assert updated_document.extraction_started_at is not None
        assert updated_job.status == DocumentExtractionJobStatus.PROCESSING


@patch(
    "packages.documents.workflows.activities.database_operations.create_span_with_context"
)
@patch("packages.documents.workflows.activities.database_operations.get_db")
@patch(
    "packages.matrices.services.batch_processing_service.get_message_queue"
)  # Mock the RabbitMQ queueing
class TestUpdateDocumentCompletionActivity:
    """Unit tests for update_document_completion_activity."""

    @pytest.mark.asyncio
    async def test_update_document_completion_success(
        self,
        mock_get_message_queue,
        mock_get_db,
        mock_create_span,
        test_db,
        sample_company,
        sample_workspace,
        sample_matrix,
    ):
        """Test successful document completion."""

        # Mock get_db to yield our test database session
        async def mock_db_generator():
            yield test_db

        mock_get_db.return_value = mock_db_generator()

        # Mock the message queue to prevent actual RabbitMQ calls
        mock_message_queue = MagicMock()
        mock_message_queue.declare_queue = MagicMock()
        mock_message_queue.publish = MagicMock(return_value=True)
        mock_get_message_queue.return_value = mock_message_queue

        # Create test data in the database
        matrix_repo = MatrixRepository()
        document_repo = DocumentRepository()
        job_repo = DocumentExtractionJobRepository()

        # Create a workspace first
        workspace = sample_workspace

        # Create a document
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="docs/test.pdf",
            content_type="application/pdf",
            extraction_status=ExtractionStatus.PROCESSING,
            checksum="1234567890",
            company_id=sample_company.id,
        )
        document = await document_repo.create(document_create)

        # Create an extraction job
        job_create = DocumentExtractionJobCreateModel(
            document_id=document.id, status=DocumentExtractionJobStatus.PROCESSING
        )
        job = await job_repo.create(job_create)

        await test_db.commit()

        # Call the activity with real database operations
        await update_document_completion_activity(
            document_id=document.id,
            extraction_job_id=job.id,
            s3_key="extracted/789/456_extracted.md",
            trace_headers={"trace-id": "12345"},
        )

        # Verify span was created with correct parameters
        mock_create_span.assert_called_once_with(
            "temporal::update_document_completion_activity", {"trace-id": "12345"}
        )

        # Verify database changes by fetching fresh from DB
        updated_document = await document_repo.get(document.id)
        updated_job = await job_repo.get(job.id)

        assert updated_document.extraction_status == ExtractionStatus.COMPLETED
        assert updated_document.extraction_completed_at is not None
        assert (
            updated_document.extracted_content_path == "extracted/789/456_extracted.md"
        )
        assert updated_job.status == DocumentExtractionJobStatus.COMPLETED
        assert updated_job.completed_at is not None
        assert updated_job.extracted_content_path == "extracted/789/456_extracted.md"

    @pytest.mark.asyncio
    async def test_update_document_completion_no_trace_headers(
        self,
        mock_get_message_queue,
        mock_get_db,
        mock_create_span,
        test_db,
        sample_workspace,
        sample_company,
        sample_matrix,
    ):
        """Test document completion without trace headers."""

        # Mock get_db to yield our test database session
        async def mock_db_generator():
            yield test_db

        mock_get_db.return_value = mock_db_generator()

        # Mock the message queue to prevent actual RabbitMQ calls
        mock_message_queue = MagicMock()
        mock_message_queue.declare_queue = MagicMock()
        mock_message_queue.publish = MagicMock(return_value=True)
        mock_get_message_queue.return_value = mock_message_queue

        # Create test data in the database
        matrix_repo = MatrixRepository()
        document_repo = DocumentRepository()
        job_repo = DocumentExtractionJobRepository()

        # Create a workspace first
        workspace = sample_workspace

        # Create a document
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="docs/test.pdf",
            content_type="application/pdf",
            extraction_status=ExtractionStatus.PROCESSING,
            checksum="1234567890",
            company_id=sample_company.id,
        )
        document = await document_repo.create(document_create)

        # Create an extraction job
        job_create = DocumentExtractionJobCreateModel(
            document_id=document.id, status=DocumentExtractionJobStatus.PROCESSING
        )
        job = await job_repo.create(job_create)

        await test_db.commit()

        # Call the activity without trace headers
        await update_document_completion_activity(
            document_id=document.id,
            extraction_job_id=job.id,
            s3_key="extracted/789/456_extracted.md",
        )

        # Verify span was created with None trace headers
        mock_create_span.assert_called_once_with(
            "temporal::update_document_completion_activity", None
        )

        # Verify database changes by fetching fresh from DB
        updated_document = await document_repo.get(document.id)
        updated_job = await job_repo.get(job.id)

        assert updated_document.extraction_status == ExtractionStatus.COMPLETED
        assert updated_document.extraction_completed_at is not None
        assert (
            updated_document.extracted_content_path == "extracted/789/456_extracted.md"
        )
        assert updated_job.status == DocumentExtractionJobStatus.COMPLETED
        assert updated_job.completed_at is not None
        assert updated_job.extracted_content_path == "extracted/789/456_extracted.md"
