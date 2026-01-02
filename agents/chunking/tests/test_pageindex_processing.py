"""Tests for PageIndex markdown processing functions."""

import pytest

from pageindex.page_index_md import (
    build_tree_from_headers,
    extract_headers_from_markdown,
    extract_text_for_headers,
    merge_small_nodes,
)
from pageindex.models import MarkdownHeader, TreeNode


class TestExtractHeadersFromMarkdown:
    """Tests for header extraction."""

    def test_extract_simple_headers(self, sample_structured_markdown: str):
        """Test extracting headers from structured markdown."""
        headers, lines = extract_headers_from_markdown(sample_structured_markdown)

        assert len(headers) > 0
        assert all(isinstance(h, MarkdownHeader) for h in headers)
        assert len(lines) > 0

        # Check first header
        first_header = headers[0]
        assert first_header.title == "Introduction"
        assert first_header.level == 1
        assert first_header.line_num > 0

    def test_ignore_headers_in_code_blocks(self):
        """Test that headers in code blocks are ignored."""
        markdown = """# Real Header

```python
# This is not a header
## Neither is this
```

## Real Header 2
"""
        headers, _ = extract_headers_from_markdown(markdown)

        assert len(headers) == 2
        assert headers[0].title == "Real Header"
        assert headers[1].title == "Real Header 2"

    def test_extract_different_header_levels(self):
        """Test extraction of all header levels."""
        markdown = """# H1
## H2
### H3
#### H4
##### H5
###### H6
"""
        headers, _ = extract_headers_from_markdown(markdown)

        assert len(headers) == 6
        for i, header in enumerate(headers, 1):
            assert header.level == i

    def test_empty_document(self):
        """Test extraction from empty document."""
        headers, lines = extract_headers_from_markdown("")

        assert len(headers) == 0
        assert lines == [""]


class TestExtractTextForHeaders:
    """Tests for text content extraction."""

    def test_extract_text_between_headers(self):
        """Test extracting content between headers."""
        markdown = """# Header 1
Content for header 1
More content

## Header 2
Content for header 2
"""
        headers, lines = extract_headers_from_markdown(markdown)
        headers = extract_text_for_headers(headers, lines)

        assert len(headers) == 2
        assert "Content for header 1" in headers[0].text
        assert "Header 2" in headers[1].text

    def test_extract_text_for_last_header(self):
        """Test that last header gets all remaining text."""
        markdown = """# Header 1
Content 1

# Header 2
Content 2
More content 2
"""
        headers, lines = extract_headers_from_markdown(markdown)
        headers = extract_text_for_headers(headers, lines)

        assert "Content 2" in headers[1].text
        assert "More content 2" in headers[1].text


class TestMergeSmallNodes:
    """Tests for node merging logic."""

    def test_merge_small_nodes_below_threshold(self):
        """Test merging nodes below token threshold."""
        headers = [
            MarkdownHeader(
                title="Big Section",
                line_num=1,
                level=1,
                text="A" * 100,  # Small text
                text_token_count=50,  # Below threshold
            ),
            MarkdownHeader(
                title="Subsection",
                line_num=5,
                level=2,
                text="B" * 50,
                text_token_count=25,
            ),
        ]

        merged = merge_small_nodes(headers, min_tokens=100, model="claude-3-haiku")

        # Should merge child into parent since parent is below threshold
        assert len(merged) < len(headers)

    def test_dont_merge_large_nodes(self):
        """Test that large nodes are not merged."""
        headers = [
            MarkdownHeader(
                title="Big Section",
                line_num=1,
                level=1,
                text="A" * 1000,
                text_token_count=500,  # Above threshold
            ),
            MarkdownHeader(
                title="Another Section",
                line_num=10,
                level=1,
                text="B" * 1000,
                text_token_count=500,
            ),
        ]

        merged = merge_small_nodes(headers, min_tokens=100, model="claude-3-haiku")

        # Should not merge since both are above threshold
        assert len(merged) == len(headers)


class TestBuildTreeFromHeaders:
    """Tests for tree building logic."""

    def test_build_simple_tree(self):
        """Test building tree from flat headers."""
        headers = [
            MarkdownHeader(title="Chapter 1", line_num=1, level=1, text="Content 1"),
            MarkdownHeader(
                title="Section 1.1", line_num=5, level=2, text="Content 1.1"
            ),
            MarkdownHeader(title="Chapter 2", line_num=10, level=1, text="Content 2"),
        ]

        tree = build_tree_from_headers(headers)

        assert len(tree) == 2  # Two root nodes (Chapter 1 and 2)
        assert all(isinstance(node, TreeNode) for node in tree)

        # First chapter should have subsection
        assert len(tree[0].nodes) == 1
        assert tree[0].nodes[0].title == "Section 1.1"

        # Second chapter should have no children
        assert len(tree[1].nodes) == 0

    def test_build_deep_hierarchy(self):
        """Test building tree with deep nesting."""
        headers = [
            MarkdownHeader(title="H1", line_num=1, level=1, text="C1"),
            MarkdownHeader(title="H2", line_num=2, level=2, text="C2"),
            MarkdownHeader(title="H3", line_num=3, level=3, text="C3"),
            MarkdownHeader(title="H4", line_num=4, level=4, text="C4"),
        ]

        tree = build_tree_from_headers(headers)

        assert len(tree) == 1
        assert tree[0].title == "H1"
        assert len(tree[0].nodes) == 1
        assert tree[0].nodes[0].title == "H2"
        assert len(tree[0].nodes[0].nodes) == 1
        assert tree[0].nodes[0].nodes[0].title == "H3"

    def test_build_tree_from_empty_headers(self):
        """Test building tree from empty header list."""
        tree = build_tree_from_headers([])

        assert len(tree) == 0

    def test_node_ids_assigned_sequentially(self):
        """Test that node IDs are assigned sequentially."""
        headers = [
            MarkdownHeader(title="H1", line_num=1, level=1, text="C1"),
            MarkdownHeader(title="H2", line_num=2, level=2, text="C2"),
            MarkdownHeader(title="H3", line_num=3, level=1, text="C3"),
        ]

        tree = build_tree_from_headers(headers)

        # IDs should be sequential regardless of hierarchy
        assert tree[0].node_id == "0001"
        assert tree[0].nodes[0].node_id == "0002"
        assert tree[1].node_id == "0003"
