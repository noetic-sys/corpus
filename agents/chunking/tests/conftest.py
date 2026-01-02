"""Shared pytest configuration and fixtures for chunking agent tests."""

import pytest_asyncio
from pathlib import Path


@pytest_asyncio.fixture
def sample_structured_markdown() -> str:
    """Sample markdown with clear hierarchical structure."""
    return """# Introduction

This is the introduction section with some content.

## Background

Some background information here.

### Historical Context

Details about the historical context.

## Objectives

The main objectives of this document.

# Main Content

## Section 1

Content for section 1.

### Subsection 1.1

Detailed content for subsection 1.1.

### Subsection 1.2

More detailed content here.

## Section 2

Content for section 2.

# Conclusion

Final thoughts and summary.
"""


@pytest_asyncio.fixture
def sample_unstructured_markdown() -> str:
    """Sample markdown without clear structure (transcript-like)."""
    return """This is a transcript of a meeting that took place.

John: Hello everyone, thanks for joining.

Sarah: Thanks for having us.

John: Let's discuss the quarterly results. The revenue was up 15% compared to last quarter.

Sarah: That's great news. What about expenses?

John: Expenses increased by 8%, mostly due to hiring new staff.

Sarah: Makes sense. What are the projections for next quarter?

John: We're expecting similar growth trends to continue.
"""


@pytest_asyncio.fixture
def sample_minimal_headers_markdown() -> str:
    """Sample markdown with too few headers for PageIndex."""
    return """# Only One Header

This document has only a single header at the top.

The rest is just plain text without any structure.

More content here without hierarchy.
"""


@pytest_asyncio.fixture
def temp_markdown_file(tmp_path: Path, sample_structured_markdown: str) -> Path:
    """Create a temporary markdown file."""
    file_path = tmp_path / "test_document.md"
    file_path.write_text(sample_structured_markdown, encoding="utf-8")
    return file_path


@pytest_asyncio.fixture
def temp_unstructured_file(tmp_path: Path, sample_unstructured_markdown: str) -> Path:
    """Create a temporary unstructured markdown file."""
    file_path = tmp_path / "transcript.md"
    file_path.write_text(sample_unstructured_markdown, encoding="utf-8")
    return file_path
