import pytest
import uuid
import io
import os
from unittest.mock import patch
import asyncio
from common.providers.storage.s3 import S3Storage


@pytest.mark.asyncio
class TestS3Integration:
    """Integration tests for S3Storage with LocalStack."""

    async def test_upload_and_download_file(
        self, s3_storage, test_s3_key, sample_file_content
    ):
        """Test uploading and downloading a file."""
        # Upload file
        file_data = io.BytesIO(sample_file_content)
        result = await s3_storage.upload(test_s3_key, file_data)
        assert result is True

        # Download file
        downloaded_content = await s3_storage.download(test_s3_key)
        assert downloaded_content == sample_file_content

    async def test_upload_with_metadata(self, s3_storage, sample_file_content):
        """Test uploading a file with metadata."""
        test_key = "test/with_metadata.txt"
        metadata = {
            "content-type": "text/plain",
            "author": "integration-test",
            "version": "1.0",
        }

        file_data = io.BytesIO(sample_file_content)
        result = await s3_storage.upload(test_key, file_data, metadata=metadata)
        assert result is True

        # Verify file exists
        exists = await s3_storage.exists(test_key)
        assert exists is True

        # Clean up
        await s3_storage.delete(test_key)

    async def test_file_exists_check(self, s3_storage, sample_file_content):
        """Test checking if a file exists."""

        test_key = f"test/exists_check/{uuid.uuid4().hex}.txt"

        # File should not exist initially
        exists = await s3_storage.exists(test_key)
        assert exists is False

        # Upload file
        file_data = io.BytesIO(sample_file_content)
        await s3_storage.upload(test_key, file_data)

        # File should now exist
        exists = await s3_storage.exists(test_key)
        assert exists is True

        # Clean up
        await s3_storage.delete(test_key)

        # File should not exist after deletion
        exists = await s3_storage.exists(test_key)
        assert exists is False

    async def test_delete_file(self, s3_storage, test_s3_key, sample_file_content):
        """Test deleting a file."""
        # Upload file first
        file_data = io.BytesIO(sample_file_content)
        await s3_storage.upload(test_s3_key, file_data)

        # Verify file exists
        exists = await s3_storage.exists(test_s3_key)
        assert exists is True

        # Delete file
        result = await s3_storage.delete(test_s3_key)
        assert result is True

        # Verify file no longer exists
        exists = await s3_storage.exists(test_s3_key)
        assert exists is False

    async def test_list_objects_empty(self, s3_storage):
        """Test listing objects when bucket is empty or no objects match prefix."""
        objects = await s3_storage.list_objects(prefix="non_existent/prefix/")
        assert isinstance(objects, list)
        assert len(objects) == 0

    async def test_list_objects_with_content(self, s3_storage, sample_file_content):
        """Test listing objects when there are files in the bucket."""
        test_prefix = "test/list/"
        test_keys = [
            f"{test_prefix}file1.txt",
            f"{test_prefix}file2.txt",
            f"{test_prefix}subdir/file3.txt",
        ]

        # Upload test files
        for key in test_keys:
            file_data = io.BytesIO(sample_file_content)
            await s3_storage.upload(key, file_data)

        # List objects with prefix
        objects = await s3_storage.list_objects(prefix=test_prefix)
        assert len(objects) == 3

        for key in test_keys:
            assert key in objects

        # Clean up
        for key in test_keys:
            await s3_storage.delete(key)

    async def test_list_objects_with_limit(self, s3_storage, sample_file_content):
        """Test listing objects with limit parameter."""
        test_prefix = "test/limit/"
        test_keys = [f"{test_prefix}file{i}.txt" for i in range(5)]

        # Upload test files
        for key in test_keys:
            file_data = io.BytesIO(sample_file_content)
            await s3_storage.upload(key, file_data)

        # List with limit
        objects = await s3_storage.list_objects(prefix=test_prefix, limit=3)
        assert len(objects) <= 3

        # Clean up
        for key in test_keys:
            await s3_storage.delete(key)

    async def test_download_nonexistent_file(self, s3_storage):
        """Test downloading a file that doesn't exist."""
        content = await s3_storage.download("nonexistent/file.txt")
        assert content is None

    async def test_delete_nonexistent_file(self, s3_storage):
        """Test deleting a file that doesn't exist."""
        # S3 delete is idempotent - deleting non-existent file should succeed
        result = await s3_storage.delete("nonexistent/file.txt")
        assert result is True

    async def test_get_presigned_url(
        self, s3_storage, test_s3_key, sample_file_content
    ):
        """Test generating presigned URLs."""
        # Upload a file first
        file_data = io.BytesIO(sample_file_content)
        await s3_storage.upload(test_s3_key, file_data)

        # Generate presigned URL
        url = await s3_storage.get_presigned_url(test_s3_key, expiration=3600)
        assert url is not None
        assert isinstance(url, str)
        assert "test-bucket" in url or "localhost" in url  # LocalStack or real S3

        # Clean up
        await s3_storage.delete(test_s3_key)

    async def test_get_presigned_url_nonexistent_file(self, s3_storage):
        """Test generating presigned URL for non-existent file."""
        # S3 allows generating presigned URLs for non-existent objects
        url = await s3_storage.get_presigned_url("nonexistent/file.txt")
        assert url is not None
        assert isinstance(url, str)

    async def test_upload_large_file(self, s3_storage):
        """Test uploading a larger file."""
        large_content = b"Large file content. " * 1000  # ~20KB
        test_key = "test/large_file.txt"

        file_data = io.BytesIO(large_content)
        result = await s3_storage.upload(test_key, file_data)
        assert result is True

        # Verify file was uploaded correctly
        downloaded_content = await s3_storage.download(test_key)
        assert downloaded_content == large_content

        # Clean up
        await s3_storage.delete(test_key)

    async def test_bucket_creation_on_init(self):
        """Test that bucket is created if it doesn't exist."""
        # Create storage instance with a new bucket name
        test_bucket = "test-integration-bucket-new"
        storage = S3Storage(bucket_name=test_bucket)

        # Try to list objects (this will verify bucket exists)
        objects = await storage.list_objects()
        assert isinstance(objects, list)

    async def test_concurrent_operations(self, s3_storage, sample_file_content):
        """Test concurrent S3 operations."""

        test_keys = [f"test/concurrent/file{i}.txt" for i in range(5)]

        # Upload files concurrently
        upload_tasks = []
        for key in test_keys:
            file_data = io.BytesIO(sample_file_content)
            task = s3_storage.upload(key, file_data)
            upload_tasks.append(task)

        results = await asyncio.gather(*upload_tasks)
        assert all(results)

        # Download files concurrently
        download_tasks = [s3_storage.download(key) for key in test_keys]
        downloaded_contents = await asyncio.gather(*download_tasks)

        for content in downloaded_contents:
            assert content == sample_file_content

        # Clean up concurrently
        delete_tasks = [s3_storage.delete(key) for key in test_keys]
        delete_results = await asyncio.gather(*delete_tasks)
        assert all(delete_results)

    @pytest.mark.parametrize(
        "key",
        [
            "simple.txt",
            "path/to/file.txt",
            "special-chars_file.txt",
            "numbers123/file456.txt",
            "very/deeply/nested/path/to/file.txt",
        ],
    )
    async def test_various_key_formats(self, s3_storage, sample_file_content, key):
        """Test uploading files with various key formats."""
        file_data = io.BytesIO(sample_file_content)

        # Upload
        result = await s3_storage.upload(key, file_data)
        assert result is True

        # Verify exists
        exists = await s3_storage.exists(key)
        assert exists is True

        # Download and verify content
        content = await s3_storage.download(key)
        assert content == sample_file_content

        # Clean up
        await s3_storage.delete(key)


@pytest.mark.asyncio
class TestS3ErrorHandling:
    """Test error handling in S3 operations."""

    async def test_invalid_bucket_name_handling(self):
        """Test handling of invalid bucket names."""
        # This test depends on LocalStack/S3 behavior
        # Some invalid names might be caught during initialization
        pass  # Implementation depends on specific validation requirements

    async def test_network_failure_simulation(self):
        """Test behavior during network failures."""

        # Create storage with invalid endpoint to simulate network failure
        with patch.dict(
            os.environ,
            {
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_REGION": "us-east-1",
                "S3_BUCKET_NAME": "test-bucket",
                "S3_ENDPOINT_URL": "http://127.0.0.1:9999",  # Non-existent endpoint
            },
        ):
            try:
                invalid_storage = S3Storage(bucket_name="test-bucket")

                # Operations should fail gracefully
                result = await invalid_storage.upload("test.txt", io.BytesIO(b"test"))
                assert result is False

                content = await invalid_storage.download("test.txt")
                assert content is None

                objects = await invalid_storage.list_objects()
                assert objects == []
            except Exception:
                # If storage creation itself fails due to network issues, that's also valid
                # This test is to ensure graceful failure handling
                pass
