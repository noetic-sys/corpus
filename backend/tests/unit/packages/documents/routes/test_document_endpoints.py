import pytest
from packages.questions.models.database.question import QuestionEntity
from packages.matrices.models.database.matrix import MatrixEntity
from packages.matrices.models.database.matrix_entity_set import (
    MatrixEntitySetEntity,
    MatrixEntitySetMemberEntity,
)
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from io import BytesIO
from fastapi import UploadFile
from sqlalchemy import select
from uuid import uuid4

from tests.fixtures import SAMPLE_WORKSPACE_DATA, SAMPLE_MATRIX_DATA, SAMPLE_PDF_CONTENT
from packages.documents.routes.documents import upload_document
from packages.documents.models.domain.document import (
    ExtractionStatus,
    DocumentUpdateModel,
)
from packages.documents.repositories.document_repository import DocumentRepository


class TestDocumentEndpoints:
    """Integration tests for document API endpoints."""

    @pytest.fixture(autouse=True)
    def require_subscription(self, sample_subscription):
        """Ensure all tests have an active subscription."""
        pass

    async def _get_document_entity_set_id(
        self, client: AsyncClient, matrix_id: int
    ) -> int:
        """Helper to get document entity set ID for a matrix."""
        entity_sets_response = await client.get(
            f"/api/v1/matrices/{matrix_id}/entity-sets"
        )
        response_data = entity_sets_response.json()
        entity_sets = response_data["entitySets"]
        document_entity_set = next(
            es for es in entity_sets if es["entityType"] == "document"
        )
        return document_entity_set["id"]

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    async def test_upload_document(
        self,
        mock_get_message_queue,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
        sample_company,
        test_user,
    ):
        """Test uploading a document to a matrix."""
        # Use common fixtures - mock both service and factory level storage
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage
        mock_get_message_queue.return_value = mock_message_queue

        company = sample_company.__dict__

        # Create a workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json={**SAMPLE_WORKSPACE_DATA}
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create a matrix
        matrix_data = {
            **SAMPLE_MATRIX_DATA,
            "workspaceId": workspace["id"],
            "companyId": company["id"],
        }
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        # Get document entity set ID
        entity_set_id = await self._get_document_entity_set_id(client, matrix["id"])

        # Upload a document
        files = {"file": ("test.pdf", BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")}
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/documents/?entitySetId={entity_set_id}",
            files=files,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.pdf"
        assert data["contentType"] == "application/pdf"
        # Note: Document response no longer includes matrix_id - it's a standalone entity
        assert "storageKey" in data

        # Verify storage was called
        mock_storage.upload.assert_called_once()

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    async def test_delete_document(
        self,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
        test_user,
    ):
        """Test deleting a document."""
        # Use common fixtures
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage

        # Mock message queue for upload
        with patch(
            "packages.qa.services.qa_job_service.get_message_queue"
        ) as mock_get_message_queue:
            mock_get_message_queue.return_value = mock_message_queue

            # Create workspace first
            workspace_response = await client.post(
                "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
            )
            assert workspace_response.status_code == 200
            workspace = workspace_response.json()

            # Create matrix and upload document
            matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
            matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
            matrix = matrix_response.json()

            entity_set_id = await self._get_document_entity_set_id(client, matrix["id"])

            files = {
                "file": ("test.pdf", BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")
            }
            doc_response = await client.post(
                f"/api/v1/matrices/{matrix['id']}/documents/?entitySetId={entity_set_id}",
                files=files,
            )
            document = doc_response.json()

        # Delete the document
        response = await client.delete(f"/api/v1/documents/{document['id']}")
        assert response.status_code == 200

        # Verify storage delete was called
        mock_storage.delete.assert_called_once_with(document["storageKey"])

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    async def test_get_nonexistent_document(
        self,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        test_user,
    ):
        """Test getting a non-existent document."""
        # Use common fixture (even though it shouldn't be called, this prevents accidental hits)
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage

        response = await client.get("/api/v1/documents/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found"

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    async def test_upload_document_storage_failure(
        self,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        test_user,
    ):
        """Test document upload when storage fails."""
        # Mock storage failure using common fixture
        mock_storage.upload.return_value = False
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        entity_set_id = await self._get_document_entity_set_id(client, matrix["id"])

        # Try to upload document
        files = {"file": ("test.pdf", BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")}
        response = await client.post(
            f"/api/v1/matrices/{matrix['id']}/documents/?entitySetId={entity_set_id}",
            files=files,
        )
        assert response.status_code == 500
        assert "Failed to upload file" in response.json()["detail"]

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch(
        "packages.matrices.services.batch_processing_service.BatchProcessingService.process_entity_added_to_set"
    )
    async def test_upload_document_rollback_on_cell_processing_failure(
        self,
        mock_process_entity_added_to_set,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        test_user,
    ):
        """Test that document upload rolls back when cell processing fails."""
        # Use common fixture
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage

        # Mock cell processing to fail
        mock_process_entity_added_to_set.side_effect = Exception(
            "Cell processing failed"
        )

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create a matrix first
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()

        entity_set_id = await self._get_document_entity_set_id(client, matrix["id"])

        # Attempt to upload document (should fail due to cell processing error)
        files = {"file": ("test.pdf", BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")}

        # Since the exception propagates through FastAPI, we need to catch it
        with pytest.raises(Exception) as exc_info:
            _ = await client.post(
                f"/api/v1/matrices/{matrix['id']}/documents/?entitySetId={entity_set_id}",
                files=files,
            )
        assert "Cell processing failed" in str(exc_info.value)

        # Verify no document was persisted (transaction rolled back)
        documents_response = await client.get(
            f"/api/v1/matrices/{matrix['id']}/documents/"
        )
        assert documents_response.status_code == 200
        documents = documents_response.json()
        # The document should be rolled back since the transaction failed
        assert len(documents) == 0

        # Verify storage upload was still called (but document record rolled back)
        mock_storage.upload.assert_called_once()


class TestDocumentStreamingEndpoints:
    """Unit tests for new document streaming endpoints."""

    @pytest.fixture(autouse=True)
    def require_subscription(self, sample_subscription):
        """Ensure all tests have an active subscription."""
        pass

    async def _get_document_entity_set_id(
        self, client: AsyncClient, matrix_id: int
    ) -> int:
        """Helper to get document entity set ID for a matrix."""
        entity_sets_response = await client.get(
            f"/api/v1/matrices/{matrix_id}/entity-sets"
        )
        response_data = entity_sets_response.json()
        entity_sets = response_data["entitySets"]
        document_entity_set = next(
            es for es in entity_sets if es["entityType"] == "document"
        )
        return document_entity_set["id"]

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    async def test_get_documents_by_matrix(
        self,
        mock_get_message_queue,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
        test_user,
    ):
        """Test getting all documents for a specific matrix."""
        # Use common fixtures
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage
        mock_get_message_queue.return_value = mock_message_queue

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()
        matrix_id = matrix["id"]

        entity_set_id = await self._get_document_entity_set_id(client, matrix_id)

        # Upload multiple documents to the matrix
        document_filenames = ["test1.pdf", "test2.pdf", "test3.pdf"]
        for filename in document_filenames:
            files = {"file": (filename, BytesIO(uuid4().bytes), "application/pdf")}
            response = await client.post(
                f"/api/v1/matrices/{matrix_id}/documents/?entitySetId={entity_set_id}",
                files=files,
            )
            assert response.status_code == 200

        # Create another matrix with a document (should not be included)
        other_matrix_data = {
            "name": "Other Matrix",
            "description": "Other",
            "workspace_id": workspace["id"],
        }
        other_matrix_response = await client.post(
            "/api/v1/matrices/", json=other_matrix_data
        )
        other_matrix = other_matrix_response.json()
        other_entity_set_id = await self._get_document_entity_set_id(
            client, other_matrix["id"]
        )
        files = {"file": ("other.pdf", BytesIO(uuid4().bytes), "application/pdf")}
        await client.post(
            f"/api/v1/matrices/{other_matrix['id']}/documents/?entitySetId={other_entity_set_id}",
            files=files,
        )

        # Call the streaming endpoint
        response = await client.get(f"/api/v1/matrices/{matrix_id}/documents/")

        # Assertions
        assert response.status_code == 200
        documents = response.json()
        assert isinstance(documents, list)
        assert len(documents) == 3

        # Verify all documents belong to the correct matrix and have the right structure
        for matrix_document in documents:
            assert matrix_document["matrixId"] == matrix_id
            assert matrix_document["document"]["filename"] in document_filenames
            assert "id" in matrix_document  # Association ID
            assert "documentId" in matrix_document
            assert "document" in matrix_document  # Nested document object
            assert "storageKey" in matrix_document["document"]
            assert "createdAt" in matrix_document

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    async def test_get_documents_by_matrix_empty(
        self,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        test_user,
    ):
        """Test getting documents for a matrix with no documents."""
        # Use common fixture
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage

        # Create workspace first
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create matrix without documents
        matrix_data = {**SAMPLE_MATRIX_DATA, "workspaceId": workspace["id"]}
        matrix_response = await client.post("/api/v1/matrices/", json=matrix_data)
        matrix = matrix_response.json()
        matrix_id = matrix["id"]

        # Call the streaming endpoint
        response = await client.get(f"/api/v1/matrices/{matrix_id}/documents/")

        # Assertions
        assert response.status_code == 200
        documents = response.json()
        assert isinstance(documents, list)
        assert len(documents) == 0

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    async def test_get_documents_by_nonexistent_matrix(
        self,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        test_user,
    ):
        """Test getting documents for a non-existent matrix."""
        # Use common fixture (even though it shouldn't be called for non-existent matrix)
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage

        # Call the streaming endpoint with non-existent matrix ID
        response = await client.get("/api/v1/matrices/99999/documents/")

        # Should return empty list since service returns empty for non-existent matrix
        assert response.status_code == 200
        documents = response.json()
        assert isinstance(documents, list)
        assert len(documents) == 0

    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    async def test_associate_existing_document_queues_jobs(
        self,
        mock_batch_get_message_queue,
        mock_qa_get_message_queue,
        mock_get_storage_factory,
        mock_get_storage_service,
        client: AsyncClient,
        mock_storage,
        mock_message_queue,
        test_user,
        test_db,
        sample_company,
    ):
        """Test that associating an existing document with a matrix queues QA jobs."""
        # Mock storage and message queue
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage
        mock_qa_get_message_queue.return_value = mock_message_queue
        mock_batch_get_message_queue.return_value = mock_message_queue

        # Create workspace
        workspace_response = await client.post(
            "/api/v1/workspaces/", json=SAMPLE_WORKSPACE_DATA
        )
        assert workspace_response.status_code == 200
        workspace = workspace_response.json()

        # Create first matrix and upload a document
        matrix1_data = {
            "name": "Matrix 1",
            "description": "First matrix",
            "workspaceId": workspace["id"],
        }
        matrix1_response = await client.post("/api/v1/matrices/", json=matrix1_data)
        matrix1 = matrix1_response.json()

        entity_set_id1 = await self._get_document_entity_set_id(client, matrix1["id"])

        files = {"file": ("test.pdf", BytesIO(SAMPLE_PDF_CONTENT), "application/pdf")}
        doc_response = await client.post(
            f"/api/v1/matrices/{matrix1['id']}/documents/?entitySetId={entity_set_id1}",
            files=files,
        )
        assert doc_response.status_code == 200
        document = doc_response.json()
        document_id = document["id"]

        # Create second matrix with questions
        matrix2_data = {
            "name": "Matrix 2",
            "description": "Second matrix",
            "workspaceId": workspace["id"],
        }
        matrix2_response = await client.post("/api/v1/matrices/", json=matrix2_data)
        matrix2 = matrix2_response.json()
        matrix2_id = matrix2["id"]

        # Get question entity set for matrix2
        entity_sets_response = await client.get(
            f"/api/v1/matrices/{matrix2_id}/entity-sets"
        )
        entity_sets_data = entity_sets_response.json()
        question_entity_set = next(
            es
            for es in entity_sets_data["entitySets"]
            if es["entityType"] == "question"
        )

        # Add questions to second matrix
        question1_response = await client.post(
            f"/api/v1/matrices/{matrix2_id}/questions/?entitySetId={question_entity_set['id']}",
            json={"questionText": "What is the topic?", "questionTypeId": 1},
        )
        assert question1_response.status_code == 200

        question2_response = await client.post(
            f"/api/v1/matrices/{matrix2_id}/questions/?entitySetId={question_entity_set['id']}",
            json={"questionText": "What are the findings?", "questionTypeId": 2},
        )
        assert question2_response.status_code == 200

        # Mark document as COMPLETED so QA jobs will be queued on association
        # Use repository directly (imports at top of file)
        doc_repo = DocumentRepository()
        await doc_repo.update(
            document_id,
            DocumentUpdateModel(
                extraction_status=ExtractionStatus.COMPLETED,
                extracted_content_path="test/path.md",
            ),
        )
        await test_db.commit()

        # Reset mock to track calls from association
        mock_message_queue.publish_batch.reset_mock()

        # Associate existing document with second matrix
        response = await client.post(
            f"/api/v1/matrices/{matrix2_id}/documents/{document_id}/associate"
        )
        assert response.status_code == 200
        result = response.json()
        assert result["message"] == "Document associated with matrix successfully"

        # Verify QA jobs were queued (2 questions = 2 jobs published in batch)
        assert mock_message_queue.publish_batch.call_count == 1


class TestDocumentUploadUnit:
    """Unit tests for document upload endpoint using real services with only external provider mocking."""

    @pytest.fixture(autouse=True)
    def require_subscription(self, sample_subscription):
        """Ensure all tests have an active subscription."""
        pass

    @pytest.fixture
    def mock_file(self):
        """Create a mock UploadFile."""
        file_content = b"test file content"
        file = UploadFile(
            filename="test.pdf",
            file=BytesIO(file_content),
            size=len(file_content),
            headers={"content-type": "application/pdf"},
        )
        return file

    @pytest.fixture
    def mock_storage(self):
        """Create a mocked storage service."""
        storage = AsyncMock()
        storage.upload = AsyncMock(return_value=True)
        storage.delete = AsyncMock(return_value=True)
        storage.download = AsyncMock(return_value=b"extracted content")
        return storage

    @pytest.fixture
    def mock_bloom_filter(self):
        """Create a mocked bloom filter provider."""
        bloom_filter = AsyncMock()
        bloom_filter.exists = AsyncMock(return_value=False)
        bloom_filter.add = AsyncMock(return_value=True)
        return bloom_filter

    @pytest.fixture
    def mock_message_queue(self):
        """Create a mocked message queue."""
        queue = AsyncMock()
        queue.send_message = AsyncMock(return_value="message_id")
        return queue

    @pytest.fixture
    async def sample_matrix_2(self, test_db, sample_workspace, sample_company):
        """Create a sample matrix in the database with entity sets."""
        matrix = MatrixEntity(
            name="Test Matrix 2",
            description="Test description 2",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
            matrix_type="standard",
        )
        test_db.add(matrix)
        await test_db.commit()
        await test_db.refresh(matrix)

        # Create required entity sets for standard matrix
        document_entity_set = MatrixEntitySetEntity(
            matrix_id=matrix.id,
            company_id=sample_company.id,
            name="Documents",
            entity_type="document",
        )
        question_entity_set = MatrixEntitySetEntity(
            matrix_id=matrix.id,
            company_id=sample_company.id,
            name="Questions",
            entity_type="question",
        )
        test_db.add(document_entity_set)
        test_db.add(question_entity_set)
        await test_db.commit()

        return matrix

    @pytest.fixture
    async def sample_questions(self, test_db, sample_matrix, sample_company):
        """Create sample questions in the database."""

        questions = [
            QuestionEntity(
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
                question_text="What is the main topic?",
                question_type_id=1,
            ),
            QuestionEntity(
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
                question_text="What are the key findings?",
                question_type_id=2,
            ),
        ]
        test_db.add_all(questions)
        await test_db.commit()
        for q in questions:
            await test_db.refresh(q)
        return questions

    @pytest.mark.asyncio
    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.documents.services.document_service.get_bloom_filter_provider")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    # @patch("workers.temporal_document_extraction_worker.get_extractor")
    async def test_upload_document_success_with_real_services(
        self,
        # mock_get_extractor,
        mock_get_message_queue,
        mock_get_bloom_filter,
        mock_get_storage_factory,
        mock_get_storage_service,
        test_db,
        mock_file,
        mock_storage,
        mock_bloom_filter,
        mock_message_queue,
        sample_matrix,
        sample_document_entity_set,
        sample_questions,
        test_user,
    ):
        """Test successful document upload with real services, only mocking external providers."""
        # Mock only external providers
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage
        mock_get_bloom_filter.return_value = mock_bloom_filter
        mock_get_message_queue.return_value = mock_message_queue

        # Mock document extractor
        # mock_extractor = AsyncMock()
        # mock_extractor.supports_file_type.return_value = True
        # mock_extractor.extract_text.return_value = "Extracted text content"
        # mock_get_extractor.return_value = mock_extractor

        # Call the endpoint with real services
        result = await upload_document(
            matrix_id=sample_matrix.id,
            entity_set_id=sample_document_entity_set.id,
            file=mock_file,
            current_user=test_user,
        )

        # Assertions - verify the document was created
        assert result is not None
        assert result.filename == "test.pdf"
        assert result.checksum is not None
        assert len(result.checksum) == 64  # SHA256 hex digest length

        # Verify external providers were called
        mock_storage.upload.assert_called_once()
        mock_bloom_filter.add.assert_called_once_with(
            "document_checksums_1", result.checksum
        )

    @pytest.mark.asyncio
    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.documents.services.document_service.get_bloom_filter_provider")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    async def test_upload_document_storage_failure(
        self,
        mock_get_message_queue,
        mock_get_bloom_filter,
        mock_get_storage_factory,
        mock_get_storage_service,
        test_db,
        mock_file,
        mock_bloom_filter,
        mock_message_queue,
        sample_matrix,
        sample_document_entity_set,
        test_user,
    ):
        """Test document upload when storage fails."""
        # Mock storage failure
        mock_storage = AsyncMock()
        mock_storage.upload.return_value = False
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage
        mock_get_bloom_filter.return_value = mock_bloom_filter
        mock_get_message_queue.return_value = mock_message_queue

        # Should raise an exception when storage upload fails
        with pytest.raises(Exception, match="Failed to upload file"):
            await upload_document(
                matrix_id=sample_matrix.id,
                entity_set_id=sample_document_entity_set.id,
                file=mock_file,
                current_user=test_user,
            )

    @pytest.mark.asyncio
    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.documents.services.document_service.get_bloom_filter_provider")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    async def test_upload_duplicate_document(
        self,
        mock_get_message_queue,
        mock_get_bloom_filter,
        mock_get_storage_factory,
        mock_get_storage_service,
        test_db,
        mock_storage,
        mock_bloom_filter,
        mock_message_queue,
        sample_matrix,
        sample_matrix_2,
        sample_document_entity_set,
        test_user,
        sample_company,
    ):
        """Test uploading a duplicate document (same checksum)."""
        # Mock external providers
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage
        mock_get_bloom_filter.return_value = mock_bloom_filter
        mock_get_message_queue.return_value = mock_message_queue

        # Get entity set for sample_matrix_2 (already created by fixture)
        result = await test_db.execute(
            select(MatrixEntitySetEntity).where(
                MatrixEntitySetEntity.matrix_id == sample_matrix_2.id,
                MatrixEntitySetEntity.entity_type == "document",
            )
        )
        entity_set_2 = result.scalar_one()

        # Create first upload file with fixed content
        file_content = b"duplicate file content"
        file1 = UploadFile(
            filename="test1.pdf",
            file=BytesIO(file_content),
            size=len(file_content),
            headers={"content-type": "application/pdf"},
        )

        # Mock bloom filter to return False for first upload (not a duplicate)
        mock_bloom_filter.exists.return_value = False

        # Upload first document
        result1 = await upload_document(
            matrix_id=sample_matrix.id,
            entity_set_id=sample_document_entity_set.id,
            file=file1,
            current_user=test_user,
        )

        # Create second file with same content (actual duplicate)
        file2 = UploadFile(
            filename="test2.pdf",
            file=BytesIO(file_content),  # Same content = same checksum
            size=len(file_content),
            headers={"content-type": "application/pdf"},
        )

        # Mock bloom filter to return True for duplicate check
        mock_bloom_filter.exists.return_value = True

        # Upload duplicate document
        result2 = await upload_document(
            matrix_id=sample_matrix_2.id,
            entity_set_id=entity_set_2.id,
            file=file2,
            current_user=test_user,
        )

        # Should return the same document (duplicate detection)
        assert result2.id == result1.id
        assert result2.checksum == result1.checksum

        # Storage upload should only be called once (for the first upload)
        assert mock_storage.upload.call_count == 1

    @pytest.mark.asyncio
    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.documents.services.document_service.get_bloom_filter_provider")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    async def test_upload_document_no_existing_questions(
        self,
        mock_get_message_queue,
        mock_get_bloom_filter,
        mock_get_storage_factory,
        mock_get_storage_service,
        test_db,
        mock_file,
        mock_storage,
        mock_bloom_filter,
        mock_message_queue,
        sample_matrix,
        sample_document_entity_set,
        test_user,
    ):
        """Test document upload when no existing questions exist."""
        # Mock external providers
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage
        mock_get_bloom_filter.return_value = mock_bloom_filter
        mock_get_message_queue.return_value = mock_message_queue

        # Upload document to matrix with no questions
        result = await upload_document(
            matrix_id=sample_matrix.id,
            entity_set_id=sample_document_entity_set.id,
            file=mock_file,
            current_user=test_user,
        )

        # Should still succeed
        assert result is not None
        assert result.filename == "test.pdf"

        # Verify external providers were called
        mock_storage.upload.assert_called_once()
        mock_bloom_filter.add.assert_called_once_with(
            "document_checksums_1", result.checksum
        )

    @pytest.mark.asyncio
    @patch("packages.documents.services.document_service.get_storage")
    @patch("common.providers.storage.factory.get_storage")
    @patch("packages.documents.services.document_service.get_bloom_filter_provider")
    @patch("packages.qa.services.qa_job_service.get_message_queue")
    @patch(
        "packages.documents.routes.documents.get_temporal_document_extraction_service"
    )
    @patch(
        "packages.matrices.services.batch_processing_service.BatchProcessingService.create_jobs_and_queue_for_cells"
    )
    async def test_upload_duplicate_document_already_extracted_skips_reextraction(
        self,
        mock_create_jobs_and_queue,
        mock_get_temporal_service,
        mock_get_message_queue,
        mock_get_bloom_filter,
        mock_get_storage_factory,
        mock_get_storage_service,
        test_db,
        mock_storage,
        mock_bloom_filter,
        mock_message_queue,
        sample_matrix,
        sample_matrix_2,
        sample_document_entity_set,
        sample_questions,
        test_user,
        sample_company,
    ):
        """Test that uploading a duplicate document that's already extracted skips re-extraction and queues jobs immediately."""
        # Mock external providers
        mock_get_storage_service.return_value = mock_storage
        mock_get_storage_factory.return_value = mock_storage
        mock_get_bloom_filter.return_value = mock_bloom_filter
        mock_get_message_queue.return_value = mock_message_queue

        # Mock temporal extraction service
        mock_temporal_service = MagicMock()
        mock_temporal_service.create_and_start_workflow = AsyncMock()
        mock_get_temporal_service.return_value = mock_temporal_service

        # Mock batch processing service to return count
        mock_create_jobs_and_queue.return_value = 2  # 2 questions = 2 jobs

        # Get entity sets for sample_matrix_2 (already created by fixture)
        result = await test_db.execute(
            select(MatrixEntitySetEntity).where(
                MatrixEntitySetEntity.matrix_id == sample_matrix_2.id,
                MatrixEntitySetEntity.entity_type == "document",
            )
        )
        entity_set_2 = result.scalar_one()

        # Get question entity set for sample_matrix_2
        question_entity_set_2_result = await test_db.execute(
            select(MatrixEntitySetEntity).where(
                MatrixEntitySetEntity.matrix_id == sample_matrix_2.id,
                MatrixEntitySetEntity.entity_type == "question",
            )
        )
        question_entity_set_2 = question_entity_set_2_result.scalar_one()

        # Add the same questions to sample_matrix_2's question entity set
        for i, question in enumerate(sample_questions):
            member = MatrixEntitySetMemberEntity(
                entity_set_id=question_entity_set_2.id,
                entity_type="question",
                entity_id=question.id,
                member_order=i,
                company_id=sample_company.id,
            )
            test_db.add(member)
        await test_db.commit()

        # Create first upload file with fixed content
        file_content = b"duplicate file content for extraction test"
        file1 = UploadFile(
            filename="original.pdf",
            file=BytesIO(file_content),
            size=len(file_content),
            headers={"content-type": "application/pdf"},
        )

        # Mock bloom filter to return False for first upload (not a duplicate)
        mock_bloom_filter.exists.return_value = False

        # Add the questions to the question entity set so cells will be created
        question_entity_set_result = await test_db.execute(
            select(MatrixEntitySetEntity).where(
                MatrixEntitySetEntity.matrix_id == sample_matrix.id,
                MatrixEntitySetEntity.entity_type == "question",
            )
        )
        question_entity_set = question_entity_set_result.scalar_one()

        for i, question in enumerate(sample_questions):
            member = MatrixEntitySetMemberEntity(
                entity_set_id=question_entity_set.id,
                entity_type="question",
                entity_id=question.id,
                member_order=i,
                company_id=sample_company.id,
            )
            test_db.add(member)
        await test_db.commit()

        # Upload first document to sample_matrix (which has questions from fixture)
        result1 = await upload_document(
            matrix_id=sample_matrix.id,
            entity_set_id=sample_document_entity_set.id,
            file=file1,
            current_user=test_user,
        )

        # Mark the document as COMPLETED extraction using the repository
        doc_repo = DocumentRepository()
        update_data = DocumentUpdateModel(
            extraction_status=ExtractionStatus.COMPLETED.value,
            extracted_content_path="extracted/original.md",
        )
        await doc_repo.update(result1.id, update_data)
        await test_db.commit()

        # Reset mocks to track the duplicate upload
        mock_temporal_service.create_and_start_workflow.reset_mock()
        mock_create_jobs_and_queue.reset_mock()

        # Create second file with same content (actual duplicate)
        file2 = UploadFile(
            filename="duplicate.pdf",
            file=BytesIO(file_content),  # Same content = same checksum
            size=len(file_content),
            headers={"content-type": "application/pdf"},
        )

        # Mock bloom filter to return True for duplicate check
        mock_bloom_filter.exists.return_value = True

        # Upload duplicate document to sample_matrix_2 (different matrix)
        result2 = await upload_document(
            matrix_id=sample_matrix_2.id,
            entity_set_id=entity_set_2.id,
            file=file2,
            current_user=test_user,
        )

        # Assertions
        # 1. Should return the same document (duplicate detection)
        assert result2.id == result1.id
        assert result2.checksum == result1.checksum

        # 2. Should NOT have started a Temporal workflow (no re-extraction)
        mock_temporal_service.create_and_start_workflow.assert_not_called()

        # 3. Should have created QA jobs immediately
        mock_create_jobs_and_queue.assert_called_once()

        # 4. Storage upload should only be called once (for the first upload)
        assert mock_storage.upload.call_count == 1
