import uuid
import pytest
import asyncio
import os
from unittest.mock import patch

from common.providers.messaging.rabbitmq_async import RabbitMQClient
from common.providers.storage.s3 import S3Storage
from common.providers.ai.openai_provider import OpenAIProvider
from packages.documents.providers.document_extraction.text_extractor import (
    TextExtractor,
)
from common.core.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def rabbitmq_client():
    """
    Provide a RabbitMQ client for integration tests.
    Requires RabbitMQ to be running (e.g., via docker-compose).
    """
    # Override settings for test environment
    with patch.dict(
        os.environ,
        {
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_PORT": "5672",
            "RABBITMQ_USERNAME": "guest",
            "RABBITMQ_PASSWORD": "guest",
            "RABBITMQ_VHOST": "/",
        },
    ):
        client = RabbitMQClient()

        # Try to connect - skip test if RabbitMQ is not available
        try:
            connected = await client.connect()
            if not connected:
                pytest.skip("RabbitMQ is not available for integration tests")
        except Exception as e:
            pytest.skip(f"RabbitMQ is not available: {e}")

        yield client

        # Cleanup
        try:
            await client.disconnect()
        except Exception:
            pass


@pytest.fixture
async def s3_storage():
    """
    Provide an S3Storage client for integration tests.
    Uses LocalStack for testing (requires LocalStack to be running).
    """
    # Override settings for test environment with LocalStack
    with patch.dict(
        os.environ,
        {
            "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
            "AWS_REGION": "us-east-1",
            "S3_BUCKET_NAME": "test-bucket",
            "S3_ENDPOINT_URL": "http://localhost:4566",  # LocalStack endpoint
        },
    ):
        storage = S3Storage(bucket_name="test-bucket")

        # Try basic operation to check if LocalStack is available
        try:
            await storage.list_objects()
        except Exception as e:
            pytest.skip(f"LocalStack S3 is not available: {e}")

        yield storage


@pytest.fixture
def test_queue_name():
    """Provide a unique test queue name."""

    return f"test_queue_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_exchange_name():
    """Provide a unique test exchange name."""

    return f"test_exchange_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def test_s3_key():
    """Provide a test S3 object key."""
    return "test/integration/test_file.txt"


@pytest.fixture
def sample_message():
    """Provide a sample message for testing."""
    return {
        "message_id": "test-123",
        "data": "integration test message",
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_file_content():
    """Provide sample file content for storage tests."""
    return b"This is test file content for integration tests"


@pytest.fixture
def openai_provider():
    """
    Provide an OpenAI provider for integration tests.
    Uses API key from settings (loaded from .env file).
    """
    try:
        # Try to access the API key from settings (use first key from rotation)
        api_key = settings.openai_api_keys[0] if settings.openai_api_keys else None
        if not api_key:
            pytest.skip("OpenAI API key not configured in settings")
    except Exception:
        pytest.skip("OpenAI API key not configured in settings")

    return OpenAIProvider(api_key=api_key)


@pytest.fixture
def text_extractor():
    """Provide a TextExtractor for integration tests."""
    return TextExtractor()


@pytest.fixture
def sample_document_content():
    """Provide sample document content for AI provider tests."""
    return """
    Python Programming Language
    
    Python is a high-level, interpreted programming language with dynamic semantics. 
    Its high-level built in data structures, combined with dynamic typing and dynamic binding, 
    make it very attractive for Rapid Application Development, as well as for use as a 
    scripting or glue language to connect existing components together.
    
    Python's simple, easy to learn syntax emphasizes readability and therefore reduces 
    the cost of program maintenance. Python supports modules and packages, which encourages 
    program modularity and code reuse.
    
    Key Features:
    - Easy to learn and use
    - Interpreted language
    - Cross-platform compatibility
    - Extensive standard library
    - Large community support
    """
