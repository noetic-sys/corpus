"""Tests for PageIndex Pydantic models."""

import pytest
from pydantic import ValidationError

from pageindex.models import (
    DocumentTree,
    MarkdownHeader,
    PageIndexConfig,
    TreeNode,
)


class TestMarkdownHeader:
    """Tests for MarkdownHeader model."""

    def test_valid_header(self):
        """Test creating a valid header."""
        header = MarkdownHeader(
            title="Test Header",
            line_num=5,
            level=2,
            text="Some content here",
        )
        assert header.title == "Test Header"
        assert header.line_num == 5
        assert header.level == 2
        assert header.text == "Some content here"

    def test_invalid_level_too_low(self):
        """Test that level must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            MarkdownHeader(
                title="Test",
                line_num=1,
                level=0,  # Invalid
                text="Content",
            )
        assert "level" in str(exc_info.value)

    def test_invalid_level_too_high(self):
        """Test that level must be <= 6."""
        with pytest.raises(ValidationError) as exc_info:
            MarkdownHeader(
                title="Test",
                line_num=1,
                level=7,  # Invalid
                text="Content",
            )
        assert "level" in str(exc_info.value)

    def test_invalid_line_num(self):
        """Test that line_num must be >= 1."""
        with pytest.raises(ValidationError) as exc_info:
            MarkdownHeader(
                title="Test",
                line_num=0,  # Invalid
                level=1,
                text="Content",
            )
        assert "line_num" in str(exc_info.value)


class TestTreeNode:
    """Tests for TreeNode model."""

    def test_valid_node_without_children(self):
        """Test creating a leaf node."""
        node = TreeNode(
            title="Section 1",
            node_id="0001",
            text="Section content",
            line_num=10,
            nodes=[],
        )
        assert node.title == "Section 1"
        assert node.node_id == "0001"
        assert len(node.nodes) == 0

    def test_valid_node_with_children(self):
        """Test creating a parent node with children."""
        child = TreeNode(
            title="Subsection",
            node_id="0002",
            text="Subsection content",
            line_num=15,
            nodes=[],
        )
        parent = TreeNode(
            title="Section",
            node_id="0001",
            text="Section content",
            line_num=10,
            nodes=[child],
        )
        assert len(parent.nodes) == 1
        assert parent.nodes[0].title == "Subsection"

    def test_optional_summary_fields(self):
        """Test that summary fields are optional."""
        node = TreeNode(
            title="Test",
            node_id="0001",
            text="Content",
            line_num=1,
            summary="This is a summary",
            prefix_summary="Prefix summary",
        )
        assert node.summary == "This is a summary"
        assert node.prefix_summary == "Prefix summary"


class TestDocumentTree:
    """Tests for DocumentTree model."""

    def test_valid_document_tree(self):
        """Test creating a valid document tree."""
        node = TreeNode(
            title="Chapter 1",
            node_id="0001",
            text="Content",
            line_num=1,
            nodes=[],
        )
        tree = DocumentTree(
            doc_name="test_document",
            structure=[node],
        )
        assert tree.doc_name == "test_document"
        assert len(tree.structure) == 1
        assert tree.doc_description is None

    def test_document_tree_with_description(self):
        """Test document tree with optional description."""
        node = TreeNode(
            title="Chapter 1",
            node_id="0001",
            text="Content",
            line_num=1,
            nodes=[],
        )
        tree = DocumentTree(
            doc_name="test_document",
            doc_description="A test document about testing",
            structure=[node],
        )
        assert tree.doc_description == "A test document about testing"


class TestPageIndexConfig:
    """Tests for PageIndexConfig model."""

    def test_default_config(self):
        """Test config with default values."""
        config = PageIndexConfig()
        assert config.enable_thinning is True
        assert config.min_token_threshold == 500
        assert config.generate_summaries is False
        assert config.include_text is True
        assert config.include_node_ids is True
        assert config.model == "claude-3-haiku-20240307"

    def test_custom_config(self):
        """Test config with custom values."""
        config = PageIndexConfig(
            enable_thinning=False,
            min_token_threshold=1000,
            generate_summaries=True,
            model="claude-3-opus-20240229",
        )
        assert config.enable_thinning is False
        assert config.min_token_threshold == 1000
        assert config.generate_summaries is True
        assert config.model == "claude-3-opus-20240229"

    def test_invalid_min_token_threshold(self):
        """Test that min_token_threshold must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            PageIndexConfig(min_token_threshold=-1)
        assert "min_token_threshold" in str(exc_info.value)

    def test_config_serialization(self):
        """Test that config can be serialized/deserialized."""
        config = PageIndexConfig(
            enable_thinning=False,
            min_token_threshold=750,
        )
        data = config.model_dump()
        assert data["enable_thinning"] is False
        assert data["min_token_threshold"] == 750

        # Reconstruct from dict
        config2 = PageIndexConfig(**data)
        assert config2.enable_thinning == config.enable_thinning
        assert config2.min_token_threshold == config.min_token_threshold
