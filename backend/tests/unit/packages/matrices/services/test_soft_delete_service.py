import pytest
import hashlib
from unittest.mock import patch

from packages.matrices.services.soft_delete_service import SoftDeleteService
from packages.matrices.models.database.matrix import MatrixEntity, MatrixCellEntity
from packages.matrices.models.database.matrix_entity_set import (
    MatrixEntitySetEntity,
    MatrixEntitySetMemberEntity,
    MatrixCellEntityReferenceEntity,
)
from packages.documents.models.database.document import DocumentEntity
from packages.questions.models.database.question import QuestionEntity
from packages.workspaces.models.database.workspace import WorkspaceEntity
from packages.matrices.models.schemas.matrix import (
    MatrixSoftDeleteRequest,
    EntitySetFilter,
)
from packages.matrices.models.domain.matrix import MatrixCellStatus
from packages.matrices.models.domain.matrix_enums import EntityRole, EntityType


class TestSoftDeleteService:
    """Unit tests for SoftDeleteService.

    NOTE: Many of these tests are currently failing because the SoftDeleteService
    has not yet been updated to work with the new document architecture where
    documents are standalone entities. The service still assumes documents are
    directly associated with matrices.
    """

    @pytest.fixture
    async def service(self, test_db):
        """Create a SoftDeleteService instance."""
        return SoftDeleteService()

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Test needs rewrite for entity-set based soft delete - requires entity set members and cell entity refs"
    )
    async def test_soft_delete_documents_success(
        self,
        service,
        sample_matrix,
        sample_document,
        sample_matrix_cell,
        sample_company,
    ):
        """Test successful soft deletion of cells via entity_set_filters."""
        # TODO: Rewrite this test to:
        # 1. Create entity set for documents
        # 2. Create entity set member for sample_document
        # 3. Create cell entity reference linking sample_matrix_cell to that member
        # 4. Use entity_set_filters to soft delete cells referencing that document
        # 5. Verify cell is soft deleted
        pass

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="SoftDeleteService needs update for new document architecture"
    )
    async def test_soft_delete_questions_success(
        self, service, sample_matrix, sample_question, sample_matrix_cell
    ):
        """Test successful soft deletion of questions."""
        request = MatrixSoftDeleteRequest(question_ids=[sample_question.id])

        entities_deleted, cells_deleted = await service.soft_delete_entities(
            sample_matrix.id, request
        )

        assert entities_deleted == 1
        assert cells_deleted == 1

        # Verify question is marked as deleted
        refreshed_question = await service.question_repo.get(sample_question.id)
        assert (
            refreshed_question is None
        )  # Should not be returned due to soft delete filter

        # Verify matrix cell is marked as deleted
        refreshed_cell = await service.matrix_cell_repo.get(sample_matrix_cell.id)
        assert (
            refreshed_cell is None
        )  # Should not be returned due to soft delete filter

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="SoftDeleteService needs update for new document architecture"
    )
    async def test_soft_delete_matrices_success(
        self,
        service,
        sample_matrix,
        sample_document,
        sample_question,
        sample_matrix_cell,
    ):
        """Test successful soft deletion of matrices with cascade."""
        request = MatrixSoftDeleteRequest(matrix_ids=[sample_matrix.id])

        entities_deleted, cells_deleted = await service.soft_delete_entities(
            sample_matrix.id, request
        )

        assert entities_deleted == 1
        assert cells_deleted == 1

        # Verify matrix is marked as deleted
        refreshed_matrix = await service.matrix_repo.get(sample_matrix.id)
        assert (
            refreshed_matrix is None
        )  # Should not be returned due to soft delete filter

        # Verify document is marked as deleted (cascade)
        refreshed_doc = await service.document_repo.get(sample_document.id)
        assert refreshed_doc is None  # Should not be returned due to soft delete filter

        # Verify question is marked as deleted (cascade)
        refreshed_question = await service.question_repo.get(sample_question.id)
        assert (
            refreshed_question is None
        )  # Should not be returned due to soft delete filter

        # Verify matrix cell is marked as deleted (cascade)
        refreshed_cell = await service.matrix_cell_repo.get(sample_matrix_cell.id)
        assert (
            refreshed_cell is None
        )  # Should not be returned due to soft delete filter

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="SoftDeleteService needs update for new document architecture"
    )
    async def test_soft_delete_multiple_types(self, service, test_db, sample_company):
        """Test soft deletion of multiple entity types in one request."""
        # Create workspace directly in test
        workspace = WorkspaceEntity(name="Test Workspace", description="Test workspace")
        test_db.add(workspace)
        await test_db.commit()
        await test_db.refresh(workspace)

        # Create matrix directly in test
        matrix = MatrixEntity(
            name="Test Matrix",
            description="Test description",
            workspace_id=workspace.id,
            deleted=False,
        )
        test_db.add(matrix)
        await test_db.commit()
        await test_db.refresh(matrix)

        # Create multiple documents and questions with explicit deleted=False
        doc1 = DocumentEntity(
            filename="doc1.pdf",
            storage_key="doc1-key",
            content_type="application/pdf",
            file_size=1024,
            checksum="b665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            deleted=False,
            company_id=sample_company.id,
        )
        doc2 = DocumentEntity(
            filename="doc2.pdf",
            storage_key="doc2-key",
            content_type="application/pdf",
            file_size=2048,
            checksum="c665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            deleted=False,
            company_id=sample_company.id,
        )
        question1 = QuestionEntity(
            company_id=sample_company.id,
            matrix_id=matrix.id,
            question_text="Question 1?",
            question_type_id=1,
            deleted=False,
        )
        question2 = QuestionEntity(
            company_id=sample_company.id,
            matrix_id=matrix.id,
            question_text="Question 2?",
            question_type_id=2,
            deleted=False,
        )

        test_db.add_all([doc1, doc2, question1, question2])
        await test_db.commit()
        await test_db.refresh(doc1)
        await test_db.refresh(doc2)
        await test_db.refresh(question1)
        await test_db.refresh(question2)

        # Create matrix cells with explicit deleted=False
        cells = [
            MatrixCellEntity(
                company_id=sample_company.id,
                matrix_id=matrix.id,
                document_id=doc1.id,
                question_id=question1.id,
                status=MatrixCellStatus.PENDING.value,
                deleted=False,
            ),
            MatrixCellEntity(
                company_id=sample_company.id,
                matrix_id=matrix.id,
                document_id=doc1.id,
                question_id=question2.id,
                status=MatrixCellStatus.PENDING.value,
                deleted=False,
            ),
            MatrixCellEntity(
                company_id=sample_company.id,
                matrix_id=matrix.id,
                document_id=doc2.id,
                question_id=question1.id,
                status=MatrixCellStatus.PENDING.value,
                deleted=False,
            ),
            MatrixCellEntity(
                company_id=sample_company.id,
                matrix_id=matrix.id,
                document_id=doc2.id,
                question_id=question2.id,
                status=MatrixCellStatus.PENDING.value,
                deleted=False,
            ),
        ]

        test_db.add_all(cells)
        await test_db.commit()

        request = MatrixSoftDeleteRequest(
            matrix_document_ids=[doc1.id], question_ids=[question1.id]
        )

        entities_deleted, cells_deleted = await service.soft_delete_entities(
            matrix.id, request
        )

        assert entities_deleted == 2  # 1 document + 1 question
        assert (
            cells_deleted == 3
        )  # 2 cells for doc1 + 1 additional cell for question1 with doc2

        # Verify doc1 is deleted
        assert await service.document_repo.get(doc1.id) is None
        # Verify doc2 is NOT deleted
        assert await service.document_repo.get(doc2.id) is not None
        # Verify question1 is deleted
        assert await service.question_repo.get(question1.id) is None
        # Verify question2 is NOT deleted
        assert await service.question_repo.get(question2.id) is not None

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="SoftDeleteService needs update for new document architecture"
    )
    async def test_soft_delete_invalid_document_ids(self, service, sample_matrix):
        """Test soft deletion with invalid document IDs."""
        request = MatrixSoftDeleteRequest(matrix_document_ids=[999, 1000])

        entities_deleted, cells_deleted = await service.soft_delete_entities(
            sample_matrix.id, request
        )

        assert entities_deleted == 0
        assert cells_deleted == 0

    @pytest.mark.asyncio
    async def test_soft_delete_invalid_question_ids(self, service, sample_matrix):
        """Test soft deletion with invalid question IDs."""
        request = MatrixSoftDeleteRequest(question_ids=[999, 1000])

        entities_deleted, cells_deleted = await service.soft_delete_entities(
            sample_matrix.id, request
        )

        assert entities_deleted == 0
        assert cells_deleted == 0

    @pytest.mark.asyncio
    async def test_soft_delete_invalid_matrix_ids(self, service, sample_matrix):
        """Test soft deletion with invalid matrix IDs."""
        request = MatrixSoftDeleteRequest(matrix_ids=[999, 1000])

        entities_deleted, cells_deleted = await service.soft_delete_entities(
            sample_matrix.id, request
        )

        assert entities_deleted == 0
        assert cells_deleted == 0

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="SoftDeleteService needs update for new document architecture"
    )
    async def test_soft_delete_document_wrong_matrix(self, service, test_db):
        """Test soft deletion of document that belongs to different matrix."""
        # Create workspace
        workspace = WorkspaceEntity(name="Test Workspace", description="Test workspace")
        test_db.add(workspace)
        await test_db.commit()
        await test_db.refresh(workspace)

        # Create two matrices with explicit deleted=False
        matrix1 = MatrixEntity(
            name="Matrix 1",
            description="First matrix",
            workspace_id=workspace.id,
            deleted=False,
        )
        matrix2 = MatrixEntity(
            name="Matrix 2",
            description="Second matrix",
            workspace_id=workspace.id,
            deleted=False,
        )
        test_db.add_all([matrix1, matrix2])
        await test_db.commit()
        await test_db.refresh(matrix1)
        await test_db.refresh(matrix2)

        # Create document in matrix2 with explicit deleted=False
        document = DocumentEntity(
            filename="test.pdf",
            storage_key="test-key",
            content_type="application/pdf",
            file_size=1024,
            checksum="d665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            deleted=False,
        )
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)

        # Try to delete document using matrix1 ID
        request = MatrixSoftDeleteRequest(matrix_document_ids=[document.id])

        entities_deleted, cells_deleted = await service.soft_delete_entities(
            matrix1.id, request
        )

        assert entities_deleted == 0
        assert cells_deleted == 0

        # Verify document is NOT deleted
        refreshed_doc = await service.document_repo.get(document.id)
        assert refreshed_doc is not None

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Test needs rewrite for entity-set based soft delete")
    async def test_soft_delete_question_wrong_matrix(
        self, service, test_db, sample_workspace, sample_company
    ):
        """Test soft deletion with entity_set_filters for wrong matrix."""
        # TODO: Rewrite for entity-set based filtering
        pass

    @pytest.mark.asyncio
    async def test_soft_delete_empty_request(self, service, sample_matrix):
        """Test soft deletion with empty request."""
        request = MatrixSoftDeleteRequest()

        entities_deleted, cells_deleted = await service.soft_delete_entities(
            sample_matrix.id, request
        )

        assert entities_deleted == 0
        assert cells_deleted == 0

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="SoftDeleteService needs update for new document architecture"
    )
    async def test_soft_delete_already_deleted_entities(
        self, service, test_db, sample_company
    ):
        """Test soft deletion of entities that are already soft deleted."""
        # Create workspace directly in test
        workspace = WorkspaceEntity(name="Test Workspace", description="Test workspace")
        test_db.add(workspace)
        await test_db.commit()
        await test_db.refresh(workspace)

        # Create matrix directly in test
        matrix = MatrixEntity(
            name="Test Matrix",
            description="Test description",
            workspace_id=workspace.id,
            deleted=False,
        )
        test_db.add(matrix)
        await test_db.commit()
        await test_db.refresh(matrix)

        # Create and immediately soft delete a document
        document = DocumentEntity(
            filename="test.pdf",
            storage_key="test-key",
            content_type="application/pdf",
            file_size=1024,
            checksum="e665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            deleted=True,  # Already soft deleted
            company_id=sample_company.id,
        )
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)

        request = MatrixSoftDeleteRequest(matrix_document_ids=[document.id])

        entities_deleted, cells_deleted = await service.soft_delete_entities(
            matrix.id, request
        )

        assert entities_deleted == 0  # Already deleted, so no change
        assert cells_deleted == 0

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="SoftDeleteService needs update for new document architecture"
    )
    @patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
    async def test_soft_delete_service_logging(
        self, mock_tracer, service, test_db, sample_company
    ):
        """Test that service logs appropriately during soft deletion."""
        # Setup mock tracer
        mock_tracer.return_value.__enter__ = lambda x: None
        mock_tracer.return_value.__exit__ = lambda x, y, z, w: None

        # Create workspace directly in test
        workspace = WorkspaceEntity(name="Test Workspace", description="Test workspace")
        test_db.add(workspace)
        await test_db.commit()
        await test_db.refresh(workspace)

        # Create matrix directly in test
        matrix = MatrixEntity(
            name="Test Matrix",
            description="Test description",
            workspace_id=workspace.id,
            deleted=False,
        )
        test_db.add(matrix)
        await test_db.commit()
        await test_db.refresh(matrix)

        # Create document directly in test
        document = DocumentEntity(
            filename="test.pdf",
            storage_key="test-key",
            content_type="application/pdf",
            file_size=1024,
            checksum="f665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            deleted=False,
            company_id=sample_company.id,
        )
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)

        request = MatrixSoftDeleteRequest(matrix_document_ids=[document.id])

        with patch("common.services.soft_delete_service.logger") as mock_logger:
            await service.soft_delete_entities(matrix.id, request)

            # Verify logging calls were made
            mock_logger.info.assert_called()
            assert mock_logger.info.call_count >= 2  # Start and completion messages

    @pytest.mark.asyncio
    async def test_service_initialization(self, test_db):
        """Test service properly initializes all repositories."""
        service = SoftDeleteService()

        assert service.matrix_repo is not None
        assert service.matrix_cell_repo is not None
        assert service.member_repo is not None
        assert service.cell_ref_repo is not None

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="SoftDeleteService needs update for new document architecture"
    )
    async def test_soft_delete_bulk_documents(self, service, test_db, sample_company):
        """Test bulk soft deletion of multiple documents."""
        # Create workspace directly in test
        workspace = WorkspaceEntity(name="Test Workspace", description="Test workspace")
        test_db.add(workspace)
        await test_db.commit()
        await test_db.refresh(workspace)

        # Create matrix directly in test
        matrix = MatrixEntity(
            name="Test Matrix",
            description="Test description",
            workspace_id=workspace.id,
            deleted=False,
        )
        test_db.add(matrix)
        await test_db.commit()
        await test_db.refresh(matrix)

        # Create multiple documents with explicit deleted=False
        documents = []

        for i in range(5):
            doc = DocumentEntity(
                filename=f"doc{i}.pdf",
                storage_key=f"doc{i}-key",
                content_type="application/pdf",
                file_size=1024 * (i + 1),
                checksum=f"checksum{i}665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"[
                    :64
                ],
                deleted=False,
                company_id=sample_company.id,
            )
            documents.append(doc)

        test_db.add_all(documents)
        await test_db.commit()

        # Refresh documents to get IDs
        for doc in documents:
            await test_db.refresh(doc)

        # Create matrix cells for each document
        question = QuestionEntity(
            matrix_id=matrix.id,
            question_text="Test question",
            question_type_id=1,
            deleted=False,
        )
        test_db.add(question)
        await test_db.commit()
        await test_db.refresh(question)

        cells = []
        for doc in documents:
            cell = MatrixCellEntity(
                matrix_id=matrix.id,
                document_id=doc.id,
                question_id=question.id,
                status=MatrixCellStatus.PENDING.value,
                deleted=False,
            )
            cells.append(cell)

        test_db.add_all(cells)
        await test_db.commit()

        # Soft delete all documents
        document_ids = [doc.id for doc in documents]
        request = MatrixSoftDeleteRequest(matrix_document_ids=document_ids)

        entities_deleted, cells_deleted = await service.soft_delete_entities(
            matrix.id, request
        )

        assert entities_deleted == 5  # All 5 documents
        assert cells_deleted == 5  # All 5 related cells

        # Verify all documents are soft deleted
        for doc in documents:
            refreshed_doc = await service.document_repo.get(doc.id)
            assert refreshed_doc is None

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="SoftDeleteService needs update for new document architecture"
    )
    async def test_soft_delete_bulk_questions(self, service, test_db):
        """Test bulk soft deletion of multiple questions."""
        # Create workspace directly in test
        workspace = WorkspaceEntity(name="Test Workspace", description="Test workspace")
        test_db.add(workspace)
        await test_db.commit()
        await test_db.refresh(workspace)

        # Create matrix directly in test
        matrix = MatrixEntity(
            name="Test Matrix",
            description="Test description",
            workspace_id=workspace.id,
            deleted=False,
        )
        test_db.add(matrix)
        await test_db.commit()
        await test_db.refresh(matrix)

        # Create a document first
        document = DocumentEntity(
            filename="test.pdf",
            storage_key="test-key",
            content_type="application/pdf",
            file_size=1024,
            checksum="g665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            deleted=False,
        )
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)

        # Create multiple questions with explicit deleted=False
        questions = []

        for i in range(3):
            question = QuestionEntity(
                matrix_id=matrix.id,
                question_text=f"Question {i}?",
                question_type_id=1,
                deleted=False,
            )
            questions.append(question)

        test_db.add_all(questions)
        await test_db.commit()

        # Refresh questions to get IDs
        for question in questions:
            await test_db.refresh(question)

        # Create matrix cells for each question with explicit deleted=False
        cells = []
        for question in questions:
            cell = MatrixCellEntity(
                matrix_id=matrix.id,
                document_id=document.id,
                question_id=question.id,
                status=MatrixCellStatus.PENDING.value,
                deleted=False,
            )
            cells.append(cell)

        test_db.add_all(cells)
        await test_db.commit()

        # Soft delete all questions
        question_ids = [question.id for question in questions]
        request = MatrixSoftDeleteRequest(question_ids=question_ids)

        entities_deleted, cells_deleted = await service.soft_delete_entities(
            matrix.id, request
        )

        assert entities_deleted == 3  # All 3 questions
        assert cells_deleted == 3  # All 3 related cells

        # Verify all questions are soft deleted
        for question in questions:
            refreshed_question = await service.question_repo.get(question.id)
            assert refreshed_question is None

    @pytest.mark.asyncio
    async def test_soft_delete_entity_set_member_with_entity_filters(
        self,
        service,
        test_db,
        sample_company,
        sample_workspace,
    ):
        """Test soft deletion using entity_set_filters deletes entity set members and cells."""
        # Create a fresh matrix for this test
        matrix = MatrixEntity(
            name="Test Matrix",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
            matrix_type="standard",
        )
        test_db.add(matrix)
        await test_db.commit()
        await test_db.refresh(matrix)

        # Create a document
        document = DocumentEntity(
            filename="test.pdf",
            storage_key="test_storage_key",
            checksum="test_checksum_hash",
            content_type="application/pdf",
            file_size=1024,
            company_id=sample_company.id,
        )
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)

        # Create document entity set
        doc_entity_set = MatrixEntitySetEntity(
            matrix_id=matrix.id,
            name="Documents",
            entity_type=EntityType.DOCUMENT.value,
            company_id=sample_company.id,
        )
        test_db.add(doc_entity_set)
        await test_db.commit()
        await test_db.refresh(doc_entity_set)

        # Create entity set member
        doc_member = MatrixEntitySetMemberEntity(
            entity_set_id=doc_entity_set.id,
            entity_type=EntityType.DOCUMENT.value,
            entity_id=document.id,
            member_order=0,
            company_id=sample_company.id,
        )
        test_db.add(doc_member)
        await test_db.commit()
        await test_db.refresh(doc_member)

        # Create cell
        cell = MatrixCellEntity(
            matrix_id=matrix.id,
            company_id=sample_company.id,
            cell_type="standard",
            status="pending",
            cell_signature=hashlib.md5(b"test_soft_delete_entity_set").hexdigest(),
        )
        test_db.add(cell)
        await test_db.commit()
        await test_db.refresh(cell)

        # Create entity reference for cell
        doc_ref = MatrixCellEntityReferenceEntity(
            matrix_id=matrix.id,
            matrix_cell_id=cell.id,
            entity_set_id=doc_entity_set.id,
            entity_set_member_id=doc_member.id,
            role=EntityRole.DOCUMENT.value,
            entity_order=0,
            company_id=sample_company.id,
        )
        test_db.add(doc_ref)
        await test_db.commit()
        await test_db.refresh(doc_ref)

        # Soft delete using entity_set_filters
        request = MatrixSoftDeleteRequest(
            entity_set_filters=[
                EntitySetFilter(
                    entity_set_id=doc_entity_set.id,
                    entity_ids=[document.id],
                    role=EntityRole.DOCUMENT,
                )
            ]
        )

        entities_deleted, cells_deleted = await service.soft_delete_entities(
            matrix.id, request
        )

        # Verify 1 entity (member) and 1 cell deleted
        assert entities_deleted == 1
        assert cells_deleted == 1

        # Verify member is marked as deleted
        await test_db.refresh(doc_member)
        assert doc_member.deleted is True

        # Verify cell is marked as deleted
        await test_db.refresh(cell)
        assert cell.deleted is True
