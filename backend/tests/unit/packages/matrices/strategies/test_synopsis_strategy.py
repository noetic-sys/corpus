"""Unit tests for SynopsisStrategy."""

import pytest
from sqlalchemy import select

from packages.matrices.models.database.matrix_entity_set import (
    MatrixEntitySetEntity,
    MatrixEntitySetMemberEntity,
    MatrixCellEntityReferenceEntity,
)

from packages.matrices.strategies.synopsis_strategy import SynopsisStrategy
from packages.matrices.models.domain.matrix_enums import (
    MatrixCellStatus,
    MatrixType,
    CellType,
    EntityType,
    EntityRole,
)
from tests.conftest import create_test_matrix_cell_entity


class TestSynopsisStrategy:
    """Unit tests for SynopsisStrategy.

    Synopsis matrix: all documents × questions (1D from cell perspective).
    - New question: Creates 1 cell with ALL existing documents
    - New document: Updates ALL existing cells to include it
    """

    async def _setup_test_matrix(
        self,
        test_db,
        matrix_id: int,
        company_id: int,
        document_ids: list,
        question_ids: list,
    ):
        """Helper to set up a test matrix with entity sets and members.

        Returns: (doc_entity_set_id, question_entity_set_id)
        """

        # Create document entity set
        doc_entity_set = MatrixEntitySetEntity(
            matrix_id=matrix_id,
            name="Documents",
            entity_type=EntityType.DOCUMENT.value,
            company_id=company_id,
        )
        test_db.add(doc_entity_set)
        await test_db.commit()
        await test_db.refresh(doc_entity_set)

        # Create question entity set
        question_entity_set = MatrixEntitySetEntity(
            matrix_id=matrix_id,
            name="Questions",
            entity_type=EntityType.QUESTION.value,
            company_id=company_id,
        )
        test_db.add(question_entity_set)
        await test_db.commit()
        await test_db.refresh(question_entity_set)

        # Add document members
        for i, doc_id in enumerate(document_ids):
            member = MatrixEntitySetMemberEntity(
                entity_set_id=doc_entity_set.id,
                entity_type=EntityType.DOCUMENT.value,
                entity_id=doc_id,
                member_order=i,
                company_id=company_id,
            )
            test_db.add(member)
        await test_db.commit()

        # Add question members
        for i, question_id in enumerate(question_ids):
            member = MatrixEntitySetMemberEntity(
                entity_set_id=question_entity_set.id,
                entity_type=EntityType.QUESTION.value,
                entity_id=question_id,
                member_order=i,
                company_id=company_id,
            )
            test_db.add(member)
        await test_db.commit()

        return doc_entity_set.id, question_entity_set.id

    # =========================================================================
    # create_cells_for_new_entity tests - Adding Questions
    # =========================================================================

    @pytest.mark.asyncio
    async def test_adding_question_creates_one_cell_with_all_documents(
        self, test_db, mock_start_span
    ):
        """Test that adding a question creates exactly 1 cell containing ALL documents."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2, 3, 4, 5]
        question_ids = [10]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        # Synopsis: 1 question = 1 cell (regardless of document count)
        assert len(cell_models) == 1

    @pytest.mark.asyncio
    async def test_cell_has_correct_attributes(self, test_db, mock_start_span):
        """Test that created cells have correct matrix_id, company_id, status, and cell_type."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2]
        question_ids = [10]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        cell = cell_models[0]
        assert cell.matrix_id == matrix_id
        assert cell.company_id == company_id
        assert cell.status == MatrixCellStatus.PENDING.value
        assert cell.cell_type == CellType.SYNOPSIS

    @pytest.mark.asyncio
    async def test_cell_has_all_documents_plus_question(self, test_db, mock_start_span):
        """Test that synopsis cell has N documents + 1 question = N+1 entity refs."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2, 3]
        question_ids = [10]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        cell = cell_models[0]
        # 3 documents + 1 question = 4 entity refs
        assert len(cell.entity_refs) == 4

    @pytest.mark.asyncio
    async def test_entity_refs_have_correct_roles(self, test_db, mock_start_span):
        """Test that entity refs have DOCUMENT and QUESTION roles."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2, 3]
        question_ids = [10]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        cell = cell_models[0]
        roles = [ref.role for ref in cell.entity_refs]

        # Should have 3 DOCUMENT roles and 1 QUESTION role
        assert roles.count(EntityRole.DOCUMENT) == 3
        assert roles.count(EntityRole.QUESTION) == 1

    @pytest.mark.asyncio
    async def test_all_documents_included_in_cell(self, test_db, mock_start_span):
        """Test that all document IDs are present in the cell's entity refs."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [101, 102, 103, 104]
        question_ids = [10]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        cell = cell_models[0]
        doc_refs = [ref for ref in cell.entity_refs if ref.role == EntityRole.DOCUMENT]
        doc_entity_ids = {ref.entity_id for ref in doc_refs}

        assert doc_entity_ids == set(document_ids)

    @pytest.mark.asyncio
    async def test_question_ref_has_correct_entity_id(self, test_db, mock_start_span):
        """Test that question ref maps to correct entity ID."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2]
        question_id = 999

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, [question_id]
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_id,
            entity_set_id=q_es_id,
        )

        cell = cell_models[0]
        question_ref = next(
            ref for ref in cell.entity_refs if ref.role == EntityRole.QUESTION
        )

        assert question_ref.entity_id == question_id
        assert question_ref.entity_type == EntityType.QUESTION

    @pytest.mark.asyncio
    async def test_multiple_questions_create_multiple_cells(
        self, test_db, mock_start_span
    ):
        """Test that each question creates its own cell."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2, 3]
        question_ids = [10, 20, 30]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        # Create cells for each question
        all_cells = []
        for q_id in question_ids:
            cells = await strategy.create_cells_for_new_entity(
                matrix_id=matrix_id,
                company_id=company_id,
                new_entity_id=q_id,
                entity_set_id=q_es_id,
            )
            all_cells.extend(cells)

        # 3 questions = 3 cells
        assert len(all_cells) == 3

        # Each cell should have 3 docs + 1 question = 4 refs
        for cell in all_cells:
            assert len(cell.entity_refs) == 4

    @pytest.mark.asyncio
    async def test_no_documents_returns_empty_list(self, test_db, mock_start_span):
        """Test that adding question with no documents returns no cells."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = []  # No documents
        question_ids = [10]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        # No documents = no cells can be created
        assert len(cell_models) == 0

    @pytest.mark.asyncio
    async def test_documents_ordered_by_member_order(self, test_db, mock_start_span):
        """Test that document refs are ordered by entity_order."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [100, 200, 300]
        question_ids = [10]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        cell = cell_models[0]
        doc_refs = sorted(
            [ref for ref in cell.entity_refs if ref.role == EntityRole.DOCUMENT],
            key=lambda r: r.entity_order,
        )

        # Documents should be in order 0, 1, 2
        for i, doc_ref in enumerate(doc_refs):
            assert doc_ref.entity_order == i

    # =========================================================================
    # create_cells_for_new_entity tests - Adding Documents
    # =========================================================================

    @pytest.mark.asyncio
    async def test_adding_document_with_no_questions_returns_empty(
        self, test_db, mock_start_span
    ):
        """Test that adding document with no questions returns no cells."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1]
        question_ids = []  # No questions

        doc_es_id, _ = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=document_ids[0],
            entity_set_id=doc_es_id,
        )

        # No questions = no cells needed
        assert len(cell_models) == 0

    @pytest.mark.asyncio
    async def test_adding_document_when_cells_exist_returns_empty(
        self, test_db, mock_start_span
    ):
        """Test that adding document when cells already exist returns empty (update path handles it)."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2]  # Will add doc 2 after doc 1
        question_ids = [10]

        doc_es_id, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        # First, create a cell for the question (simulating existing state)
        initial_cells = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )
        assert len(initial_cells) == 1

        # Persist the cell to the database WITH entity references (simulating batch_processing_service)
        persisted_cell = create_test_matrix_cell_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            cell_type=CellType.SYNOPSIS.value,
            status=MatrixCellStatus.PENDING.value,
        )
        test_db.add(persisted_cell)
        await test_db.commit()
        await test_db.refresh(persisted_cell)

        # Get the question member ID to create the entity reference
        result = await test_db.execute(
            select(MatrixEntitySetMemberEntity).where(
                MatrixEntitySetMemberEntity.entity_set_id == q_es_id,
                MatrixEntitySetMemberEntity.entity_id == question_ids[0],
            )
        )
        question_member = result.scalar_one()

        # Create entity reference linking cell to question (this is what strategy checks)
        question_ref = MatrixCellEntityReferenceEntity(
            matrix_id=matrix_id,
            matrix_cell_id=persisted_cell.id,
            entity_set_id=q_es_id,
            entity_set_member_id=question_member.id,
            role=EntityRole.QUESTION.value,
            entity_order=0,
            company_id=company_id,
        )
        test_db.add(question_ref)
        await test_db.commit()

        # Now add another document - should return empty (handled by update_cells_for_new_entity)
        new_cells = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=document_ids[1],
            entity_set_id=doc_es_id,
        )

        # No new cells - update path will handle adding doc to existing cells
        assert len(new_cells) == 0

    # =========================================================================
    # update_cells_for_new_entity tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_update_cells_creates_specs_for_all_existing_cells(
        self, test_db, mock_start_span
    ):
        """Test that update_cells_for_new_entity creates update specs for all existing cells."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1]
        question_ids = [10, 20, 30]

        doc_es_id, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        # Create cells for all questions first
        for q_id in question_ids:
            cell = create_test_matrix_cell_entity(
                matrix_id=matrix_id,
                company_id=company_id,
                cell_type=CellType.SYNOPSIS.value,
                status=MatrixCellStatus.COMPLETED.value,
            )
            test_db.add(cell)
        await test_db.commit()

        # Add another document to the entity set
        new_doc_id = 2
        new_member = MatrixEntitySetMemberEntity(
            entity_set_id=doc_es_id,
            entity_type=EntityType.DOCUMENT.value,
            entity_id=new_doc_id,
            member_order=1,
            company_id=company_id,
        )
        test_db.add(new_member)
        await test_db.commit()

        # Get update specs
        update_specs = await strategy.update_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=new_doc_id,
            entity_set_id=doc_es_id,
        )

        # Should have 3 update specs (one for each existing cell)
        assert len(update_specs) == 3

    @pytest.mark.asyncio
    async def test_update_specs_have_reset_status_true(self, test_db, mock_start_span):
        """Test that update specs set reset_status=True to trigger reprocessing."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1]
        question_ids = [10]

        doc_es_id, _ = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        # Create existing cell
        cell = create_test_matrix_cell_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            cell_type=CellType.SYNOPSIS.value,
            status=MatrixCellStatus.COMPLETED.value,
        )
        test_db.add(cell)
        await test_db.commit()

        # Add new document
        new_doc_id = 2
        new_member = MatrixEntitySetMemberEntity(
            entity_set_id=doc_es_id,
            entity_type=EntityType.DOCUMENT.value,
            entity_id=new_doc_id,
            member_order=1,
            company_id=company_id,
        )
        test_db.add(new_member)
        await test_db.commit()

        update_specs = await strategy.update_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=new_doc_id,
            entity_set_id=doc_es_id,
        )

        assert len(update_specs) == 1
        assert update_specs[0].reset_status is True

    @pytest.mark.asyncio
    async def test_update_specs_include_new_document_ref(
        self, test_db, mock_start_span
    ):
        """Test that update specs include entity ref for new document."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1]
        question_ids = [10]

        doc_es_id, _ = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        # Create existing cell
        cell = create_test_matrix_cell_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            cell_type=CellType.SYNOPSIS.value,
            status=MatrixCellStatus.COMPLETED.value,
        )
        test_db.add(cell)
        await test_db.commit()

        # Add new document
        new_doc_id = 999
        new_member = MatrixEntitySetMemberEntity(
            entity_set_id=doc_es_id,
            entity_type=EntityType.DOCUMENT.value,
            entity_id=new_doc_id,
            member_order=1,
            company_id=company_id,
        )
        test_db.add(new_member)
        await test_db.commit()

        update_specs = await strategy.update_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=new_doc_id,
            entity_set_id=doc_es_id,
        )

        assert len(update_specs) == 1
        assert len(update_specs[0].entity_refs_to_add) == 1

        new_ref = update_specs[0].entity_refs_to_add[0]
        assert new_ref.entity_id == new_doc_id
        assert new_ref.entity_type == EntityType.DOCUMENT
        assert new_ref.role == EntityRole.DOCUMENT

    @pytest.mark.asyncio
    async def test_update_for_question_returns_empty(self, test_db, mock_start_span):
        """Test that update_cells_for_new_entity returns empty for questions."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1]
        question_ids = [10]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        # Questions don't trigger updates - they create new cells
        update_specs = await strategy.update_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        assert len(update_specs) == 0

    @pytest.mark.asyncio
    async def test_update_with_no_existing_cells_returns_empty(
        self, test_db, mock_start_span
    ):
        """Test that update returns empty when no cells exist yet."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1]
        question_ids = []  # No questions means no cells

        doc_es_id, _ = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        update_specs = await strategy.update_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=document_ids[0],
            entity_set_id=doc_es_id,
        )

        assert len(update_specs) == 0

    # =========================================================================
    # Metadata tests
    # =========================================================================

    def test_get_matrix_type(self):
        """Test that strategy returns SYNOPSIS matrix type."""
        strategy = SynopsisStrategy()
        assert strategy.get_matrix_type() == MatrixType.SYNOPSIS

    def test_get_cell_type(self):
        """Test that strategy returns SYNOPSIS cell type."""
        strategy = SynopsisStrategy()
        assert strategy.get_cell_type() == CellType.SYNOPSIS

    def test_get_entity_set_definitions(self):
        """Test that strategy returns correct entity set definitions."""
        strategy = SynopsisStrategy()
        definitions = strategy.get_entity_set_definitions()

        assert len(definitions) == 2

        doc_def = next(d for d in definitions if d.entity_type == EntityType.DOCUMENT)
        assert doc_def.name == "Documents"

        question_def = next(
            d for d in definitions if d.entity_type == EntityType.QUESTION
        )
        assert question_def.name == "Questions"

    def test_get_structure_metadata(self):
        """Test that strategy returns meaningful structure metadata."""
        strategy = SynopsisStrategy()
        metadata = strategy.get_structure_metadata()

        assert "synopsis" in metadata.explanation.lower()
        assert "DOCUMENT" in metadata.roles_explanation
        assert "QUESTION" in metadata.roles_explanation

    # =========================================================================
    # Edge case tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_ten_documents_one_question_creates_one_cell(
        self, test_db, mock_start_span
    ):
        """Test that 10 documents + 1 question = 1 cell (not 10)."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = list(range(1, 11))  # 10 documents
        question_ids = [100]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        # Synopsis: always 1 cell per question
        assert len(cell_models) == 1
        # Cell should have 10 docs + 1 question = 11 refs
        assert len(cell_models[0].entity_refs) == 11

    @pytest.mark.asyncio
    async def test_large_document_set_all_included(self, test_db, mock_start_span):
        """Test that all documents are included even with large sets."""
        strategy = SynopsisStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = list(range(1, 51))  # 50 documents
        question_ids = [100]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        cell = cell_models[0]
        doc_refs = [ref for ref in cell.entity_refs if ref.role == EntityRole.DOCUMENT]

        # All 50 documents should be included
        assert len(doc_refs) == 50
        doc_ids = {ref.entity_id for ref in doc_refs}
        assert doc_ids == set(document_ids)
