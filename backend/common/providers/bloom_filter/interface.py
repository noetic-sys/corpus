from abc import ABC, abstractmethod


class BloomFilterInterface(ABC):
    """Interface for bloom filter providers."""

    @abstractmethod
    async def add(self, filter_name: str, value: str) -> bool:
        """
        Add a value to the bloom filter.

        Args:
            filter_name: The name of the bloom filter
            value: The value to add

        Returns:
            True if added successfully, False otherwise
        """
        pass

    @abstractmethod
    async def exists(self, filter_name: str, value: str) -> bool:
        """
        Check if a value might exist in the bloom filter.

        Args:
            filter_name: The name of the bloom filter
            value: The value to check

        Returns:
            True if the value might exist (false positives possible),
            False if the value definitely does not exist
        """
        pass

    @abstractmethod
    async def clear(self, filter_name: str) -> bool:
        """
        Clear all values from the bloom filter.

        Args:
            filter_name: The name of the bloom filter

        Returns:
            True if cleared successfully, False otherwise
        """
        pass

    @abstractmethod
    async def info(self, filter_name: str) -> dict:
        """
        Get information about the bloom filter.

        Args:
            filter_name: The name of the bloom filter

        Returns:
            Dictionary with filter information (size, capacity, error rate, etc.)
        """
        pass
