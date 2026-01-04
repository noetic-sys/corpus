"""Tests for naive chunking service."""

import pytest

from packages.documents.services.naive_chunking_service import (
    NaiveChunkingService,
    get_naive_chunking_service,
)
from packages.documents.models.domain.chunking_strategy import ChunkingStrategy


class TestNaiveChunkingService:
    """Unit tests for NaiveChunkingService."""

    @pytest.fixture
    def service(self):
        """Create a NaiveChunkingService instance."""
        return NaiveChunkingService()

    @pytest.fixture
    def sample_text(self):
        """Sample text for chunking tests."""
        return (
            "This is the first sentence. This is the second sentence. "
            "This is the third sentence.\n\n"
            "This is a new paragraph with more content. It has multiple sentences. "
            "And even more text here.\n\n"
            "Final paragraph with concluding remarks. The end."
        )

    @pytest.fixture
    def long_text(self):
        """Longer text that will produce multiple chunks."""
        paragraph = "This is a test paragraph with some content. " * 50
        return "\n\n".join([paragraph for _ in range(10)])

    def test_get_naive_chunking_service(self):
        """Test factory function returns service instance."""
        service = get_naive_chunking_service()
        assert isinstance(service, NaiveChunkingService)

    def test_chunk_id_on_object_not_in_metadata(self, service, long_text):
        """Test chunk_id is on chunk object, NOT in metadata dict.

        chunk_id is an identifier, not metadata. It's stored separately
        and injected at the API response layer.
        """
        chunks = service.chunk(long_text, ChunkingStrategy.FIXED_SIZE, document_id=123)

        assert len(chunks) > 1

        for chunk in chunks:
            # chunk_id should be on the object
            assert chunk.chunk_id is not None
            assert chunk.chunk_id.startswith("chunk-123-")

            # chunk_id should NOT be in metadata
            assert "chunk_id" not in chunk.metadata

    def test_chunk_fixed_size_metadata_fields(self, service, long_text):
        """Test fixed-size chunking produces correct metadata fields."""
        chunks = service.chunk(long_text, ChunkingStrategy.FIXED_SIZE, document_id=123)

        assert len(chunks) > 1

        for chunk in chunks:
            assert "char_start" in chunk.metadata
            assert "char_end" in chunk.metadata
            assert "overlap_prev" in chunk.metadata
            assert "overlap_next" in chunk.metadata
            assert "strategy" in chunk.metadata
            assert chunk.metadata["strategy"] == "fixed_size"

    def test_chunk_sentence_metadata_fields(self, service, long_text):
        """Test sentence chunking produces correct metadata fields."""
        chunks = service.chunk(long_text, ChunkingStrategy.SENTENCE, document_id=456)

        assert len(chunks) > 1

        for chunk in chunks:
            assert "char_start" in chunk.metadata
            assert "char_end" in chunk.metadata
            assert chunk.metadata["strategy"] == "sentence"
            # chunk_id should NOT be in metadata
            assert "chunk_id" not in chunk.metadata

    def test_chunk_paragraph_metadata_fields(self, service, long_text):
        """Test paragraph chunking produces correct metadata fields."""
        chunks = service.chunk(long_text, ChunkingStrategy.PARAGRAPH, document_id=789)

        assert len(chunks) > 1

        for chunk in chunks:
            assert "char_start" in chunk.metadata
            assert "char_end" in chunk.metadata
            assert chunk.metadata["strategy"] == "paragraph"
            # chunk_id should NOT be in metadata
            assert "chunk_id" not in chunk.metadata

    def test_chunk_none_metadata_fields(self, service, sample_text):
        """Test no-chunking strategy produces correct metadata fields."""
        chunks = service.chunk(sample_text, ChunkingStrategy.NONE, document_id=101)

        assert len(chunks) == 1

        chunk = chunks[0]
        assert chunk.chunk_id is not None
        assert "chunk_id" not in chunk.metadata
        assert chunk.metadata["strategy"] == "none"
        assert chunk.metadata["char_start"] == 0
        assert chunk.metadata["char_end"] == len(sample_text)

    def test_metadata_has_required_fields(self, service, long_text):
        """Test metadata has all required fields for API response."""
        chunks = service.chunk(long_text, ChunkingStrategy.FIXED_SIZE, document_id=999)

        for chunk in chunks:
            # Required fields
            assert "char_start" in chunk.metadata
            assert "char_end" in chunk.metadata
            assert "overlap_prev" in chunk.metadata
            assert "overlap_next" in chunk.metadata

            # Type checks
            assert isinstance(chunk.metadata["char_start"], int)
            assert isinstance(chunk.metadata["char_end"], int)
            assert isinstance(chunk.metadata["overlap_prev"], bool)
            assert isinstance(chunk.metadata["overlap_next"], bool)

    def test_fixed_size_overlap_flags(self, service, long_text):
        """Test overlap flags are set correctly for fixed-size chunks."""
        chunks = service.chunk(long_text, ChunkingStrategy.FIXED_SIZE, document_id=1)

        assert len(chunks) > 2

        assert chunks[0].metadata["overlap_prev"] is False
        assert chunks[0].metadata["overlap_next"] is True

        for chunk in chunks[1:-1]:
            assert chunk.metadata["overlap_prev"] is True
            assert chunk.metadata["overlap_next"] is True

        assert chunks[-1].metadata["overlap_prev"] is True
        assert chunks[-1].metadata["overlap_next"] is False

    def test_empty_text_returns_empty_list(self, service):
        """Test empty text returns empty chunk list."""
        for strategy in ChunkingStrategy:
            chunks = service.chunk("", strategy, document_id=1)
            assert chunks == []

    def test_chunk_ids_are_unique(self, service, long_text):
        """Test all chunk IDs are unique within a document."""
        chunks = service.chunk(long_text, ChunkingStrategy.FIXED_SIZE, document_id=1)

        chunk_ids = [chunk.chunk_id for chunk in chunks]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_chunk_id_contains_document_id(self, service, sample_text):
        """Test chunk IDs contain the document ID."""
        document_id = 12345
        chunks = service.chunk(
            sample_text, ChunkingStrategy.NONE, document_id=document_id
        )

        assert len(chunks) == 1
        assert str(document_id) in chunks[0].chunk_id

    def test_char_positions_are_valid(self, service, long_text):
        """Test character positions are valid."""
        chunks = service.chunk(long_text, ChunkingStrategy.PARAGRAPH, document_id=1)

        for chunk in chunks:
            assert chunk.metadata["char_start"] < chunk.metadata["char_end"]
            assert chunk.metadata["char_start"] >= 0

    def test_strategy_field_in_metadata(self, service, sample_text):
        """Test strategy field is included in metadata."""
        strategies = [
            (ChunkingStrategy.FIXED_SIZE, "fixed_size"),
            (ChunkingStrategy.SENTENCE, "sentence"),
            (ChunkingStrategy.PARAGRAPH, "paragraph"),
            (ChunkingStrategy.NONE, "none"),
        ]

        for strategy_enum, expected_name in strategies:
            chunks = service.chunk(sample_text, strategy_enum, document_id=1)
            if chunks:
                assert chunks[0].metadata["strategy"] == expected_name
