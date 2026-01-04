"""
PageIndex-enhanced chunking using hierarchical document structure.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List

from documents.chunk import ChunkInfo, ChunkManifest
from pydantic import BaseModel, Field

from pageindex.models import PageIndexConfig, TreeNode
from pageindex.page_index_md import markdown_to_tree
from pageindex.utils import flatten_tree


class EnrichedChunkMetadata(BaseModel):
    """Extended chunk metadata with PageIndex information.

    Note: chunk_id is NOT included here - it's stored separately on the chunk
    object and injected at the API response layer.
    """

    node_id: str = Field(..., description="Hierarchical node ID")
    node_title: str = Field(..., description="Section title from PageIndex")
    line_start: int = Field(..., description="Starting line number")
    section: str = Field(..., description="Section title")
    page_start: None = Field(None, description="Not applicable for markdown")
    page_end: None = Field(None, description="Not applicable for markdown")
    char_start: int = Field(..., description="Character position start")
    char_end: int = Field(..., description="Character position end")
    overlap_prev: bool = Field(default=False)
    overlap_next: bool = Field(default=False)


async def chunk_with_pageindex(
    document_path: Path,
    document_id: int,
    output_dir: Path,
    model: str = "claude-3-haiku-20240307",
    enable_thinning: bool = True,
    min_token_threshold: int = 500,
) -> None:
    """
    Chunk document using PageIndex hierarchical structure.

    Args:
        document_path: Path to markdown document
        document_id: Document ID
        output_dir: Output directory for chunks
        model: Claude model for PageIndex processing
        enable_thinning: Whether to merge small nodes
        min_token_threshold: Minimum tokens before merging
    """
    print("Running PageIndex tree extraction...")

    # Configure PageIndex
    config = PageIndexConfig(
        enable_thinning=enable_thinning,
        min_token_threshold=min_token_threshold,
        generate_summaries=False,  # We don't need summaries
        include_text=True,  # We need the text content
        include_node_ids=True,  # We need node IDs for hierarchy
        model=model,
    )

    # Run PageIndex to get tree structure
    document_tree = await markdown_to_tree(document_path, config)

    # Flatten tree to get all nodes
    flat_nodes = flatten_tree(document_tree.structure)
    print(f"PageIndex extracted {len(flat_nodes)} nodes")

    # Convert tree nodes to chunks
    chunk_infos: List[ChunkInfo] = []

    for idx, node in enumerate(flat_nodes):
        chunk_id = f"chunk_{str(idx + 1).zfill(3)}"

        # Create metadata (chunk_id stored separately, not in metadata)
        metadata = EnrichedChunkMetadata(
            node_id=node.node_id,
            node_title=node.title,
            line_start=node.line_num,
            section=node.title,
            char_start=0,  # PageIndex doesn't track char positions
            char_end=len(node.text),
            overlap_prev=False,  # PageIndex doesn't create overlap
            overlap_next=False,
        )

        # Write chunk content
        chunk_path = output_dir / f"{chunk_id}.md"
        with open(chunk_path, "w", encoding="utf-8") as f:
            f.write(node.text)

        # Write chunk metadata
        meta_path = output_dir / f"{chunk_id}.meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata.model_dump(), f, indent=2)

        chunk_infos.append(
            ChunkInfo(
                chunk_id=chunk_id,
                section=node.title,
                page_range=None,  # No pages in markdown
            )
        )

    # Create manifest
    manifest = ChunkManifest(
        document_id=document_id, total_chunks=len(chunk_infos), chunks=chunk_infos
    )

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        # Add timestamp manually
        manifest_dict = manifest.model_dump()
        manifest_dict["created_at"] = datetime.utcnow().isoformat()
        json.dump(manifest_dict, f, indent=2)

    print(f"✓ Created {len(chunk_infos)} chunks using PageIndex structure")
