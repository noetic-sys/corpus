"""
Intelligent chunking strategy selection based on document structure.
"""

import re
from pathlib import Path
from typing import List
from pydantic import BaseModel, Field


class MarkdownHeader(BaseModel):
    """Represents a markdown header."""

    level: int = Field(..., ge=1, le=6, description="Header level (1-6)")
    title: str = Field(..., description="Header text")
    line_number: int = Field(..., description="Line number in document")


class DocumentStructureStats(BaseModel):
    """Statistics about document structure."""

    total_headers: int = Field(..., ge=0)
    header_levels: List[int] = Field(..., description="Unique header levels found")
    has_hierarchy: bool = Field(..., description="Whether multiple header levels exist")
    sample_headers: List[MarkdownHeader] = Field(default_factory=list)


class ChunkingStrategyDecision(BaseModel):
    """Decision about which chunking strategy to use."""

    use_pageindex: bool = Field(..., description="Whether to use PageIndex")
    strategy_name: str = Field(..., description="Name of chosen strategy")
    reason: str = Field(..., description="Human-readable reasoning")
    stats: DocumentStructureStats


def detect_markdown_structure(document_path: Path) -> DocumentStructureStats:
    """
    Detect document structure by analyzing markdown headers.

    Args:
        document_path: Path to markdown document

    Returns:
        DocumentStructureStats with analysis results
    """
    with open(document_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract headers (avoiding code blocks)
    lines = content.split('\n')
    headers: List[MarkdownHeader] = []
    in_code_block = False

    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()

        # Toggle code block state
        if stripped.startswith('```'):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        # Match headers
        match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if match:
            headers.append(
                MarkdownHeader(
                    level=len(match.group(1)),
                    title=match.group(2).strip(),
                    line_number=line_num
                )
            )

    # Calculate statistics
    header_levels = sorted(list(set(h.level for h in headers)))
    has_hierarchy = len(header_levels) >= 2

    return DocumentStructureStats(
        total_headers=len(headers),
        header_levels=header_levels,
        has_hierarchy=has_hierarchy,
        sample_headers=headers[:5]
    )


def decide_chunking_strategy(
    document_path: Path,
    min_headers: int = 3,
    require_hierarchy: bool = True
) -> ChunkingStrategyDecision:
    """
    Decide which chunking strategy to use based on document structure.

    Args:
        document_path: Path to document file
        min_headers: Minimum headers required for PageIndex
        require_hierarchy: Whether to require multiple header levels

    Returns:
        ChunkingStrategyDecision with strategy choice and reasoning
    """
    stats = detect_markdown_structure(document_path)

    # Determine if PageIndex should be used
    use_pageindex = stats.total_headers >= min_headers
    if require_hierarchy:
        use_pageindex = use_pageindex and stats.has_hierarchy

    if use_pageindex:
        strategy_name = "pageindex_enhanced"
        reason = f"Document has clear hierarchical structure ({stats.total_headers} headers across levels {stats.header_levels})"
    else:
        strategy_name = "semantic"
        if stats.total_headers == 0:
            reason = "Document has no headers (likely transcript or unstructured text)"
        elif stats.total_headers < min_headers:
            reason = f"Document has too few headers ({stats.total_headers} < {min_headers})"
        else:
            reason = "Document lacks hierarchical structure (single level of headers)"

    return ChunkingStrategyDecision(
        use_pageindex=use_pageindex,
        strategy_name=strategy_name,
        reason=reason,
        stats=stats
    )
