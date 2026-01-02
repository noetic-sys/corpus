import pytest
import hashlib
from datetime import datetime
from unittest.mock import AsyncMock, patch

from packages.matrices.services.matrix_service import MatrixService
from packages.matrices.services.entity_set_service import EntitySetService
from packages.matrices.models.domain.matrix import (
    MatrixCreateModel,
    MatrixCellModel,
    MatrixCellStatus,
)
from packages.matrices.models.schemas.matrix import MatrixDuplicateRequest
from packages.matrices.models.domain.matrix_enums import EntityType, CellType
from packages.documents.models.database.document import DocumentEntity
from packages.questions.models.database.question import QuestionEntity
from packages.questions.services.question_service import QuestionService


class TestMatrixService:
    """Unit tests for MatrixService."""

    @pytest.fixture
    def matrix_service(self, test_db):
        """Create a MatrixService instance with real database session."""
        return MatrixService(test_db)

    @pytest.mark.asyncio
    async def test_create_matrix(
        self, matrix_service, sample_workspace, sample_company
    ):
        """Test creating a matrix."""
        matrix_create = MatrixCreateModel(
            name="Test Matrix",
            description="Test description",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )

        result = await matrix_service.create_matrix(matrix_create)

        assert result.name == "Test Matrix"
        assert result.description == "Test description"
        assert result.id is not None
        assert result.created_at is not None
        assert result.updated_at is not None

    @pytest.mark.asyncio
    async def test_get_matrix(self, matrix_service, sample_workspace, sample_company):
        """Test getting a matrix by ID."""
        matrix_create = MatrixCreateModel(
            name="Test Matrix",
            description="Test description",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        created_matrix = await matrix_service.create_matrix(matrix_create)

        result = await matrix_service.get_matrix(created_matrix.id)

        assert result is not None
        assert result.id == created_matrix.id
        assert result.name == "Test Matrix"
        assert result.description == "Test description"

    @pytest.mark.asyncio
    async def test_delete_matrix(
        self, matrix_service, sample_workspace, sample_company
    ):
        """Test deleting a matrix."""
        matrix_create = MatrixCreateModel(
            name="Test Matrix",
            description="Test description",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
        )
        created_matrix = await matrix_service.create_matrix(matrix_create)

        result = await matrix_service.delete_matrix(created_matrix.id)

        assert result is True

        # Verify it was deleted
        deleted_matrix = await matrix_service.get_matrix(created_matrix.id)
        assert deleted_matrix is None

    @pytest.mark.asyncio
    @patch("packages.matrices.services.matrix_service.QuotaService")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_matrix_with_documents_only(
        self,
        mock_tracer,
        mock_queue,
        mock_quota_service,
        matrix_service,
        sample_workspace,
        sample_company,
        test_db,
    ):
        """Test duplicating a matrix with only document entity sets."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None
        mock_queue.return_value = None
        mock_quota_service.return_value.check_cell_operation_quota = AsyncMock()
        mock_quota_service.return_value.check_agentic_qa_quota = AsyncMock()

        # Create source matrix
        source_matrix = await matrix_service.create_matrix(
            MatrixCreateModel(
                name="Source Matrix",
                description="Source",
                workspace_id=sample_workspace.id,
                company_id=sample_company.id,
            )
        )

        # Create documents and add to entity set
        doc1 = DocumentEntity(
            filename="doc1.pdf",
            storage_key="documents/doc1.pdf",
            content_type="application/pdf",
            file_size=1024,
            checksum="doc1checksum" + "0" * 54,
            company_id=sample_company.id,
        )
        doc2 = DocumentEntity(
            filename="doc2.pdf",
            storage_key="documents/doc2.pdf",
            content_type="application/pdf",
            file_size=2048,
            checksum="doc2checksum" + "0" * 54,
            company_id=sample_company.id,
        )
        test_db.add_all([doc1, doc2])
        await test_db.commit()
        await test_db.refresh(doc1)
        await test_db.refresh(doc2)

        # Get document entity set and add members
        entity_set_service = EntitySetService(test_db)
        entity_sets = await entity_set_service.get_matrix_entity_sets(
            source_matrix.id, sample_company.id
        )
        doc_entity_set = next(
            es for es in entity_sets if es.entity_type == EntityType.DOCUMENT
        )

        await entity_set_service.add_members_batch(
            doc_entity_set.id,
            [doc1.id, doc2.id],
            EntityType.DOCUMENT,
            sample_company.id,
        )

        # Duplicate matrix with only document entity set
        duplicate_request = MatrixDuplicateRequest(
            name="Duplicated Matrix",
            description="Documents only",
            entity_set_ids=[doc_entity_set.id],
        )

        result = await matrix_service.duplicate_matrix(
            source_matrix.id, duplicate_request
        )

        # Verify duplication
        assert result.original_matrix_id == source_matrix.id
        assert result.duplicate_matrix_id != source_matrix.id
        assert doc_entity_set.id in result.entity_sets_duplicated
        assert (
            result.entity_sets_duplicated[doc_entity_set.id] == 2
        )  # 2 documents copied
        assert "Successfully duplicated matrix" in result.message

        # Verify target matrix has the documents
        target_entity_sets = await entity_set_service.get_matrix_entity_sets(
            result.duplicate_matrix_id, sample_company.id
        )
        target_doc_entity_set = next(
            es for es in target_entity_sets if es.entity_type == EntityType.DOCUMENT
        )
        target_members = await entity_set_service.get_entity_set_members(
            target_doc_entity_set.id, sample_company.id
        )

        assert len(target_members) == 2

    @pytest.mark.asyncio
    @patch("packages.matrices.services.matrix_service.QuotaService")
    @patch("packages.matrices.services.batch_processing_service.get_message_queue")
    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_duplicate_matrix_with_questions_only(
        self,
        mock_tracer,
        mock_queue,
        mock_quota_service,
        matrix_service,
        sample_workspace,
        sample_company,
        test_db,
    ):
        """Test duplicating a matrix with only question entity sets."""
        # Setup mocks
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None
        mock_queue.return_value = None
        mock_quota_service.return_value.check_cell_operation_quota = AsyncMock()
        mock_quota_service.return_value.check_agentic_qa_quota = AsyncMock()

        # Create source matrix
        source_matrix = await matrix_service.create_matrix(
            MatrixCreateModel(
                name="Source Matrix",
                description="Source",
                workspace_id=sample_workspace.id,
                company_id=sample_company.id,
            )
        )

        # Create questions and add to entity set
        question1 = QuestionEntity(
            matrix_id=source_matrix.id,
            company_id=sample_company.id,
            question_text="What is the date?",
            question_type_id=1,
            label="Date Question",
        )
        question2 = QuestionEntity(
            matrix_id=source_matrix.id,
            company_id=sample_company.id,
            question_text="What is the amount?",
            question_type_id=2,
            label="Amount Question",
        )
        test_db.add_all([question1, question2])
        await test_db.commit()
        await test_db.refresh(question1)
        await test_db.refresh(question2)

        # Get question entity set and add members
        entity_set_service = EntitySetService(test_db)
        entity_sets = await entity_set_service.get_matrix_entity_sets(
            source_matrix.id, sample_company.id
        )
        question_entity_set = next(
            es for es in entity_sets if es.entity_type == EntityType.QUESTION
        )

        await entity_set_service.add_members_batch(
            question_entity_set.id,
            [question1.id, question2.id],
            EntityType.QUESTION,
            sample_company.id,
        )

        # Duplicate matrix with only question entity set
        duplicate_request = MatrixDuplicateRequest(
            name="Duplicated Matrix",
            description="Questions only",
            entity_set_ids=[question_entity_set.id],
        )

        result = await matrix_service.duplicate_matrix(
            source_matrix.id, duplicate_request
        )

        # Verify duplication
        assert result.original_matrix_id == source_matrix.id
        assert result.duplicate_matrix_id != source_matrix.id
        assert question_entity_set.id in result.entity_sets_duplicated
        assert (
            result.entity_sets_duplicated[question_entity_set.id] == 2
        )  # 2 questions copied
        assert "Successfully duplicated matrix" in result.message

        # Verify target matrix has the questions
        question_service = QuestionService(test_db)
        target_questions = await question_service.get_questions_for_matrix(
            result.duplicate_matrix_id
        )

        assert len(target_questions) == 2


class TestMatrixServiceStreamingMethods:
    """Unit tests for new MatrixService streaming methods."""

    @pytest.fixture
    def mock_matrix_service(self, test_db):
        """Create a MatrixService with mocked repository."""
        service = MatrixService(test_db)
        service.matrix_cell_repo = AsyncMock()
        return service

    @pytest.fixture
    def sample_matrix_cells(self):
        """Sample matrix cells for testing."""
        return [
            MatrixCellModel(
                id=1,
                company_id=1,
                matrix_id=1,
                status=MatrixCellStatus.PENDING,
                cell_type=CellType.STANDARD,
                current_answer_set_id=None,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                cell_signature=hashlib.md5(b"sample_cell_1").hexdigest(),
            ),
            MatrixCellModel(
                id=2,
                company_id=1,
                matrix_id=1,
                status=MatrixCellStatus.COMPLETED,
                cell_type=CellType.STANDARD,
                current_answer_set_id=123,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                cell_signature=hashlib.md5(b"sample_cell_2").hexdigest(),
            ),
        ]

    @pytest.mark.asyncio
    async def test_get_matrix_cells(self, mock_matrix_service, sample_matrix_cells):
        """Test getting all matrix cells for a matrix."""
        matrix_id = 1
        mock_matrix_service.matrix_cell_repo.get_cells_by_matrix_id.return_value = (
            sample_matrix_cells
        )

        result = await mock_matrix_service.get_matrix_cells(matrix_id)

        assert result == sample_matrix_cells
        mock_matrix_service.matrix_cell_repo.get_cells_by_matrix_id.assert_called_once_with(
            matrix_id
        )

    @pytest.mark.asyncio
    async def test_get_matrix_cells_empty_result(self, mock_matrix_service):
        """Test getting matrix cells when none exist."""
        matrix_id = 999
        mock_matrix_service.matrix_cell_repo.get_cells_by_matrix_id.return_value = []

        result = await mock_matrix_service.get_matrix_cells(matrix_id)

        assert result == []
        mock_matrix_service.matrix_cell_repo.get_cells_by_matrix_id.assert_called_once_with(
            matrix_id
        )
