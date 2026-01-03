"""Unit tests for CellEntityReferenceRepository."""

import pytest
import hashlib
from unittest.mock import patch, MagicMock, AsyncMock

from packages.matrices.repositories.cell_entity_reference_repository import (
    CellEntityReferenceRepository,
)
from packages.matrices.models.database.matrix_entity_set import (
    MatrixCellEntityReferenceEntity,
)
from packages.matrices.models.domain.matrix_enums import EntityRole
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixCellEntityReferenceCreateModel,
)

from packages.matrices.models.database.matrix import MatrixCellEntity


class TestCellEntityReferenceRepository:
    """Unit tests for CellEntityReferenceRepository."""

    @pytest.fixture
    async def reference_repo(self, test_db):
        """Create a CellEntityReferenceRepository instance."""
        return CellEntityReferenceRepository()

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

    @pytest.mark.asyncio
    async def test_get_by_cell_id(
        self,
        reference_repo,
        test_db,
        sample_matrix,
        sample_matrix_cell,
        sample_entity_set,
        sample_entity_set_member,
        sample_company,
    ):
        """Test getting all entity references for a cell."""
        # Create references (standard cell: 1 document + 1 question)
        references = [
            MatrixCellEntityReferenceEntity(
                matrix_id=sample_matrix.id,
                matrix_cell_id=sample_matrix_cell.id,
                entity_set_id=sample_entity_set.id,
                entity_set_member_id=sample_entity_set_member.id,
                company_id=sample_company.id,
                role=EntityRole.DOCUMENT.value,
                entity_order=0,
            ),
            MatrixCellEntityReferenceEntity(
                matrix_id=sample_matrix.id,
                matrix_cell_id=sample_matrix_cell.id,
                entity_set_id=sample_entity_set.id,
                entity_set_member_id=sample_entity_set_member.id,
                company_id=sample_company.id,
                role=EntityRole.QUESTION.value,
                entity_order=1,
            ),
        ]
        test_db.add_all(references)
        await test_db.commit()

        # Get references
        result = await reference_repo.get_by_cell_id(sample_matrix_cell.id)

        assert len(result) == 2
        # Check ordering
        assert result[0].entity_order == 0
        assert result[1].entity_order == 1

    @pytest.mark.asyncio
    async def test_get_by_cell_id_and_role(
        self, reference_repo, sample_cell_entity_reference
    ):
        """Test getting entity reference by cell and role."""
        result = await reference_repo.get_by_cell_id_and_role(
            sample_cell_entity_reference.matrix_cell_id, EntityRole.DOCUMENT
        )

        assert result is not None
        assert result.id == sample_cell_entity_reference.id
        assert result.role == EntityRole.DOCUMENT

    @pytest.mark.asyncio
    async def test_get_by_cell_id_and_role_not_found(
        self, reference_repo, sample_matrix_cell
    ):
        """Test getting reference that doesn't exist."""
        result = await reference_repo.get_by_cell_id_and_role(
            sample_matrix_cell.id, EntityRole.LEFT
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_cells_by_entity_member(
        self,
        reference_repo,
        test_db,
        sample_matrix,
        sample_entity_set,
        sample_entity_set_member,
        sample_company,
    ):
        """Test finding cells that use a specific entity member."""
        # Create cells

        cells = []
        for i in range(3):
            cell = MatrixCellEntity(
                matrix_id=sample_matrix.id,
                company_id=sample_company.id,
                cell_type="standard",
                status="pending",
                cell_signature=hashlib.md5(f"test_cell_ref_{i}".encode()).hexdigest(),
            )
            cells.append(cell)

        test_db.add_all(cells)
        await test_db.commit()
        for cell in cells:
            await test_db.refresh(cell)

        # Create references for each cell with the same entity member
        references = []
        for cell in cells:
            ref = MatrixCellEntityReferenceEntity(
                matrix_id=sample_matrix.id,
                matrix_cell_id=cell.id,
                entity_set_id=sample_entity_set.id,
                entity_set_member_id=sample_entity_set_member.id,
                company_id=sample_company.id,
                role=EntityRole.DOCUMENT.value,
                entity_order=0,
            )
            references.append(ref)

        test_db.add_all(references)
        await test_db.commit()

        # Get cells by entity member
        result = await reference_repo.get_cells_by_entity_member(
            sample_matrix.id,
            sample_entity_set.id,
            sample_entity_set_member.id,
            EntityRole.DOCUMENT,
        )

        assert len(result) == 3
        cell_ids = [c.id for c in cells]
        assert all(cell_id in cell_ids for cell_id in result)

    @pytest.mark.asyncio
    async def test_create_reference(
        self,
        reference_repo,
        sample_matrix,
        sample_matrix_cell,
        sample_entity_set,
        sample_entity_set_member,
        sample_company,
    ):
        """Test creating a new cell entity reference."""
        create_model = MatrixCellEntityReferenceCreateModel(
            matrix_id=sample_matrix.id,
            matrix_cell_id=sample_matrix_cell.id,
            entity_set_id=sample_entity_set.id,
            entity_set_member_id=sample_entity_set_member.id,
            company_id=sample_company.id,
            role=EntityRole.DOCUMENT,
            entity_order=0,
        )

        result = await reference_repo.create_reference(create_model)

        assert result is not None
        assert result.matrix_cell_id == sample_matrix_cell.id
        assert result.role == EntityRole.DOCUMENT

    @pytest.mark.asyncio
    async def test_create_references_batch(
        self,
        reference_repo,
        sample_matrix,
        sample_matrix_cell,
        sample_entity_set,
        sample_entity_set_member,
        sample_company,
    ):
        """Test creating multiple references in a batch."""
        create_models = [
            MatrixCellEntityReferenceCreateModel(
                matrix_id=sample_matrix.id,
                matrix_cell_id=sample_matrix_cell.id,
                entity_set_id=sample_entity_set.id,
                entity_set_member_id=sample_entity_set_member.id,
                company_id=sample_company.id,
                role=role,
                entity_order=i,
            )
            for i, role in enumerate([EntityRole.DOCUMENT, EntityRole.QUESTION])
        ]

        result = await reference_repo.create_references_batch(create_models)

        assert len(result) == 2
        assert result[0].role == EntityRole.DOCUMENT
        assert result[1].role == EntityRole.QUESTION

    @pytest.mark.asyncio
    async def test_get_by_matrix_id(
        self,
        reference_repo,
        test_db,
        sample_matrix,
        sample_matrix_cell,
        sample_entity_set,
        sample_entity_set_member,
        sample_company,
    ):
        """Test getting all references for a matrix."""
        # Create references
        references = []
        for i in range(3):
            ref = MatrixCellEntityReferenceEntity(
                matrix_id=sample_matrix.id,
                matrix_cell_id=sample_matrix_cell.id,
                entity_set_id=sample_entity_set.id,
                entity_set_member_id=sample_entity_set_member.id,
                company_id=sample_company.id,
                role=EntityRole.DOCUMENT.value if i == 0 else EntityRole.QUESTION.value,
                entity_order=i,
            )
            references.append(ref)

        test_db.add_all(references)
        await test_db.commit()

        # Get all references
        result = await reference_repo.get_by_matrix_id(sample_matrix.id)

        assert len(result) >= 3  # May include fixture reference

    @pytest.mark.asyncio
    async def test_delete_by_cell_id(
        self,
        reference_repo,
        test_db,
        sample_matrix,
        sample_matrix_cell,
        sample_entity_set,
        sample_entity_set_member,
        sample_company,
    ):
        """Test deleting all references for a cell."""
        # Create references
        references = []
        for i in range(2):
            ref = MatrixCellEntityReferenceEntity(
                matrix_id=sample_matrix.id,
                matrix_cell_id=sample_matrix_cell.id,
                entity_set_id=sample_entity_set.id,
                entity_set_member_id=sample_entity_set_member.id,
                company_id=sample_company.id,
                role=EntityRole.DOCUMENT.value if i == 0 else EntityRole.QUESTION.value,
                entity_order=i,
            )
            references.append(ref)

        test_db.add_all(references)
        await test_db.commit()

        # Delete references
        await reference_repo.delete_by_cell_id(sample_matrix_cell.id)
        await test_db.commit()

        # Verify deletion
        result = await reference_repo.get_by_cell_id(sample_matrix_cell.id)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_role_required_for_queries(
        self,
        reference_repo,
        test_db,
        sample_matrix,
        sample_entity_set,
        sample_entity_set_member,
        sample_company,
    ):
        """Test that role is required and distinguishes between axes."""
        # Create two cells with same entity member but different roles

        cell1 = MatrixCellEntity(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            cell_type="correlation",
            status="pending",
            cell_signature=hashlib.md5(b"test_role_1").hexdigest(),
        )
        cell2 = MatrixCellEntity(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            cell_type="correlation",
            status="pending",
            cell_signature=hashlib.md5(b"test_role_2").hexdigest(),
        )
        test_db.add_all([cell1, cell2])
        await test_db.commit()
        await test_db.refresh(cell1)
        await test_db.refresh(cell2)

        # Cell1 uses member as LEFT, Cell2 uses member as RIGHT
        ref1 = MatrixCellEntityReferenceEntity(
            matrix_id=sample_matrix.id,
            matrix_cell_id=cell1.id,
            entity_set_id=sample_entity_set.id,
            entity_set_member_id=sample_entity_set_member.id,
            company_id=sample_company.id,
            role=EntityRole.LEFT.value,
            entity_order=0,
        )
        ref2 = MatrixCellEntityReferenceEntity(
            matrix_id=sample_matrix.id,
            matrix_cell_id=cell2.id,
            entity_set_id=sample_entity_set.id,
            entity_set_member_id=sample_entity_set_member.id,
            company_id=sample_company.id,
            role=EntityRole.RIGHT.value,
            entity_order=1,
        )
        test_db.add_all([ref1, ref2])
        await test_db.commit()

        # Query for LEFT role only
        left_cells = await reference_repo.get_cells_by_entity_member(
            sample_matrix.id,
            sample_entity_set.id,
            sample_entity_set_member.id,
            EntityRole.LEFT,
        )

        # Query for RIGHT role only
        right_cells = await reference_repo.get_cells_by_entity_member(
            sample_matrix.id,
            sample_entity_set.id,
            sample_entity_set_member.id,
            EntityRole.RIGHT,
        )

        # Verify role distinguishes the results
        assert cell1.id in left_cells
        assert cell1.id not in right_cells
        assert cell2.id in right_cells
        assert cell2.id not in left_cells

    @pytest.mark.asyncio
    async def test_company_id_filtering(
        self,
        reference_repo,
        test_db,
        sample_matrix,
        sample_matrix_cell,
        sample_entity_set,
        sample_entity_set_member,
        sample_company,
        second_company,
    ):
        """Test that company_id filtering works correctly."""
        # Create reference for first company
        ref = MatrixCellEntityReferenceEntity(
            matrix_id=sample_matrix.id,
            matrix_cell_id=sample_matrix_cell.id,
            entity_set_id=sample_entity_set.id,
            entity_set_member_id=sample_entity_set_member.id,
            company_id=sample_company.id,
            role=EntityRole.DOCUMENT.value,
            entity_order=0,
        )
        test_db.add(ref)
        await test_db.commit()

        # Query with correct company_id
        result = await reference_repo.get_by_cell_id(
            sample_matrix_cell.id, company_id=sample_company.id
        )
        assert len(result) == 1

        # Query with different company_id
        result = await reference_repo.get_by_cell_id(
            sample_matrix_cell.id, company_id=second_company.id
        )
        assert len(result) == 0
