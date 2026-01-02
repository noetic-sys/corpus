"""Unit tests for EntitySetRepository."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from packages.matrices.models.database import MatrixEntity
from packages.matrices.repositories.entity_set_repository import EntitySetRepository
from packages.matrices.models.domain.matrix_enums import EntityType
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixEntitySetCreateModel,
)


class TestEntitySetRepository:
    """Unit tests for EntitySetRepository."""

    @pytest.fixture
    async def entity_set_repo(self, test_db):
        """Create an EntitySetRepository instance."""
        return EntitySetRepository(test_db)

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
    async def test_get_by_matrix_id(
        self, entity_set_repo, test_db, sample_matrix, sample_company
    ):
        """Test getting all entity sets for a matrix."""
        # Entity sets already created by sample_matrix fixture
        # Get entity sets
        result = await entity_set_repo.get_by_matrix_id(sample_matrix.id)

        assert len(result) == 2
        assert any(es.entity_type == EntityType.DOCUMENT for es in result)
        assert any(es.entity_type == EntityType.QUESTION for es in result)

    @pytest.mark.asyncio
    async def test_get_by_matrix_and_type(
        self, entity_set_repo, test_db, sample_matrix, sample_company
    ):
        """Test getting entity set by matrix and type."""
        # Entity sets already created by sample_matrix fixture
        # Get document entity set
        result = await entity_set_repo.get_by_matrix_and_type(
            sample_matrix.id, EntityType.DOCUMENT
        )

        assert result is not None
        assert result.entity_type == EntityType.DOCUMENT

    @pytest.mark.asyncio
    async def test_get_by_matrix_and_type_not_found(
        self, entity_set_repo, test_db, sample_workspace, sample_company
    ):
        """Test getting entity set that doesn't exist."""
        # Create a matrix WITHOUT entity sets

        matrix = MatrixEntity(
            name="Empty Matrix",
            workspace_id=sample_workspace.id,
            company_id=sample_company.id,
            matrix_type="standard",
        )
        test_db.add(matrix)
        await test_db.commit()
        await test_db.refresh(matrix)

        result = await entity_set_repo.get_by_matrix_and_type(
            matrix.id, EntityType.DOCUMENT
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_create_entity_set(
        self, entity_set_repo, sample_matrix, sample_company
    ):
        """Test creating a new entity set."""
        create_model = MatrixEntitySetCreateModel(
            matrix_id=sample_matrix.id,
            company_id=sample_company.id,
            name="documents",
            entity_type=EntityType.DOCUMENT,
        )

        result = await entity_set_repo.create_entity_set(create_model)

        assert result is not None
        assert result.matrix_id == sample_matrix.id
        assert result.name == "documents"
        assert result.entity_type == EntityType.DOCUMENT

    @pytest.mark.asyncio
    async def test_get_by_ids(
        self, entity_set_repo, test_db, sample_matrix, sample_company
    ):
        """Test getting multiple entity sets by IDs."""
        # Entity sets already created by sample_matrix fixture
        # Get all entity sets for the matrix to get their IDs
        all_sets = await entity_set_repo.get_by_matrix_id(sample_matrix.id)
        ids = [s.id for s in all_sets]

        # Get by IDs
        result = await entity_set_repo.get_by_ids(ids)

        assert len(result) == 2
        assert all(r.id in ids for r in result)

    @pytest.mark.asyncio
    async def test_get_by_ids_empty_list(self, entity_set_repo):
        """Test get_by_ids with empty list."""
        result = await entity_set_repo.get_by_ids([])
        assert result == []

    @pytest.mark.asyncio
    async def test_company_id_filtering(
        self, entity_set_repo, test_db, sample_matrix, sample_company, second_company
    ):
        """Test that company_id filtering works correctly."""
        # Entity sets already created by sample_matrix fixture for sample_company

        # Query with correct company_id
        result = await entity_set_repo.get_by_matrix_id(
            sample_matrix.id, company_id=sample_company.id
        )
        assert len(result) == 2  # Both document and question entity sets

        # Query with different company_id
        result = await entity_set_repo.get_by_matrix_id(
            sample_matrix.id, company_id=second_company.id
        )
        assert len(result) == 0
