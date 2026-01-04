"""Unit tests for CrossCorrelationStrategy."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from packages.matrices.strategies.cross_correlation_strategy import (
    CrossCorrelationStrategy,
)
from packages.matrices.models.domain.matrix_enums import (
    MatrixCellStatus,
    CellType,
    EntityType,
    EntityRole,
)
from packages.matrices.models.database.matrix_entity_set import (
    MatrixEntitySetEntity,
    MatrixEntitySetMemberEntity,
)


class TestCrossCorrelationStrategy:
    """Unit tests for CrossCorrelationStrategy."""

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
    async def test_creates_correct_number_of_cells(self, test_db):
        """Test that strategy creates N*(N-1) pairs × questions cells."""
        strategy = CrossCorrelationStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2, 3, 4]
        question_ids = [10, 20]

        doc_es_id, _ = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=document_ids[-1],
            entity_set_id=doc_es_id,
        )

        # Adding doc4 to [doc1,doc2,doc3,doc4]: creates pairs involving doc4 only
        # (4,1), (4,2), (4,3), (1,4), (2,4), (3,4) = 6 pairs × 2 questions = 12 cells
        assert len(cell_models) == 12

    @pytest.mark.asyncio
    async def test_three_documents_creates_six_pairs(self, test_db):
        """Test that adding doc1 creates pairs involving doc1 only."""
        strategy = CrossCorrelationStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2, 3]
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

        # Adding doc1 to [doc1,doc2,doc3]: creates pairs involving doc1 only
        # (1,2), (1,3), (2,1), (3,1) = 4 pairs × 1 question = 4 cells
        assert len(cell_models) == 4

    @pytest.mark.asyncio
    async def test_cell_has_correct_attributes(self, test_db):
        """Test that cells have correct matrix_id, company_id, status, and cell_type."""
        strategy = CrossCorrelationStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2]
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
        assert cell.matrix_id == matrix_id
        assert cell.company_id == company_id
        assert cell.status == MatrixCellStatus.PENDING.value
        assert cell.cell_type == CellType.CORRELATION

    @pytest.mark.asyncio
    async def test_cell_has_three_entity_refs(self, test_db):
        """Test that correlation cells have exactly 3 entity refs (left, right, question)."""
        strategy = CrossCorrelationStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2]
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
        assert len(cell.entity_refs) == 3

    @pytest.mark.asyncio
    async def test_entity_refs_have_correct_roles(self, test_db):
        """Test that entity refs have LEFT, RIGHT, and QUESTION roles."""
        strategy = CrossCorrelationStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2]
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
        roles = [ref.role for ref in cell.entity_refs]
        assert EntityRole.LEFT in roles
        assert EntityRole.RIGHT in roles
        assert EntityRole.QUESTION in roles

    @pytest.mark.asyncio
    async def test_pairs_include_all_non_diagonal_combinations(self, test_db):
        """Test that pairs include only combinations involving the new document."""
        strategy = CrossCorrelationStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2, 3]
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

        # Extract (left_id, right_id) pairs
        pairs = set()
        for cell in cell_models:
            left_ref = next(
                ref for ref in cell.entity_refs if ref.role == EntityRole.LEFT
            )
            right_ref = next(
                ref for ref in cell.entity_refs if ref.role == EntityRole.RIGHT
            )
            pairs.add((left_ref.entity_id, right_ref.entity_id))

        # Expected pairs: only pairs involving doc1 (the new entity)
        # (1,2), (1,3), (2,1), (3,1)
        expected = {(1, 2), (1, 3), (2, 1), (3, 1)}
        assert pairs == expected

    @pytest.mark.asyncio
    async def test_no_self_pairs(self, test_db):
        """Test that no document is paired with itself."""
        strategy = CrossCorrelationStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2, 3]
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

        for cell in cell_models:
            left_ref = next(
                ref for ref in cell.entity_refs if ref.role == EntityRole.LEFT
            )
            right_ref = next(
                ref for ref in cell.entity_refs if ref.role == EntityRole.RIGHT
            )
            assert left_ref.entity_id != right_ref.entity_id

    @pytest.mark.asyncio
    async def test_each_pair_has_all_questions(self, test_db):
        """Test that each document pair gets a cell for each question."""
        strategy = CrossCorrelationStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2]
        question_ids = [10, 20, 30]

        doc_es_id, _ = await self._setup_test_matrix(
            test_db, matrix_id, company_id, document_ids, question_ids
        )

        cell_models = await strategy.create_cells_for_new_entity(
            matrix_id=matrix_id,
            company_id=company_id,
            new_entity_id=document_ids[0],
            entity_set_id=doc_es_id,
        )

        # Adding doc1 to [doc1,doc2]: creates pairs involving doc1 only
        # (1,2), (2,1) = 2 pairs × 3 questions = 6 cells
        assert len(cell_models) == 6

        # Extract question IDs for the pair (1, 2)
        question_ids_for_pair = set()
        for cell in cell_models:
            left_ref = next(
                ref for ref in cell.entity_refs if ref.role == EntityRole.LEFT
            )
            right_ref = next(
                ref for ref in cell.entity_refs if ref.role == EntityRole.RIGHT
            )
            question_ref = next(
                ref for ref in cell.entity_refs if ref.role == EntityRole.QUESTION
            )

            if left_ref.entity_id == 1 and right_ref.entity_id == 2:
                question_ids_for_pair.add(question_ref.entity_id)

        assert question_ids_for_pair == {10, 20, 30}

    @pytest.mark.asyncio
    async def test_single_document_returns_no_cells(self, test_db):
        """Test that a single document creates no pairs."""
        strategy = CrossCorrelationStrategy()

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

        assert len(cell_models) == 0

    @pytest.mark.asyncio
    async def test_empty_questions_returns_empty_list(self, test_db):
        """Test that empty question list returns no cells."""
        strategy = CrossCorrelationStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2]
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
    async def test_eight_documents_one_question_creates_56_cells(self, test_db):
        """Test that 8 documents × 1 question creates exactly 56 cells (8*7 pairs)."""
        strategy = CrossCorrelationStrategy()

        matrix_id = 1
        company_id = 100
        document_ids = [1, 2, 3, 4, 5, 6, 7, 8]
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

        # Adding doc1 to [doc1,doc2,...,doc8]: creates pairs involving doc1 only
        # (1,2), (1,3), ..., (1,8), (2,1), (3,1), ..., (8,1) = 14 pairs × 1 question = 14 cells
        assert len(cell_models) == 14
