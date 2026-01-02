from typing import Optional, List, BinaryIO
from datetime import timedelta
from google.cloud import storage
from google.api_core.exceptions import NotFound
import google.auth

from common.core.config import settings
from .interface import StorageInterface
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class GCSStorage(StorageInterface):
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.s3_bucket_name

        # Initialize GCS client with Workload Identity
        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)

        # Get service account email for IAM signing (Workload Identity compatible)
        credentials, _ = google.auth.default()
        self.service_account_email = credentials.service_account_email

        logger.info(
            f"Initialized GCS storage with bucket: {self.bucket_name}, "
            f"service account: {self.service_account_email}"
        )

    @trace_span
    async def upload(
        self, key: str, data: BinaryIO, metadata: Optional[dict] = None
    ) -> bool:
        try:
            blob = self.bucket.blob(key)

            # Set metadata if provided
            if metadata:
                blob.metadata = metadata

            # Upload the data
            blob.upload_from_file(data, rewind=True)

            logger.info(f"Successfully uploaded {key} to {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload {key}: {e}")
            return False

    @trace_span
    async def download(self, key: str) -> Optional[bytes]:
        try:
            blob = self.bucket.blob(key)
            return blob.download_as_bytes()
        except NotFound:
            logger.warning(f"Object {key} not found")
            return None
        except Exception as e:
            logger.error(f"Failed to download {key}: {e}")
            return None

    @trace_span
    async def delete(self, key: str) -> bool:
        try:
            blob = self.bucket.blob(key)
            blob.delete()
            logger.info(f"Successfully deleted {key}")
            return True
        except NotFound:
            logger.warning(f"Object {key} not found for deletion")
            return True  # Consider it success if already deleted
        except Exception as e:
            logger.error(f"Failed to delete {key}: {e}")
            return False

    @trace_span
    async def exists(self, key: str) -> bool:
        try:
            blob = self.bucket.blob(key)
            return blob.exists()
        except Exception as e:
            logger.error(f"Failed to check if {key} exists: {e}")
            return False

    @trace_span
    async def list_objects(self, prefix: str = "", limit: int = 1000) -> List[str]:
        try:
            blobs = self.client.list_blobs(
                self.bucket_name, prefix=prefix, max_results=limit
            )
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            return []

    @trace_span
    async def get_presigned_url(
        self, key: str, expiration: int = 3600
    ) -> Optional[str]:
        try:
            blob = self.bucket.blob(key)
            # Use IAM signing (Workload Identity compatible - no private key needed)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration),
                service_account_email=self.service_account_email,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    @trace_span
    async def generate_presigned_upload_url(
        self, key: str, expiration: int = 3600
    ) -> Optional[str]:
        try:
            blob = self.bucket.blob(key)
            # Use IAM signing (Workload Identity compatible - no private key needed)
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiration),
                method="PUT",
                service_account_email=self.service_account_email,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned upload URL: {e}")
            return None

    async def get_storage_uri(self, key: str) -> str:
        """Get the GCS URI for a given key."""
        return f"gs://{self.bucket.name}/{key}"

    @trace_span
    async def delete_prefix(self, prefix: str) -> int:
        """
        Delete all objects with a given prefix.

        Args:
            prefix: The prefix to delete

        Returns:
            Number of objects deleted
        """
        try:
            # List all blobs with prefix
            blobs = list(self.client.list_blobs(self.bucket_name, prefix=prefix))

            if not blobs:
                logger.info(f"No objects found with prefix {prefix}")
                return 0

            # Delete all blobs
            deleted_count = 0
            for blob in blobs:
                try:
                    blob.delete()
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to delete {blob.name}: {e}")

            logger.info(f"Deleted {deleted_count} objects with prefix {prefix}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete prefix {prefix}: {e}")
            return 0
