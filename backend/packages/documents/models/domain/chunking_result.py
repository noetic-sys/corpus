"""Domain models for chunking workflow results."""

from dataclasses import dataclass

from packages.documents.models.domain.chunking_strategy import ChunkingStrategy


@dataclass
class ChunkingStrategyResult:
    """Result from determining chunking strategy."""

    strategy: ChunkingStrategy
    tier: str
    agentic_available: bool
    quota_exceeded: bool = False


@dataclass
class ChunkingResult:
    """Result from chunking operation (naive or agentic)."""

    document_id: int
    chunk_count: int
    s3_prefix: str
    strategy: ChunkingStrategy
