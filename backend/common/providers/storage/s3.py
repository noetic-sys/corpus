from typing import Optional, List, BinaryIO
import boto3
from botocore.exceptions import ClientError

from common.core.config import settings
from .interface import StorageInterface
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class S3Storage(StorageInterface):
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.s3_bucket_name

        client_config = {
            "service_name": "s3",
            "aws_access_key_id": settings.aws_access_key_id,
            "aws_secret_access_key": settings.aws_secret_access_key,
            "region_name": settings.aws_region,
        }

        if settings.s3_endpoint_url:
            client_config["endpoint_url"] = settings.s3_endpoint_url
            client_config["config"] = boto3.session.Config(
                s3={"addressing_style": "path"}
            )

        self.client = boto3.client(**client_config)
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self):
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                try:
                    if settings.s3_endpoint_url:
                        self.client.create_bucket(Bucket=self.bucket_name)
                    else:
                        if settings.aws_region != "us-east-1":
                            self.client.create_bucket(
                                Bucket=self.bucket_name,
                                CreateBucketConfiguration={
                                    "LocationConstraint": settings.aws_region
                                },
                            )
                        else:
                            self.client.create_bucket(Bucket=self.bucket_name)
                    logger.info(f"Created bucket: {self.bucket_name}")
                except Exception as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")

    @trace_span
    async def upload(
        self, key: str, data: BinaryIO, metadata: Optional[dict] = None
    ) -> bool:
        try:
            extra_args = {}
            if metadata:
                extra_args["Metadata"] = metadata

            self.client.upload_fileobj(
                data, self.bucket_name, key, ExtraArgs=extra_args
            )
            logger.info(f"Successfully uploaded {key} to {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload {key}: {e}")
            return False

    @trace_span
    async def download(self, key: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"Object {key} not found")
            else:
                logger.error(f"Failed to download {key}: {e}")
            return None

    @trace_span
    async def delete(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Successfully deleted {key}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {key}: {e}")
            return False

    @trace_span
    async def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False

    @trace_span
    async def list_objects(self, prefix: str = "", limit: int = 1000) -> List[str]:
        try:
            paginator = self.client.get_paginator("list_objects_v2")
            pages = paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=prefix,
                PaginationConfig={"MaxItems": limit},
            )

            keys = []
            for page in pages:
                if "Contents" in page:
                    keys.extend([obj["Key"] for obj in page["Contents"]])

            return keys
        except Exception as e:
            logger.error(f"Failed to list objects: {e}")
            return []

    @trace_span
    async def get_presigned_url(
        self, key: str, expiration: int = 3600
    ) -> Optional[str]:
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
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
            url = self.client.generate_presigned_url(
                "put_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
            )
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned upload URL: {e}")
            return None

    async def get_storage_uri(self, key: str) -> str:
        """Get the S3 URI for a given key."""
        return f"s3://{self.bucket_name}/{key}"

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
            # List all objects with prefix
            objects_to_delete = await self.list_objects(prefix=prefix)

            if not objects_to_delete:
                logger.info(f"No objects found with prefix {prefix}")
                return 0

            # Delete in batches of 1000 (S3 limit)
            deleted_count = 0
            for i in range(0, len(objects_to_delete), 1000):
                batch = objects_to_delete[i : i + 1000]
                delete_dict = {"Objects": [{"Key": key} for key in batch]}

                response = self.client.delete_objects(
                    Bucket=self.bucket_name, Delete=delete_dict
                )

                deleted_count += len(response.get("Deleted", []))

            logger.info(f"Deleted {deleted_count} objects with prefix {prefix}")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete prefix {prefix}: {e}")
            return 0
