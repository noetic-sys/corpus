"""
Factory for creating cell creation strategies based on matrix type.
"""

from typing import Type, Dict
from packages.matrices.models.domain.matrix_enums import MatrixType
from .base_strategy import BaseCellCreationStrategy
from .standard_matrix_strategy import StandardMatrixStrategy
from .cross_correlation_strategy import CrossCorrelationStrategy
from .generic_correlation_strategy import GenericCorrelationStrategy


class CellStrategyFactory:
    """Factory for creating cell creation strategies based on matrix type."""

    _strategies: Dict[MatrixType, Type[BaseCellCreationStrategy]] = {
        MatrixType.STANDARD: StandardMatrixStrategy,
        MatrixType.CROSS_CORRELATION: CrossCorrelationStrategy,
        MatrixType.GENERIC_CORRELATION: GenericCorrelationStrategy,
    }

    @classmethod
    def get_strategy(cls, matrix_type: MatrixType) -> BaseCellCreationStrategy:
        """Get strategy instance for matrix type.

        Args:
            matrix_type: The type of matrix

        Returns:
            Strategy instance for the given matrix type

        Raises:
            ValueError: If no strategy exists for the matrix type
        """
        strategy_class = cls._strategies.get(matrix_type)
        if not strategy_class:
            raise ValueError(f"No strategy found for matrix type: {matrix_type}")
        return strategy_class()

    @classmethod
    def register_strategy(
        cls, matrix_type: MatrixType, strategy_class: Type[BaseCellCreationStrategy]
    ) -> None:
        """Register a new strategy for a matrix type.

        Allows extending the factory with custom strategies.

        Args:
            matrix_type: The matrix type to register for
            strategy_class: The strategy class to use
        """
        cls._strategies[matrix_type] = strategy_class
