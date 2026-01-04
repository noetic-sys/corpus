import pytest
from common.providers.audio_transcription.constants import AudioFormat
import io
from packages.documents.providers.document_extraction.audio_extractor import (
    AudioExtractor,
)
from unittest.mock import AsyncMock, MagicMock, patch
from packages.documents.models.domain.document import DocumentModel
from datetime import datetime

from packages.documents.workflows.activities import (
    extract_document_content_activity,
    save_extracted_content_to_s3_activity,
    index_document_for_search_activity,
)
from packages.documents.repositories.document_repository import DocumentRepository
from packages.documents.models.database.document import ExtractionStatus
from packages.documents.models.domain.document import DocumentCreateModel


@pytest.fixture
def mock_session_context():
    """Fixture that creates a MockSessionContext class for AsyncSessionLocal mocking."""

    class MockSessionContext:
        def __init__(self, test_db):
            self.test_db = test_db

        async def __aenter__(self):
            return self.test_db

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    return MockSessionContext


@patch(
    "packages.documents.workflows.activities.document_extraction.create_span_with_context"
)
@patch(
    "packages.documents.workflows.activities.document_extraction.ExtractorFactory.get_extractor"
)
@patch("packages.documents.services.document_service.get_storage")
@patch("packages.documents.services.document_service.get_bloom_filter_provider")
@patch("packages.documents.services.document_service.get_document_search_provider")
class TestExtractDocumentContentActivity:
    """Unit tests for extract_document_content_activity."""

    @pytest.mark.asyncio
    async def test_extract_document_content_success(
        self,
        mock_get_document_search_provider,
        mock_get_bloom_filter_provider,
        mock_get_storage,
        mock_get_extractor,
        mock_create_span,
        test_db,
        sample_company,
    ):
        """Test successful document content extraction."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Create a test document in the database

        doc_repo = DocumentRepository()
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="documents/test.pdf",
            content_type="application/pdf",
            checksum="test_checksum",
            extraction_status=ExtractionStatus.PENDING,
            company_id=sample_company.id,
        )
        document = await doc_repo.create(document_create)

        # Mock storage provider
        mock_storage = AsyncMock()
        mock_get_storage.return_value = mock_storage

        # Mock extractor
        mock_extractor = AsyncMock()
        mock_extractor.extract_text.return_value = "Extracted text content"
        mock_get_extractor.return_value = mock_extractor

        # Call the activity with document_id
        result = await extract_document_content_activity(
            document.id, {"trace-id": "12345"}
        )

        # Assertions
        assert result == "Extracted text content"
        mock_get_extractor.assert_called_once_with("pdf")
        mock_extractor.extract_text.assert_called_once()

        # Check that the extractor was called with a DocumentModel
        call_args = mock_extractor.extract_text.call_args
        document_arg = call_args[0][0]
        assert document_arg.id == document.id
        assert document_arg.filename == "test.pdf"

        mock_create_span.assert_called_once_with(
            "temporal::extract_document_content_activity", {"trace-id": "12345"}
        )

    @pytest.mark.asyncio
    async def test_extract_document_content_not_found(
        self,
        mock_get_document_search_provider,
        mock_get_bloom_filter_provider,
        mock_get_storage,
        mock_get_extractor,
        mock_create_span,
        test_db,
    ):
        """Test when document is not found in database."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock storage and extractor (shouldn't be called)
        mock_storage = AsyncMock()
        mock_get_storage.return_value = mock_storage
        mock_extractor = AsyncMock()
        mock_get_extractor.return_value = mock_extractor

        # Call the activity with non-existent document ID and expect ValueError
        with pytest.raises(ValueError, match="Document 99999 not found in database"):
            await extract_document_content_activity(99999)

        # Assertions
        mock_get_extractor.assert_not_called()  # Should not be called when document not found
        mock_extractor.extract_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_document_content_extraction_failure(
        self,
        mock_get_document_search_provider,
        mock_get_bloom_filter_provider,
        mock_get_storage,
        mock_get_extractor,
        mock_create_span,
        test_db,
        sample_company,
    ):
        """Test when document extraction fails."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Create a test document in the database

        doc_repo = DocumentRepository()
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="documents/test.pdf",
            content_type="application/pdf",
            checksum="test_checksum",
            extraction_status=ExtractionStatus.PENDING,
            company_id=sample_company.id,
        )
        document = await doc_repo.create(document_create)

        # Mock storage provider
        mock_storage = AsyncMock()
        mock_get_storage.return_value = mock_storage

        # Mock extractor to raise exception
        mock_extractor = AsyncMock()
        mock_extractor.extract_text.side_effect = Exception("Extraction failed")
        mock_get_extractor.return_value = mock_extractor

        # Call the activity and expect exception to propagate
        with pytest.raises(Exception, match="Extraction failed"):
            await extract_document_content_activity(document.id)

        # Assertions
        mock_get_extractor.assert_called_once_with("pdf")
        mock_extractor.extract_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_document_content_no_trace_headers(
        self,
        mock_get_document_search_provider,
        mock_get_bloom_filter_provider,
        mock_get_storage,
        mock_get_extractor,
        mock_create_span,
        test_db,
        sample_company,
    ):
        """Test extraction without trace headers."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Create a test document in the database

        doc_repo = DocumentRepository()
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="documents/test.pdf",
            content_type="application/pdf",
            checksum="test_checksum",
            extraction_status=ExtractionStatus.PENDING,
            company_id=sample_company.id,
        )
        document = await doc_repo.create(document_create)

        # Mock storage provider
        mock_storage = AsyncMock()
        mock_get_storage.return_value = mock_storage

        # Mock extractor
        mock_extractor = AsyncMock()
        mock_extractor.extract_text.return_value = "Extracted text content"
        mock_get_extractor.return_value = mock_extractor

        # Call the activity without trace headers
        result = await extract_document_content_activity(document.id)

        # Assertions
        assert result == "Extracted text content"
        mock_create_span.assert_called_once_with(
            "temporal::extract_document_content_activity", None
        )


