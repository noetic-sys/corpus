from abc import ABC, abstractmethod
from typing import Optional, List, BinaryIO


class StorageInterface(ABC):
    @abstractmethod
    async def upload(
        self, key: str, data: BinaryIO, metadata: Optional[dict] = None
    ) -> bool:
        pass

    @abstractmethod
    async def download(self, key: str) -> Optional[bytes]:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        pass

    @abstractmethod
    async def list_objects(self, prefix: str = "", limit: int = 1000) -> List[str]:
        pass

    @abstractmethod
    async def get_presigned_url(
        self, key: str, expiration: int = 3600
    ) -> Optional[str]:
        pass

    @abstractmethod
    async def generate_presigned_upload_url(
        self, key: str, expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate presigned URL for uploading to a specific key.

        Args:
            key: The storage key to upload to
            expiration: Expiration time in seconds

        Returns:
            Presigned URL for PUT operation
        """
        pass

    @abstractmethod
    async def get_storage_uri(self, key: str) -> str:
        """
        Get the storage URI for a given key in the provider's native format.

        Args:
            key: The storage key

        Returns:
            The storage URI (e.g., 'gs://bucket/key' for GCS, 's3://bucket/key' for S3)
        """
        pass

    @abstractmethod
    async def delete_prefix(self, prefix: str) -> int:
        """
        Delete all objects with a given prefix.

        Args:
            prefix: The prefix to delete

        Returns:
            Number of objects deleted
        """
        pass
