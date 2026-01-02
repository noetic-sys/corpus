"""Tests for chunking strategy selection logic."""

import pytest
from pathlib import Path

from chunking_strategy import (
    ChunkingStrategyDecision,
    DocumentStructureStats,
    MarkdownHeader,
    decide_chunking_strategy,
    detect_markdown_structure,
)


class TestDetectMarkdownStructure:
    """Tests for markdown structure detection."""

    def test_structured_document(self, temp_markdown_file: Path):
        """Test detection of well-structured markdown."""
        stats = detect_markdown_structure(temp_markdown_file)

        assert stats.total_headers > 5
        assert stats.has_hierarchy is True
        assert len(stats.header_levels) >= 2
        assert 1 in stats.header_levels  # Has H1
        assert 2 in stats.header_levels  # Has H2

    def test_unstructured_document(self, temp_unstructured_file: Path):
        """Test detection of unstructured markdown (transcript)."""
        stats = detect_markdown_structure(temp_unstructured_file)

        # Transcript has no headers
        assert stats.total_headers == 0
        assert stats.has_hierarchy is False
        assert len(stats.header_levels) == 0

    def test_minimal_headers_document(self, tmp_path: Path):
        """Test document with too few headers."""
        content = "# Single Header\n\nSome content without more structure."
        file_path = tmp_path / "minimal.md"
        file_path.write_text(content, encoding="utf-8")

        stats = detect_markdown_structure(file_path)

        assert stats.total_headers == 1
        assert stats.has_hierarchy is False  # Only one level

    def test_flat_header_structure(self, tmp_path: Path):
        """Test document with headers but no hierarchy (all same level)."""
        content = """# Header 1

Content 1

# Header 2

Content 2

# Header 3

Content 3
"""
        file_path = tmp_path / "flat.md"
        file_path.write_text(content, encoding="utf-8")

        stats = detect_markdown_structure(file_path)

        assert stats.total_headers == 3
        assert stats.has_hierarchy is False  # All H1, no hierarchy
        assert stats.header_levels == [1]

    def test_sample_headers_populated(self, temp_markdown_file: Path):
        """Test that sample headers are populated."""
        stats = detect_markdown_structure(temp_markdown_file)

        assert len(stats.sample_headers) > 0
        assert len(stats.sample_headers) <= 5  # Max 5 samples
        assert isinstance(stats.sample_headers[0], MarkdownHeader)


class TestDecideChunkingStrategy:
    """Tests for chunking strategy decision logic."""

    def test_decision_for_structured_document(self, temp_markdown_file: Path):
        """Test that structured docs use PageIndex."""
        decision = decide_chunking_strategy(temp_markdown_file)

        assert decision.use_pageindex is True
        assert decision.strategy_name == "pageindex_enhanced"
        assert "hierarchical structure" in decision.reason.lower()
        assert decision.stats.total_headers >= 3
        assert decision.stats.has_hierarchy is True

    def test_decision_for_unstructured_document(self, temp_unstructured_file: Path):
        """Test that unstructured docs use semantic chunking."""
        decision = decide_chunking_strategy(temp_unstructured_file)

        assert decision.use_pageindex is False
        assert decision.strategy_name == "semantic"
        assert "no headers" in decision.reason.lower()

    def test_decision_with_custom_min_headers(self, temp_markdown_file: Path):
        """Test custom minimum header threshold."""
        # Require 100 headers (document won't meet this)
        decision = decide_chunking_strategy(temp_markdown_file, min_headers=100)

        assert decision.use_pageindex is False
        assert "too few headers" in decision.reason.lower()

    def test_decision_without_hierarchy_requirement(self, tmp_path: Path):
        """Test decision when hierarchy is not required."""
        # Create doc with many headers but no hierarchy
        content = "\n\n".join([f"# Header {i}\n\nContent {i}" for i in range(5)])
        file_path = tmp_path / "flat_many.md"
        file_path.write_text(content, encoding="utf-8")

        # Without hierarchy requirement, should use PageIndex
        decision = decide_chunking_strategy(file_path, require_hierarchy=False)
        assert decision.use_pageindex is True

        # With hierarchy requirement (default), should not
        decision = decide_chunking_strategy(file_path, require_hierarchy=True)
        assert decision.use_pageindex is False
        assert "lacks hierarchical structure" in decision.reason.lower()

    def test_decision_model_validation(self, temp_markdown_file: Path):
        """Test that decision returns valid Pydantic model."""
        decision = decide_chunking_strategy(temp_markdown_file)

        # Should be able to serialize/deserialize
        data = decision.model_dump()
        assert "use_pageindex" in data
        assert "strategy_name" in data
        assert "reason" in data
        assert "stats" in data

        # Reconstruct from dict
        decision2 = ChunkingStrategyDecision(**data)
        assert decision2.use_pageindex == decision.use_pageindex
        assert decision2.strategy_name == decision.strategy_name
