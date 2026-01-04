"""Unit tests for StandardMatrixStrategy."""

import pytest
from packages.matrices.models.database.matrix_entity_set import (
    MatrixEntitySetEntity,
    MatrixEntitySetMemberEntity,
)
from unittest.mock import patch, MagicMock, AsyncMock

from packages.matrices.strategies.standard_matrix_strategy import StandardMatrixStrategy
from packages.matrices.models.domain.matrix_enums import (
    MatrixCellStatus,
    CellType,
    EntityType,
    EntityRole,
)


class TestStandardMatrixStrategy:
    """Unit tests for StandardMatrixStrategy."""

    @pytest.fixture(autouse=True)
    def setup_span_mock(self):
        """Set up the span mock to work properly with async methods."""
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

    @pytest.mark.asyncio
    async def test_creates_cells_for_all_document_question_combinations(self, test_db):
        """Test that strategy creates one cell for each document × question."""
        strategy = StandardMatrixStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2, 3]
        question_ids = [10, 20]

        doc_es_id, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        # Add a new question - should create cells with ALL documents
        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        # Should create 3 docs × 1 question = 3 cells
        assert len(cell_models) == 3

    @pytest.mark.asyncio
    async def test_cell_has_correct_attributes(self, test_db):
        """Test that created cells have correct matrix_id, company_id, status, and cell_type."""
        strategy = StandardMatrixStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1]
        question_ids = [10]

        doc_es_id, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=document_ids[0],
            entity_set_id=doc_es_id,
        )

        cell = cell_models[0]
        assert cell.matrix_id == matrix_id
        assert cell.company_id == company_id
        assert cell.status == MatrixCellStatus.PENDING.value
        assert cell.cell_type == CellType.STANDARD

    @pytest.mark.asyncio
    async def test_cell_has_two_entity_refs(self, test_db):
        """Test that standard matrix cells have exactly 2 entity references (document + question)."""
        strategy = StandardMatrixStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1]
        question_ids = [10]

        doc_es_id, _ = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=document_ids[0],
            entity_set_id=doc_es_id,
        )

        cell = cell_models[0]
        assert len(cell.entity_refs) == 2

    @pytest.mark.asyncio
    async def test_entity_refs_have_correct_roles(self, test_db):
        """Test that entity refs have DOCUMENT and QUESTION roles."""
        strategy = StandardMatrixStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [5]
        question_ids = [15]

        doc_es_id, _ = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=document_ids[0],
            entity_set_id=doc_es_id,
        )

        cell = cell_models[0]
        roles = [ref.role for ref in cell.entity_refs]
        assert EntityRole.DOCUMENT in roles
        assert EntityRole.QUESTION in roles

    @pytest.mark.asyncio
    async def test_entity_refs_have_correct_entity_ids(self, test_db):
        """Test that entity refs map to correct entity IDs."""
        strategy = StandardMatrixStrategy()

        matrix_id = 1
        company_id = 100
        doc_id = 5
        question_id = 15

        doc_es_id, _ = await self._setup_test_matrix(
            test_db, matrix_id, company_id, [doc_id], [question_id]
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=doc_id,
            entity_set_id=doc_es_id,
        )

        cell = cell_models[0]

        doc_ref = next(
            ref for ref in cell.entity_refs if ref.role == EntityRole.DOCUMENT
        )
        assert doc_ref.entity_id == doc_id
        assert doc_ref.entity_type == EntityType.DOCUMENT
        assert doc_ref.entity_order == 0

        question_ref = next(
            ref for ref in cell.entity_refs if ref.role == EntityRole.QUESTION
        )
        assert question_ref.entity_id == question_id
        assert question_ref.entity_type == EntityType.QUESTION
        assert question_ref.entity_order == 1

    @pytest.mark.asyncio
    async def test_correct_combinations_generated(self, test_db):
        """Test that all document × question combinations are generated."""
        strategy = StandardMatrixStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2]
        question_ids = [10, 20]

        doc_es_id, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        # Add new question - should pair with all documents
        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        # Extract (doc_id, question_id) tuples from cells
        combinations = set()
        for cell in cell_models:
            doc_ref = next(
                ref for ref in cell.entity_refs if ref.role == EntityRole.DOCUMENT
            )
            q_ref = next(
                ref for ref in cell.entity_refs if ref.role == EntityRole.QUESTION
            )
            combinations.add((doc_ref.entity_id, q_ref.entity_id))

        expected = {(1, 10), (2, 10)}
        assert combinations == expected

    @pytest.mark.asyncio
    async def test_empty_documents_returns_empty_list(self, test_db):
        """Test that empty document list returns no cells."""
        strategy = StandardMatrixStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = []
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

        assert len(cell_models) == 0

    @pytest.mark.asyncio
    async def test_empty_questions_returns_empty_list(self, test_db):
        """Test that empty question list returns no cells."""
        strategy = StandardMatrixStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1]
        question_ids = []

        doc_es_id, _ = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=document_ids[0],
            entity_set_id=doc_es_id,
        )

        assert len(cell_models) == 0

    @pytest.mark.asyncio
    async def test_adding_new_document_pairs_with_all_questions(self, test_db):
        """Test that adding a new document creates cells with all questions."""
        strategy = StandardMatrixStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2, 3]
        question_ids = [10, 20]

        doc_es_id, _ = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        # Add new document - should pair with all questions
        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=document_ids[0],
            entity_set_id=doc_es_id,
        )

        # Should create 1 doc × 2 questions = 2 cells
        assert len(cell_models) == 2

    @pytest.mark.asyncio
    async def test_adding_new_question_pairs_with_all_documents(self, test_db):
        """Test that adding a new question creates cells with all documents."""
        strategy = StandardMatrixStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2, 3, 4, 5]
        question_ids = [10, 20]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        # Add new question - should pair with all documents
        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        # Should create 5 docs × 1 question = 5 cells
        assert len(cell_models) == 5

    @pytest.mark.asyncio
    async def test_ten_documents_creates_correct_cells_for_new_question(self, test_db):
        """Test that adding a question to 10 documents creates 10 cells."""
        strategy = StandardMatrixStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = list(range(1, 11))  # 1-10
        question_ids = [100, 200]

        _, q_es_id = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=question_ids[0],
            entity_set_id=q_es_id,
        )

        assert len(cell_models) == 10
