import pytest
import io
import uuid
from unittest.mock import patch
import os

from common.providers.messaging.factory import get_message_queue
from common.providers.messaging.interface import MessageQueueInterface
from common.providers.messaging.rabbitmq_async import RabbitMQClient
from common.providers.storage.factory import get_storage
from common.providers.storage.interface import StorageInterface
from common.providers.storage.s3 import S3Storage


class TestFactoryFunctions:
    """Test provider factory functions."""

    def test_get_message_queue_returns_interface(self):
        """Test that get_message_queue returns MessageQueueInterface implementation."""
        client = get_message_queue()
        assert isinstance(client, MessageQueueInterface)
        assert isinstance(client, RabbitMQClient)

    def test_get_message_queue_returns_new_instance(self):
        """Test that get_message_queue returns a new instance each time."""
        client1 = get_message_queue()
        client2 = get_message_queue()
        assert client1 is not client2

    def test_get_storage_returns_interface(self):
        """Test that get_storage returns StorageInterface implementation."""
        with patch.dict(
            os.environ,
            {
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_REGION": "us-east-1",
                "S3_BUCKET_NAME": "test-bucket",
            },
        ):
            storage = get_storage()
            assert isinstance(storage, StorageInterface)
            assert isinstance(storage, S3Storage)

    def test_get_storage_returns_new_instance(self):
        """Test that get_storage returns a new instance each time."""
        with patch.dict(
            os.environ,
            {
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_REGION": "us-east-1",
                "S3_BUCKET_NAME": "test-bucket",
            },
        ):
            storage1 = get_storage()
            storage2 = get_storage()
            assert storage1 is not storage2


@pytest.mark.asyncio
class TestFactoryIntegration:
    """Integration tests for factory-created instances."""

    async def test_factory_message_queue_basic_operations(self):
        """Test basic operations on factory-created message queue."""
        # Skip if RabbitMQ not available
        client = get_message_queue()
        try:
            connected = await client.connect()
            if not connected:
                pytest.skip("RabbitMQ not available for factory integration test")
        except Exception as e:
            pytest.skip(f"RabbitMQ not available: {e}")

        # Test basic operations with unique queue name

        test_queue = f"factory_test_queue_{uuid.uuid4().hex[:8]}"
        queue_declared = await client.declare_queue(test_queue, durable=True)
        assert queue_declared is True

        # Test message publishing
        message = {"test": "factory_integration", "timestamp": "2024-01-01"}
        published = await client.publish(test_queue, message)
        assert published is True

        await client.disconnect()

    async def test_factory_storage_basic_operations(self):
        """Test basic operations on factory-created storage."""

        # Use test configuration
        with patch.dict(
            os.environ,
            {
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
                "AWS_REGION": "us-east-1",
                "S3_BUCKET_NAME": "factory-test-bucket",
                "S3_ENDPOINT_URL": "http://localhost:4566",
            },
        ):
            storage = get_storage()

            # Skip if LocalStack not available
            try:
                await storage.list_objects()
            except Exception as e:
                pytest.skip(f"LocalStack not available: {e}")

            # Test basic operations
            test_key = "factory/test/file.txt"
            test_content = b"Factory integration test content"

            # Upload
            file_data = io.BytesIO(test_content)
            uploaded = await storage.upload(test_key, file_data)
            assert uploaded is True

            # Check exists
            exists = await storage.exists(test_key)
            assert exists is True

            # Download
            downloaded = await storage.download(test_key)
            assert downloaded == test_content

            # Clean up
            deleted = await storage.delete(test_key)
            assert deleted is True
