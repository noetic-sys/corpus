import pytest
from unittest.mock import AsyncMock, patch

from packages.documents.workers.document_indexing_worker import DocumentIndexingWorker
from packages.documents.models.database.document import DocumentEntity, ExtractionStatus
from packages.documents.models.database.document_indexing_job import (
    DocumentIndexingJobEntity,
)
from packages.documents.models.domain.document_indexing_job import (
    DocumentIndexingJobStatus,
)
from common.providers.messaging.messages import DocumentIndexingMessage
from common.providers.messaging.constants import QueueName


class TestDocumentIndexingWorker:
    """Tests for DocumentIndexingWorker class with real database."""

    @pytest.fixture(autouse=True)
    def setup_storage_mock(self):
        """Setup mock storage for all tests."""
        with patch(
            "packages.documents.services.document_service.get_storage"
        ) as mock_storage_factory:
            mock_storage = AsyncMock()
            mock_storage_factory.return_value = mock_storage
            self.mock_storage_factory = mock_storage_factory
            self.mock_storage = mock_storage
            yield

    @pytest.fixture
    def mock_search_provider(self):
        """Create mock search provider."""
        mock_provider = AsyncMock()
        mock_provider.index_document = AsyncMock(return_value=True)
        return mock_provider

    @pytest.fixture
    def indexing_worker(self):
        """Create DocumentIndexingWorker instance."""
        worker = DocumentIndexingWorker()
        return worker

    @pytest.fixture
    async def test_data(self, test_db, sample_company):
        """Create test data in the database."""
        # Create document with COMPLETED extraction status
        document = DocumentEntity(
            company_id=sample_company.id,
            filename="test_doc.pdf",
            storage_key="documents/test_doc.pdf",
            content_type="application/pdf",
            file_size=1000,
            checksum="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            extraction_status=ExtractionStatus.COMPLETED,
            extracted_content_path="extracted/test_doc/content.md",
        )
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)

        # Create indexing job
        job = DocumentIndexingJobEntity(
            document_id=document.id, status=DocumentIndexingJobStatus.QUEUED.value
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)

        return {
            "document": document,
            "job": job,
        }

    @pytest.fixture
    def sample_message(self, test_data):
        """Sample message based on real test data."""
        return DocumentIndexingMessage(
            job_id=test_data["job"].id,
            document_id=test_data["document"].id,
        )

    @pytest.mark.asyncio
    @patch(
        "packages.documents.workers.document_indexing_worker.get_document_search_provider"
    )
    async def test_process_message_success(
        self,
        mock_get_search_provider,
        indexing_worker,
        mock_search_provider,
        test_db,
        test_data,
        sample_message,
    ):
        """Test successful document indexing processing."""

        # Mock search provider
        mock_get_search_provider.return_value = mock_search_provider

        # Process message
        await indexing_worker.process_message(sample_message)

        # Verify search provider was called
        mock_search_provider.index_document.assert_called_once()

        # Get the document that was passed to index_document
        call_args = mock_search_provider.index_document.call_args
        indexed_doc = call_args[0][0]
        assert indexed_doc.id == test_data["document"].id
        assert indexed_doc.filename == "test_doc.pdf"

        # Verify job status was updated to completed
        await test_db.refresh(test_data["job"])
        assert test_data["job"].status == DocumentIndexingJobStatus.COMPLETED.value
        assert test_data["job"].completed_at is not None

    @pytest.mark.asyncio
    @patch(
        "packages.documents.workers.document_indexing_worker.get_document_search_provider"
    )
    async def test_process_message_document_not_found(
        self,
        mock_get_search_provider,
        indexing_worker,
        mock_search_provider,
        test_db,
        test_data,
    ):
        """Test processing when document doesn't exist."""
        # Create message with non-existent document ID
        message = DocumentIndexingMessage(
            job_id=test_data["job"].id,
            document_id=999999,  # Non-existent document
        )

        # Process message - should raise ValueError
        with pytest.raises(ValueError, match="Document 999999 not found"):
            await indexing_worker.process_message(message)

        # Verify job was marked as failed
        await test_db.refresh(test_data["job"])
        assert test_data["job"].status == DocumentIndexingJobStatus.FAILED.value
        assert "Document 999999 not found" in test_data["job"].error_message

    @pytest.mark.asyncio
    @patch(
        "packages.documents.workers.document_indexing_worker.get_document_search_provider"
    )
    async def test_process_message_indexing_failure(
        self,
        mock_get_search_provider,
        indexing_worker,
        test_db,
        test_data,
        sample_message,
    ):
        """Test processing when indexing fails."""
        # Mock search provider to raise exception
        mock_failing_search = AsyncMock()
        mock_failing_search.index_document = AsyncMock(
            side_effect=Exception("Search index connection failed")
        )
        mock_get_search_provider.return_value = mock_failing_search

        # Process message - should raise exception
        with pytest.raises(Exception, match="Search index connection failed"):
            await indexing_worker.process_message(sample_message)

        # Verify job was marked as failed
        await test_db.refresh(test_data["job"])
        assert test_data["job"].status == DocumentIndexingJobStatus.FAILED.value
        assert "Search index connection failed" in test_data["job"].error_message

    @pytest.mark.asyncio
    @patch(
        "packages.documents.workers.document_indexing_worker.get_document_search_provider"
    )
    async def test_process_message_with_pending_extraction(
        self,
        mock_get_search_provider,
        indexing_worker,
        mock_search_provider,
        test_db,
        sample_message,
    ):
        """Test indexing document with PENDING extraction status."""
        # Create document with PENDING extraction status
        document = DocumentEntity(
            company_id=1,
            filename="pending_doc.pdf",
            storage_key="documents/pending_doc.pdf",
            content_type="application/pdf",
            file_size=1000,
            checksum="b775a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae4",
            extraction_status=ExtractionStatus.PENDING,
            extracted_content_path=None,
        )
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)

        # Create indexing job for pending document
        job = DocumentIndexingJobEntity(
            document_id=document.id, status=DocumentIndexingJobStatus.QUEUED.value
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)

        # Create message for pending document
        message = DocumentIndexingMessage(
            job_id=job.id,
            document_id=document.id,
        )

        # Mock search provider
        mock_get_search_provider.return_value = mock_search_provider

        # Process message
        await indexing_worker.process_message(message)

        # Verify search provider was still called (indexes metadata only)
        mock_search_provider.index_document.assert_called_once()

        # Verify job was marked as completed even though extraction is pending
        await test_db.refresh(job)
        assert job.status == DocumentIndexingJobStatus.COMPLETED.value

    @pytest.mark.asyncio
    @patch(
        "packages.documents.workers.document_indexing_worker.get_document_search_provider"
    )
    async def test_process_message_with_processing_extraction(
        self,
        mock_get_search_provider,
        indexing_worker,
        mock_search_provider,
        test_db,
        sample_message,
    ):
        """Test indexing document with PROCESSING extraction status."""
        # Create document with PROCESSING extraction status
        document = DocumentEntity(
            company_id=1,
            filename="processing_doc.pdf",
            storage_key="documents/processing_doc.pdf",
            content_type="application/pdf",
            file_size=1000,
            checksum="c885a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae5",
            extraction_status=ExtractionStatus.PROCESSING,
            extracted_content_path=None,
        )
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)

        # Create indexing job
        job = DocumentIndexingJobEntity(
            document_id=document.id, status=DocumentIndexingJobStatus.QUEUED.value
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)

        # Create message
        message = DocumentIndexingMessage(
            job_id=job.id,
            document_id=document.id,
        )

        # Mock search provider
        mock_get_search_provider.return_value = mock_search_provider

        # Process message
        await indexing_worker.process_message(message)

        # Verify search provider was called (indexes metadata)
        mock_search_provider.index_document.assert_called_once()

        # Verify job was marked as completed
        await test_db.refresh(job)
        assert job.status == DocumentIndexingJobStatus.COMPLETED.value

    @pytest.mark.asyncio
    @patch(
        "packages.documents.workers.document_indexing_worker.get_document_search_provider"
    )
    async def test_process_message_with_failed_extraction(
        self,
        mock_get_search_provider,
        indexing_worker,
        mock_search_provider,
        test_db,
        sample_message,
    ):
        """Test indexing document with FAILED extraction status."""
        # Create document with FAILED extraction status
        document = DocumentEntity(
            company_id=1,
            filename="failed_doc.pdf",
            storage_key="documents/failed_doc.pdf",
            content_type="application/pdf",
            file_size=1000,
            checksum="d995a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae6",
            extraction_status=ExtractionStatus.FAILED,
            extracted_content_path=None,
        )
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)

        # Create indexing job
        job = DocumentIndexingJobEntity(
            document_id=document.id, status=DocumentIndexingJobStatus.QUEUED.value
        )
        test_db.add(job)
        await test_db.commit()
        await test_db.refresh(job)

        # Create message
        message = DocumentIndexingMessage(
            job_id=job.id,
            document_id=document.id,
        )

        # Mock search provider
        mock_get_search_provider.return_value = mock_search_provider

        # Process message
        await indexing_worker.process_message(message)

        # Verify search provider was still called (indexes metadata only)
        mock_search_provider.index_document.assert_called_once()

        # Verify job was marked as completed
        await test_db.refresh(job)
        assert job.status == DocumentIndexingJobStatus.COMPLETED.value

    @pytest.mark.asyncio
    @patch(
        "packages.documents.workers.document_indexing_worker.get_document_search_provider"
    )
    async def test_process_message_status_transitions(
        self,
        mock_get_search_provider,
        indexing_worker,
        mock_search_provider,
        test_db,
        test_data,
        sample_message,
    ):
        """Test job status transitions during processing."""
        # Mock search provider
        mock_get_search_provider.return_value = mock_search_provider

        # Verify initial status
        assert test_data["job"].status == DocumentIndexingJobStatus.QUEUED.value

        # Process message
        await indexing_worker.process_message(sample_message)

        # Verify final status
        await test_db.refresh(test_data["job"])
        assert test_data["job"].status == DocumentIndexingJobStatus.COMPLETED.value
        assert test_data["job"].completed_at is not None

    @pytest.mark.asyncio
    def test_worker_initialization(self):
        """Test DocumentIndexingWorker initialization."""

        worker = DocumentIndexingWorker()

        assert worker.queue_name == QueueName.DOCUMENT_INDEXING
        assert worker.message_class == DocumentIndexingMessage
        assert worker.worker_id is not None

    @pytest.mark.asyncio
    @patch(
        "packages.documents.workers.document_indexing_worker.get_document_search_provider"
    )
    async def test_process_message_job_update_failure(
        self,
        mock_get_search_provider,
        indexing_worker,
        mock_search_provider,
        test_db,
        test_data,
        sample_message,
    ):
        """Test handling when job status update fails."""
        # Mock search provider
        mock_get_search_provider.return_value = mock_search_provider

        # Mock the indexing job service to fail on status update
        with patch(
            "packages.documents.workers.document_indexing_worker.DocumentIndexingJobService"
        ) as mock_service_class:
            mock_service = AsyncMock()
            mock_service_class.return_value = mock_service

            # First update (IN_PROGRESS) succeeds
            # Second update (COMPLETED) fails
            mock_service.update_job_status = AsyncMock(
                side_effect=[True, Exception("Database connection lost")]
            )

            # Mock document service
            with patch(
                "packages.documents.workers.document_indexing_worker.get_document_service"
            ) as mock_doc_service:
                mock_doc = AsyncMock()
                mock_doc_service.return_value = mock_doc
                mock_doc.get_document = AsyncMock(return_value=test_data["document"])

                # Process message - should raise the database exception
                with pytest.raises(Exception, match="Database connection lost"):
                    await indexing_worker.process_message(sample_message)

    @pytest.mark.asyncio
    @patch(
        "packages.documents.workers.document_indexing_worker.get_document_search_provider"
    )
    async def test_process_multiple_jobs_same_document(
        self,
        mock_get_search_provider,
        indexing_worker,
        mock_search_provider,
        test_db,
        test_data,
    ):
        """Test processing multiple indexing jobs for the same document."""
        # Create second job for the same document
        job2 = DocumentIndexingJobEntity(
            document_id=test_data["document"].id,
            status=DocumentIndexingJobStatus.QUEUED.value,
        )
        test_db.add(job2)
        await test_db.commit()
        await test_db.refresh(job2)

        # Mock search provider
        mock_get_search_provider.return_value = mock_search_provider

        # Process first job
        message1 = DocumentIndexingMessage(
            job_id=test_data["job"].id,
            document_id=test_data["document"].id,
        )
        await indexing_worker.process_message(message1)

        # Process second job
        message2 = DocumentIndexingMessage(
            job_id=job2.id,
            document_id=test_data["document"].id,
        )
        await indexing_worker.process_message(message2)

        # Verify both jobs completed
        await test_db.refresh(test_data["job"])
        await test_db.refresh(job2)
        assert test_data["job"].status == DocumentIndexingJobStatus.COMPLETED.value
        assert job2.status == DocumentIndexingJobStatus.COMPLETED.value

        # Verify index_document was called twice
        assert mock_search_provider.index_document.call_count == 2
