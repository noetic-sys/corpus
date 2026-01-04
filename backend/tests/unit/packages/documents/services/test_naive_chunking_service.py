"""Tests for naive chunking service."""

import pytest

from packages.documents.services.naive_chunking_service import (
    NaiveChunkingService,
    get_naive_chunking_service,
)
from packages.documents.models.domain.chunking_strategy import ChunkingStrategy
from packages.documents.models.schemas.chunk import ChunkMetadataResponse


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

    def test_chunk_fixed_size_includes_chunk_id_in_metadata(self, service, long_text):
        """Test fixed-size chunking includes chunk_id in metadata."""
        chunks = service.chunk(long_text, ChunkingStrategy.FIXED_SIZE, document_id=123)

        assert len(chunks) > 1

        for chunk in chunks:
            assert "chunk_id" in chunk.metadata
            assert chunk.metadata["chunk_id"] == chunk.chunk_id
            # Verify metadata can construct ChunkMetadataResponse
            response = ChunkMetadataResponse(**chunk.metadata)
            assert response.chunk_id == chunk.chunk_id

    def test_chunk_sentence_includes_chunk_id_in_metadata(self, service, long_text):
        """Test sentence chunking includes chunk_id in metadata."""
        chunks = service.chunk(long_text, ChunkingStrategy.SENTENCE, document_id=456)

        assert len(chunks) > 1

        for chunk in chunks:
            assert "chunk_id" in chunk.metadata
            assert chunk.metadata["chunk_id"] == chunk.chunk_id
            response = ChunkMetadataResponse(**chunk.metadata)
            assert response.chunk_id == chunk.chunk_id

    def test_chunk_paragraph_includes_chunk_id_in_metadata(self, service, long_text):
        """Test paragraph chunking includes chunk_id in metadata."""
        chunks = service.chunk(long_text, ChunkingStrategy.PARAGRAPH, document_id=789)

        assert len(chunks) > 1

        for chunk in chunks:
            assert "chunk_id" in chunk.metadata
            assert chunk.metadata["chunk_id"] == chunk.chunk_id
            response = ChunkMetadataResponse(**chunk.metadata)
            assert response.chunk_id == chunk.chunk_id

    def test_chunk_none_includes_chunk_id_in_metadata(self, service, sample_text):
        """Test no-chunking strategy includes chunk_id in metadata."""
        chunks = service.chunk(sample_text, ChunkingStrategy.NONE, document_id=101)

        assert len(chunks) == 1

        chunk = chunks[0]
        assert "chunk_id" in chunk.metadata
        assert chunk.metadata["chunk_id"] == chunk.chunk_id
        response = ChunkMetadataResponse(**chunk.metadata)
        assert response.chunk_id == chunk.chunk_id

    def test_metadata_has_required_fields_for_response_schema(self, service, long_text):
        """Test all metadata fields required by ChunkMetadataResponse are present."""
        chunks = service.chunk(long_text, ChunkingStrategy.FIXED_SIZE, document_id=999)

        for chunk in chunks:
            assert "chunk_id" in chunk.metadata
            assert "char_start" in chunk.metadata
            assert "char_end" in chunk.metadata
            assert "overlap_prev" in chunk.metadata
            assert "overlap_next" in chunk.metadata

            assert isinstance(chunk.metadata["chunk_id"], str)
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
        chunks = service.chunk(sample_text, ChunkingStrategy.NONE, document_id=document_id)

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
