import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_storage():
    """Create a mock storage instance for testing."""
    storage = AsyncMock()
    storage.upload = AsyncMock(return_value=True)
    storage.download = AsyncMock(return_value=b"mock file content")
    storage.delete = AsyncMock(return_value=True)
    storage.exists = AsyncMock(return_value=True)
    storage.list_objects = AsyncMock(return_value=[])
    storage.get_presigned_url = AsyncMock(return_value="https://mock-presigned-url.com")
    storage.get_storage_uri = MagicMock(return_value="s3://mock-bucket/mock-key")
    return storage


@pytest.fixture(autouse=True)
def mock_get_storage(mock_storage):
    """Automatically mock get_storage for all unit tests."""
    with patch(
        "packages.documents.services.document_service.get_storage",
        return_value=mock_storage,
    ):
        yield


@pytest.fixture
def mock_message_queue():
    """Create a mock message queue instance for testing."""
    queue = AsyncMock()
    queue.declare_queue = AsyncMock(return_value=True)
    queue.publish = AsyncMock(return_value=True)
    queue.consume = AsyncMock()
    queue.connect = AsyncMock(return_value=None)
    queue.disconnect = AsyncMock(return_value=None)
    return queue


@pytest.fixture
def mock_span():
    """Create a mock span instance for testing telemetry."""
    span = MagicMock()
    span.__enter__ = MagicMock(return_value=span)
    span.__exit__ = MagicMock(return_value=None)
    span.__aenter__ = AsyncMock(return_value=span)
    span.__aexit__ = AsyncMock(return_value=None)
    return span


@pytest.fixture
def mock_start_span(mock_span):
    """Create a mock start_span function that returns mock_span."""
    with patch(
        "common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span",
        return_value=mock_span,
    ) as mock:
        yield mock
