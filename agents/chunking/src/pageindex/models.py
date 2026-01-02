"""
Pydantic models for PageIndex document processing.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class MarkdownHeader(BaseModel):
    """Raw header extracted from markdown."""

    title: str = Field(..., description="Header text")
    line_num: int = Field(..., ge=1, description="Line number in document")
    level: int = Field(..., ge=1, le=6, description="Header level (1-6)")
    text: str = Field(..., description="Content under this header")
    text_token_count: Optional[int] = Field(None, description="Token count including children")


class TreeNode(BaseModel):
    """Hierarchical tree node representing document structure."""

    title: str = Field(..., description="Node title")
    node_id: str = Field(..., description="Zero-padded node ID (e.g., '0001')")
    text: str = Field(..., description="Text content of this node")
    line_num: int = Field(..., ge=1, description="Starting line number")
    nodes: List["TreeNode"] = Field(default_factory=list, description="Child nodes")
    summary: Optional[str] = Field(None, description="AI-generated summary (leaf nodes)")
    prefix_summary: Optional[str] = Field(
        None, description="AI-generated summary (parent nodes)"
    )


class DocumentTree(BaseModel):
    """Complete document tree structure."""

    doc_name: str = Field(..., description="Document name (without extension)")
    doc_description: Optional[str] = Field(None, description="Document-level summary")
    structure: List[TreeNode] = Field(..., description="Root-level tree nodes")


class PageIndexConfig(BaseModel):
    """Configuration for PageIndex processing."""

    enable_thinning: bool = Field(
        default=True, description="Merge small nodes into parents"
    )
    min_token_threshold: int = Field(
        default=500, ge=0, description="Min tokens before merging nodes"
    )
    generate_summaries: bool = Field(
        default=False, description="Generate AI summaries of nodes"
    )
    summary_token_threshold: int = Field(
        default=200, ge=0, description="Min tokens before summarizing"
    )
    include_text: bool = Field(
        default=True, description="Include full text in nodes"
    )
    include_node_ids: bool = Field(
        default=True, description="Add sequential node IDs"
    )
    generate_document_description: bool = Field(
        default=False, description="Generate document-level description"
    )
    model: str = Field(
        default="claude-3-haiku-20240307", description="LLM model for summaries"
    )
