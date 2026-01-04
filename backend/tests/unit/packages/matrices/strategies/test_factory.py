"""Unit tests for CellStrategyFactory."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from packages.matrices.strategies.models import (
    EntitySetDefinition,
    MatrixStructureMetadata,
)
from packages.matrices.models.domain.matrix_enums import CellType, EntityType
from packages.matrices.strategies.factory import CellStrategyFactory
from packages.matrices.strategies.standard_matrix_strategy import StandardMatrixStrategy
from packages.matrices.strategies.cross_correlation_strategy import (
    CrossCorrelationStrategy,
)
from packages.matrices.strategies.base_strategy import BaseCellCreationStrategy
from packages.matrices.models.domain.matrix_enums import MatrixType


class TestCellStrategyFactory:
    """Unit tests for CellStrategyFactory."""

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

    def test_get_strategy_for_standard_matrix(self):
        """Test that STANDARD matrix type returns StandardMatrixStrategy."""
        mock_db = AsyncMock()
        strategy = CellStrategyFactory.get_strategy(MatrixType.STANDARD)
        assert isinstance(strategy, StandardMatrixStrategy)

    def test_get_strategy_for_cross_correlation_matrix(self):
        """Test that CROSS_CORRELATION matrix type returns CrossCorrelationStrategy."""
        mock_db = AsyncMock()
        strategy = CellStrategyFactory.get_strategy(MatrixType.CROSS_CORRELATION)
        assert isinstance(strategy, CrossCorrelationStrategy)

    def test_get_strategy_for_unknown_type_raises_error(self):
        """Test that unknown matrix type raises ValueError."""
        mock_db = AsyncMock()
        # First need to unregister GENERIC_CORRELATION to test unknown type
        saved_strategy = CellStrategyFactory._strategies.pop(
            MatrixType.GENERIC_CORRELATION, None
        )
        try:
            with pytest.raises(ValueError, match="No strategy found for matrix type"):
                CellStrategyFactory.get_strategy(MatrixType.GENERIC_CORRELATION)
        finally:
            # Restore it if it existed
            if saved_strategy:
                CellStrategyFactory._strategies[MatrixType.GENERIC_CORRELATION] = (
                    saved_strategy
                )

    def test_register_strategy_adds_new_strategy(self):
        """Test that register_strategy allows adding custom strategies."""

        # Create a mock strategy class
        class CustomStrategy(BaseCellCreationStrategy):
            def get_entity_set_definitions(self):
                return [
                    EntitySetDefinition(name="Custom", entity_type=EntityType.DOCUMENT)
                ]

            def get_matrix_type(self):
                return MatrixType.GENERIC_CORRELATION

            def get_cell_type(self):
                return CellType.STANDARD

            def get_structure_metadata(self):
                return MatrixStructureMetadata(
                    explanation="Custom matrix type for testing",
                    roles_explanation={"DOCUMENT": "Test document role"},
                    system_placeholders={},
                    cell_structure="Test cell structure",
                )

            async def create_cells_for_new_entity(
                self, matrix_id, company_id, new_entity_id, entity_set_id
            ):
                return []

            async def load_cell_data(self, cell_id, company_id):
                return None

        # Register it for GENERIC_CORRELATION type
        CellStrategyFactory.register_strategy(
            MatrixType.GENERIC_CORRELATION, CustomStrategy
        )

        # Verify we can retrieve it (note: factory returns instance, not class)
        strategy = CellStrategyFactory.get_strategy(MatrixType.GENERIC_CORRELATION)
        assert isinstance(strategy, CustomStrategy)

        # Clean up: remove the custom strategy from the registry
        del CellStrategyFactory._strategies[MatrixType.GENERIC_CORRELATION]

    def test_register_strategy_overwrites_existing(self):
        """Test that registering a strategy for existing type overwrites it."""

        # Create a custom strategy
        class CustomStandardStrategy(BaseCellCreationStrategy):
            def get_entity_set_definitions(self):
                return [
                    EntitySetDefinition(name="Custom", entity_type=EntityType.DOCUMENT)
                ]

            def get_matrix_type(self):
                return MatrixType.STANDARD

            def get_cell_type(self):
                return CellType.STANDARD

            def get_structure_metadata(self):
                return MatrixStructureMetadata(
                    explanation="Custom standard matrix for testing",
                    roles_explanation={"DOCUMENT": "Test document role"},
                    system_placeholders={},
                    cell_structure="Test cell structure",
                )

            async def create_cells_for_new_entity(
                self, matrix_id, company_id, new_entity_id, entity_set_id
            ):
                return []

            async def load_cell_data(self, cell_id, company_id):
                return None

        # Save original strategy
        original_strategy_class = CellStrategyFactory._strategies[MatrixType.STANDARD]

        try:
            # Register custom strategy for STANDARD type
            CellStrategyFactory.register_strategy(
                MatrixType.STANDARD, CustomStandardStrategy
            )

            # Verify it's been replaced
            strategy = CellStrategyFactory.get_strategy(MatrixType.STANDARD)
            assert isinstance(strategy, CustomStandardStrategy)
            assert not isinstance(strategy, StandardMatrixStrategy)

        finally:
            # Restore original strategy
            CellStrategyFactory._strategies[MatrixType.STANDARD] = (
                original_strategy_class
            )

    def test_get_strategy_returns_new_instance_each_time(self):
        """Test that get_strategy returns a new instance on each call."""
        mock_db = AsyncMock()
        strategy1 = CellStrategyFactory.get_strategy(MatrixType.STANDARD)
        strategy2 = CellStrategyFactory.get_strategy(MatrixType.STANDARD)

        # Should be same type but different instances
        assert type(strategy1) == type(strategy2)
        assert strategy1 is not strategy2
