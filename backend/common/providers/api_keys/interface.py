from abc import ABC, abstractmethod


class APIKeyRotationInterface(ABC):
    """Interface for API key rotation providers."""

    @abstractmethod
    def get_next_key(self) -> str:
        """
        Get the next API key in the rotation.

        Returns:
            The next available API key.
        """
        pass

    @abstractmethod
    def report_failure(self, key: str) -> None:
        """
        Report that an API key failed.

        Args:
            key: The API key that failed.
        """
        pass

    @abstractmethod
    def report_success(self, key: str) -> None:
        """
        Report that an API key succeeded.

        Args:
            key: The API key that succeeded.
        """
        pass

    @abstractmethod
    def get_healthy_key_count(self) -> int:
        """
        Get the number of currently healthy keys.

        Returns:
            Number of healthy keys available.
        """
        pass
