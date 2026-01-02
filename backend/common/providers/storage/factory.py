from common.core.config import settings
from common.core.constants import StorageProvider
from .interface import StorageInterface
from .gcs import GCSStorage
from .s3 import S3Storage


def get_storage() -> StorageInterface:
    """Get storage instance based on environment profile."""
    if settings.storage_provider == StorageProvider.GCS:
        return GCSStorage()
    elif settings.storage_provider == StorageProvider.S3:
        return S3Storage()
    else:
        raise ValueError(f"Unknown storage provider: {settings.storage_provider}")