@patch(
    "packages.documents.workflows.activities.document_extraction.create_span_with_context"
)
@patch("packages.documents.workflows.activities.document_extraction.get_storage")
class TestSaveExtractedContentToS3Activity:
    """Unit tests for save_extracted_content_to_s3_activity."""

    @pytest.mark.asyncio
    async def test_save_extracted_content_success(
        self,
        mock_get_storage,
        mock_create_span,
        test_db,
        sample_document,
        sample_company,
    ):
        """Test successful saving of extracted content to S3."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock storage provider
        mock_storage = AsyncMock()
        mock_storage.upload.return_value = True
        mock_get_storage.return_value = mock_storage

        # Call the activity
        result = await save_extracted_content_to_s3_activity(
            "This is extracted content", sample_document.id, {"trace-id": "12345"}
        )

        # Assertions - path now includes company_id
        expected_s3_key = (
            f"company/{sample_company.id}/documents/{sample_document.id}/extracted.md"
        )
        assert result == expected_s3_key

        # Verify upload was called with correct parameters
        mock_storage.upload.assert_called_once()
        call_args = mock_storage.upload.call_args
        assert call_args[0][0] == expected_s3_key  # s3_key
        assert isinstance(call_args[0][1], io.BytesIO)  # content stream
        assert call_args[1]["metadata"]["content_type"] == "text/markdown"

        mock_create_span.assert_called_once_with(
            "temporal::save_extracted_content_to_s3_activity", {"trace-id": "12345"}
        )

    @pytest.mark.asyncio
    async def test_save_extracted_content_upload_failure(
        self, mock_get_storage, mock_create_span, test_db, sample_document
    ):
        """Test when S3 upload fails."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock storage provider to return False (upload failure)
        mock_storage = AsyncMock()
        mock_storage.upload.return_value = False
        mock_get_storage.return_value = mock_storage

        # Call the activity and expect exception
        with pytest.raises(Exception, match="Failed to upload extracted content to S3"):
            await save_extracted_content_to_s3_activity(
                "This is extracted content", sample_document.id
            )

        # Assertions
        mock_storage.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_extracted_content_storage_exception(
        self, mock_get_storage, mock_create_span, test_db, sample_document
    ):
        """Test when storage upload raises an exception."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock storage provider to raise exception
        mock_storage = AsyncMock()
        mock_storage.upload.side_effect = Exception("S3 connection failed")
        mock_get_storage.return_value = mock_storage

        # Call the activity and expect exception to propagate
        with pytest.raises(Exception, match="S3 connection failed"):
            await save_extracted_content_to_s3_activity(
                "This is extracted content", sample_document.id
            )

        # Assertions
        mock_storage.upload.assert_called_once()


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
@patch(
    "packages.documents.workflows.activities.document_extraction.get_document_search_provider"
)
class TestIndexDocumentForSearchActivity:
    """Unit tests for index_document_for_search_activity."""

    @pytest.mark.asyncio
    async def test_index_document_success(
        self,
        mock_get_search_provider,
        mock_start_span,
        test_db,
        mock_session_context,
        sample_company,
    ):
        """Test successful document indexing."""
        # patch_lazy_sessions fixture in conftest handles test database routing
        # Create a real document in the database

        doc_repo = DocumentRepository()
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="documents/test.pdf",
            checksum="test_checksum",
            extraction_status=ExtractionStatus.COMPLETED,
            company_id=sample_company.id,
        )
        document = await doc_repo.create(document_create)

        # Mock search provider - not a context manager, direct call
        mock_search_provider = AsyncMock()
        mock_search_provider.index_document.return_value = True
        mock_get_search_provider.return_value = mock_search_provider

        # Call the activity
        result = await index_document_for_search_activity(
            document.id, "Extracted content for testing", {"trace-id": "12345"}
        )

        # Assertions
        assert result is True
        mock_search_provider.index_document.assert_called_once()

        # Verify the document model was passed correctly
        call_args = mock_search_provider.index_document.call_args
        assert call_args[0][1] == "Extracted content for testing"  # extracted_content

        # Verify document data
        indexed_doc = call_args[0][0]
        assert indexed_doc.filename == "test.pdf"
        assert indexed_doc.id == document.id

    @pytest.mark.asyncio
    async def test_index_document_not_found(
        self,
        mock_get_search_provider,
        mock_start_span,
        test_db,
        mock_session_context,
    ):
        """Test when document is not found in database."""
        # patch_lazy_sessions fixture in conftest handles test database routing

        # Mock search provider (shouldn't be called)
        mock_search_provider = AsyncMock()
        mock_get_search_provider.return_value = mock_search_provider

        # Call the activity with non-existent document ID
        result = await index_document_for_search_activity(99999, "Extracted content")

        # Assertions
        assert result is False
        mock_search_provider.index_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_index_document_indexing_failure(
        self,
        mock_get_search_provider,
        mock_start_span,
        test_db,
        mock_session_context,
        sample_company,
    ):
        """Test when search provider fails to index."""
        # patch_lazy_sessions fixture in conftest handles test database routing
        # Create a real document in the database

        doc_repo = DocumentRepository()
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="documents/test.pdf",
            checksum="test_checksum",
            extraction_status=ExtractionStatus.COMPLETED,
            company_id=sample_company.id,
        )
        document = await doc_repo.create(document_create)

        # Mock search provider to return False
        mock_search_provider = AsyncMock()
        mock_search_provider.index_document.return_value = False
        mock_get_search_provider.return_value = mock_search_provider

        # Call the activity
        result = await index_document_for_search_activity(
            document.id, "Extracted content"
        )

        # Assertions
        assert result is False
        mock_search_provider.index_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_index_document_exception_handling(
        self,
        mock_get_search_provider,
        mock_start_span,
        test_db,
        mock_session_context,
        sample_company,
    ):
        """Test exception handling during indexing."""
        # patch_lazy_sessions fixture in conftest handles test database routing
        # Create a real document in the database

        doc_repo = DocumentRepository()
        document_create = DocumentCreateModel(
            filename="test.pdf",
            storage_key="documents/test.pdf",
            checksum="test_checksum",
            extraction_status=ExtractionStatus.COMPLETED,
            company_id=sample_company.id,
        )
        document = await doc_repo.create(document_create)

        # Mock search provider to raise exception
        mock_search_provider = AsyncMock()
        mock_search_provider.index_document.side_effect = Exception(
            "Search provider error"
        )
        mock_get_search_provider.return_value = mock_search_provider

        # Call the activity - should not raise, but return False
        result = await index_document_for_search_activity(
            document.id, "Extracted content"
        )

        # Assertions
        assert result is False
        mock_search_provider.index_document.assert_called_once()


@patch("common.core.otel_axiom_exporter.axiom_tracer.start_as_current_span")
@patch("packages.documents.providers.document_extraction.audio_extractor.MutagenFile")
class TestAudioExtractionFallback:
    """Tests for audio extraction fallback logic."""

    @pytest.fixture
    def mock_audio_extractor(self):
        """Create a mock AudioExtractor with mocked providers."""
        # Mock the providers before creating AudioExtractor
        with patch(
            "packages.documents.providers.document_extraction.audio_extractor.GoogleSpeechToTextProvider"
        ) as mock_google, patch(
            "packages.documents.providers.document_extraction.audio_extractor.OpenAIWhisperProvider"
        ) as mock_whisper, patch(
            "packages.documents.providers.document_extraction.audio_extractor.get_storage"
        ) as mock_storage:

            # Set up mock instances
            mock_google_instance = AsyncMock()
            mock_whisper_instance = AsyncMock()
            mock_storage_instance = AsyncMock()

            mock_google.return_value = mock_google_instance
            mock_whisper.return_value = mock_whisper_instance
            mock_storage.return_value = mock_storage_instance

            extractor = AudioExtractor()
            # Return the extractor with already mocked providers
            return extractor

    @pytest.fixture
    def sample_audio_document(self, sample_company):
        """Create a sample audio document."""

        return DocumentModel(
            id=1,
            company_id=sample_company.id,
            filename="test_audio.mp3",
            storage_key="audio/test_audio.mp3",
            content_type="audio/mp3",
            checksum="audio_checksum",
            file_size=1024000,  # 1MB
            extraction_status=ExtractionStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    @pytest.mark.asyncio
    async def test_short_audio_gcs_success(
        self, mock_mutagen, mock_start_span, mock_audio_extractor, sample_audio_document
    ):
        """Test successful transcription of short audio file using GCS short method."""
        # Mock audio duration as 30 seconds (short)
        mock_file = MagicMock()
        mock_file.info.length = 30.0
        mock_mutagen.return_value = mock_file

        # Mock GCS storage URI (non-async method)
        mock_audio_extractor.storage.get_storage_uri.return_value = (
            "gs://bucket/audio/test_audio.mp3"
        )
        mock_audio_extractor.storage.download.return_value = b"fake_audio_data"

        # Mock Google provider supports format and succeeds on short method
        mock_audio_extractor.google_provider.supports_format = MagicMock(
            return_value=True
        )
        mock_audio_extractor.google_provider.transcribe_audio_bytes = AsyncMock(
            return_value="Transcribed text from short method"
        )

        # Test
        result = await mock_audio_extractor._transcribe_with_fallback(
            sample_audio_document, AudioFormat.MP3
        )

        # Assertions
        assert result == "Transcribed text from short method"
        mock_audio_extractor.google_provider.transcribe_audio_bytes.assert_called_once()
        mock_audio_extractor.whisper_provider.transcribe_audio_bytes.assert_not_called()

    @pytest.mark.asyncio
    async def test_long_audio_gcs_success(
        self, mock_mutagen, mock_start_span, mock_audio_extractor, sample_audio_document
    ):
        """Test successful transcription of long audio file using GCS long method."""
        # Mock audio duration as 120 seconds (long)
        mock_file = MagicMock()
        mock_file.info.length = 120.0
        mock_mutagen.return_value = mock_file

        # Mock GCS storage URI
        mock_audio_extractor.storage.get_storage_uri.return_value = (
            "gs://bucket/audio/test_audio.mp3"
        )
        mock_audio_extractor.storage.download.return_value = b"fake_audio_data"

        # Mock Google provider supports format and succeeds on long method
        mock_audio_extractor.google_provider.supports_format.return_value = True
        mock_audio_extractor.google_provider.transcribe_audio_uri.return_value = (
            "Transcribed text from long method"
        )

        # Test
        result = await mock_audio_extractor._transcribe_with_fallback(
            sample_audio_document, AudioFormat.MP3
        )

        # Assertions
        assert result == "Transcribed text from long method"
        mock_audio_extractor.google_provider.transcribe_audio_uri.assert_called_once_with(
            storage_uri="gs://bucket/audio/test_audio.mp3", audio_format=AudioFormat.MP3
        )
        mock_audio_extractor.whisper_provider.transcribe_audio_bytes.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_duration_defaults_to_long(
        self, mock_mutagen, mock_start_span, mock_audio_extractor, sample_audio_document
    ):
        """Test that unknown duration (-1) defaults to long_running_recognize."""
        # Mock mutagen fails to get duration
        mock_mutagen.return_value = None

        # Mock GCS storage URI
        mock_audio_extractor.storage.get_storage_uri.return_value = (
            "gs://bucket/audio/test_audio.mp3"
        )
        mock_audio_extractor.storage.download.return_value = b"fake_audio_data"

        # Mock Google provider supports format and succeeds on long method
        mock_audio_extractor.google_provider.supports_format.return_value = True
        mock_audio_extractor.google_provider.transcribe_audio_uri.return_value = (
            "Transcribed text from long method"
        )

        # Test
        result = await mock_audio_extractor._transcribe_with_fallback(
            sample_audio_document, AudioFormat.MP3
        )

        # Assertions
        assert result == "Transcribed text from long method"
        mock_audio_extractor.google_provider.transcribe_audio_uri.assert_called_once()
        mock_audio_extractor.whisper_provider.transcribe_audio_bytes.assert_not_called()

    @pytest.mark.asyncio
    async def test_short_audio_gcs_fallback_to_long_then_whisper(
        self, mock_mutagen, mock_start_span, mock_audio_extractor, sample_audio_document
    ):
        """Test fallback from short to long to Whisper when both Google methods fail."""
        # Mock audio duration as 30 seconds (short)
        mock_file = MagicMock()
        mock_file.info.length = 30.0
        mock_mutagen.return_value = mock_file

        # Mock GCS storage URI
        mock_audio_extractor.storage.get_storage_uri.return_value = (
            "gs://bucket/audio/test_audio.mp3"
        )
        mock_audio_extractor.storage.download.return_value = b"fake_audio_data"

        # Mock Google provider supports format but both methods fail
        mock_audio_extractor.google_provider.supports_format.return_value = True
        mock_audio_extractor.google_provider.transcribe_audio_bytes.side_effect = (
            Exception("Short method failed")
        )
        mock_audio_extractor.google_provider.transcribe_audio_uri.side_effect = (
            Exception("Long method failed")
        )

        # Mock Whisper succeeds
        mock_audio_extractor.whisper_provider.supports_format.return_value = True
        mock_audio_extractor.whisper_provider.transcribe_audio_bytes.return_value = (
            "Transcribed text from Whisper"
        )

        # Test
        result = await mock_audio_extractor._transcribe_with_fallback(
            sample_audio_document, AudioFormat.MP3
        )

        # Assertions
        assert result == "Transcribed text from Whisper"
        mock_audio_extractor.google_provider.transcribe_audio_bytes.assert_called_once()
        mock_audio_extractor.google_provider.transcribe_audio_uri.assert_called_once()
        mock_audio_extractor.whisper_provider.transcribe_audio_bytes.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_gcs_fallback_to_whisper(
        self, mock_mutagen, mock_start_span, mock_audio_extractor, sample_audio_document
    ):
        """Test that non-GCS storage falls back to Whisper directly."""
        # Mock audio duration
        mock_file = MagicMock()
        mock_file.info.length = 30.0
        mock_mutagen.return_value = mock_file

        # Mock S3 storage URI (not GCS)
        mock_audio_extractor.storage.get_storage_uri.return_value = (
            "s3://bucket/audio/test_audio.mp3"
        )
        mock_audio_extractor.storage.download.return_value = b"fake_audio_data"

        # Mock Whisper succeeds
        mock_audio_extractor.whisper_provider.supports_format.return_value = True
        mock_audio_extractor.whisper_provider.transcribe_audio_bytes.return_value = (
            "Transcribed text from Whisper"
        )

        # Test
        result = await mock_audio_extractor._transcribe_with_fallback(
            sample_audio_document, AudioFormat.MP3
        )

        # Assertions
        assert result == "Transcribed text from Whisper"
        mock_audio_extractor.google_provider.transcribe_audio_bytes.assert_not_called()
        mock_audio_extractor.google_provider.transcribe_audio_uri.assert_not_called()
        mock_audio_extractor.whisper_provider.transcribe_audio_bytes.assert_called_once()

    @pytest.mark.asyncio
    async def test_google_unsupported_format_fallback_to_whisper(
        self, mock_mutagen, mock_start_span, mock_audio_extractor, sample_audio_document
    ):
        """Test fallback to Whisper when Google doesn't support the audio format."""
        # Mock audio duration
        mock_file = MagicMock()
        mock_file.info.length = 30.0
        mock_mutagen.return_value = mock_file

        # Mock GCS storage URI
        mock_audio_extractor.storage.get_storage_uri.return_value = (
            "gs://bucket/audio/test_audio.mp3"
        )
        mock_audio_extractor.storage.download.return_value = b"fake_audio_data"

        # Mock Google provider doesn't support format
        mock_audio_extractor.google_provider.supports_format = MagicMock(
            return_value=False
        )

        # Mock Whisper succeeds
        mock_audio_extractor.whisper_provider.supports_format = MagicMock(
            return_value=True
        )
        mock_audio_extractor.whisper_provider.transcribe_audio_bytes = AsyncMock(
            return_value="Transcribed text from Whisper"
        )

        # Test
        result = await mock_audio_extractor._transcribe_with_fallback(
            sample_audio_document, AudioFormat.MP3
        )

        # Assertions
        assert result == "Transcribed text from Whisper"
        mock_audio_extractor.google_provider.transcribe_audio_bytes.assert_not_called()
        mock_audio_extractor.google_provider.transcribe_audio_uri.assert_not_called()
        mock_audio_extractor.whisper_provider.transcribe_audio_bytes.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_providers_fail(
        self, mock_mutagen, mock_start_span, mock_audio_extractor, sample_audio_document
    ):
        """Test that exception is raised when all transcription methods fail."""
        # Mock audio duration
        mock_file = MagicMock()
        mock_file.info.length = 30.0
        mock_mutagen.return_value = mock_file

        # Mock GCS storage URI
        mock_audio_extractor.storage.get_storage_uri.return_value = (
            "gs://bucket/audio/test_audio.mp3"
        )
        mock_audio_extractor.storage.download.return_value = b"fake_audio_data"

        # Mock Google provider supports format but fails
        mock_audio_extractor.google_provider.supports_format.return_value = True
        mock_audio_extractor.google_provider.transcribe_audio_bytes.side_effect = (
            Exception("Google short failed")
        )
        mock_audio_extractor.google_provider.transcribe_audio_uri.side_effect = (
            Exception("Google long failed")
        )

        # Mock Whisper also fails
        mock_audio_extractor.whisper_provider.supports_format.return_value = True
        mock_audio_extractor.whisper_provider.transcribe_audio_bytes.side_effect = (
            Exception("Whisper failed")
        )

        # Test
        with pytest.raises(Exception, match="All transcription methods failed"):
            await mock_audio_extractor._transcribe_with_fallback(
                sample_audio_document, AudioFormat.MP3
            )

    @pytest.mark.asyncio
    async def test_no_provider_supports_format(
        self, mock_mutagen, mock_start_span, mock_audio_extractor, sample_audio_document
    ):
        """Test that exception is raised when no provider supports the format."""
        # Mock audio duration
        mock_file = MagicMock()
        mock_file.info.length = 30.0
        mock_mutagen.return_value = mock_file

        # Mock GCS storage URI
        mock_audio_extractor.storage.get_storage_uri.return_value = (
            "gs://bucket/audio/test_audio.mp3"
        )
        mock_audio_extractor.storage.download.return_value = b"fake_audio_data"

        # Mock both providers don't support format - replace the methods completely
        mock_audio_extractor.google_provider.supports_format = MagicMock(
            return_value=False
        )
        mock_audio_extractor.whisper_provider.supports_format = MagicMock(
            return_value=False
        )

        # Test
        with pytest.raises(
            ValueError
        ):  # , match="No transcription provider supports format: mp3"):
            val = await mock_audio_extractor._transcribe_with_fallback(
                sample_audio_document, AudioFormat.MP3
            )
            print("VAL!!!")
            print(val)
