"""
Naive chunking service for free/low-cost document processing.

These methods run in-process with zero AI cost, providing acceptable
but not optimal chunking quality. Returns chunks in the same format
as the agentic chunker so they can be processed by ChunkUploadService.
"""

import re
import uuid
from typing import List

from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.documents.models.schemas.chunk import ChunkUploadItem
from packages.documents.models.domain.chunking_strategy import ChunkingStrategy

logger = get_logger(__name__)


class NaiveChunkingService:
    """Service for non-AI document chunking."""

    @trace_span
    def chunk(
        self,
        text: str,
        strategy: ChunkingStrategy,
        document_id: int,
    ) -> List[ChunkUploadItem]:
        """
        Chunk text using the specified naive strategy.

        Args:
            text: Document text to chunk
            strategy: Chunking strategy to use
            document_id: Document ID (for chunk ID generation)

        Returns:
            List of ChunkUploadItem ready for ChunkUploadService
        """
        if strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(text, document_id)
        elif strategy == ChunkingStrategy.SENTENCE:
            return self._chunk_by_sentences(text, document_id)
        elif strategy == ChunkingStrategy.PARAGRAPH:
            return self._chunk_by_paragraphs(text, document_id)
        elif strategy == ChunkingStrategy.NONE:
            return self._chunk_none(text, document_id)
        else:
            # Default to sentence for unknown strategies
            logger.warning(f"Unknown strategy {strategy}, falling back to sentence")
            return self._chunk_by_sentences(text, document_id)

    def _chunk_fixed_size(
        self,
        text: str,
        document_id: int,
        chunk_size: int = 2000,
        overlap: int = 200,
    ) -> List[ChunkUploadItem]:
        """
        Split text into fixed-size chunks with overlap.

        Fastest method, but may split mid-sentence or mid-word.
        Use for: Free tier, very large documents.
        """
        if not text:
            return []

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]

            chunk_id = f"chunk-{document_id}-{chunk_index}-{uuid.uuid4().hex[:8]}"
            chunks.append(
                ChunkUploadItem(
                    chunk_id=chunk_id,
                    content=chunk_text,
                    metadata={
                        "chunk_index": chunk_index,
                        "char_start": start,
                        "char_end": end,
                        "strategy": "fixed_size",
                        "overlap_prev": chunk_index > 0,
                        "overlap_next": end < len(text),
                    },
                )
            )

            chunk_index += 1
            if end >= len(text):
                break
            start = end - overlap

        logger.info(f"Fixed-size chunking produced {len(chunks)} chunks")
        return chunks

    def _chunk_by_sentences(
        self,
        text: str,
        document_id: int,
        target_size: int = 2000,
    ) -> List[ChunkUploadItem]:
        """
        Split on sentence boundaries, respecting target size.

        Better than fixed-size as it preserves sentence integrity.
        Use for: Starter tier, general documents.
        """
        if not text:
            return []

        # Split on sentence-ending punctuation followed by whitespace
        sentence_pattern = r"(?<=[.!?])\s+"
        sentences = re.split(sentence_pattern, text)

        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # If adding this sentence exceeds target and we have content, flush
            if len(current_chunk) + len(sentence) + 1 > target_size and current_chunk:
                chunk_id = f"chunk-{document_id}-{chunk_index}-{uuid.uuid4().hex[:8]}"
                chunks.append(
                    ChunkUploadItem(
                        chunk_id=chunk_id,
                        content=current_chunk.strip(),
                        metadata={
                            "chunk_index": chunk_index,
                            "char_start": current_start,
                            "char_end": current_start + len(current_chunk),
                            "strategy": "sentence",
                            "overlap_prev": False,
                            "overlap_next": False,
                        },
                    )
                )
                chunk_index += 1
                current_start += len(current_chunk) + 1
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence

        # Don't forget the last chunk
        if current_chunk:
            chunk_id = f"chunk-{document_id}-{chunk_index}-{uuid.uuid4().hex[:8]}"
            chunks.append(
                ChunkUploadItem(
                    chunk_id=chunk_id,
                    content=current_chunk.strip(),
                    metadata={
                        "chunk_index": chunk_index,
                        "char_start": current_start,
                        "char_end": current_start + len(current_chunk),
                        "strategy": "sentence",
                        "overlap_prev": False,
                        "overlap_next": False,
                    },
                )
            )

        logger.info(f"Sentence chunking produced {len(chunks)} chunks")
        return chunks

    def _chunk_by_paragraphs(
        self,
        text: str,
        document_id: int,
        target_size: int = 3000,
    ) -> List[ChunkUploadItem]:
        """
        Split on paragraph boundaries, merging small paragraphs.

        Best naive method for well-structured documents.
        """
        if not text:
            return []

        # Split on double newlines (paragraph boundaries)
        paragraphs = re.split(r"\n\s*\n", text)

        chunks = []
        current_chunk = ""
        current_start = 0
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If adding this paragraph exceeds target and we have content, flush
            if len(current_chunk) + len(para) + 2 > target_size and current_chunk:
                chunk_id = f"chunk-{document_id}-{chunk_index}-{uuid.uuid4().hex[:8]}"
                chunks.append(
                    ChunkUploadItem(
                        chunk_id=chunk_id,
                        content=current_chunk.strip(),
                        metadata={
                            "chunk_index": chunk_index,
                            "char_start": current_start,
                            "char_end": current_start + len(current_chunk),
                            "strategy": "paragraph",
                            "overlap_prev": False,
                            "overlap_next": False,
                        },
                    )
                )
                chunk_index += 1
                current_start += len(current_chunk) + 2
                current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para

        # Don't forget the last chunk
        if current_chunk:
            chunk_id = f"chunk-{document_id}-{chunk_index}-{uuid.uuid4().hex[:8]}"
            chunks.append(
                ChunkUploadItem(
                    chunk_id=chunk_id,
                    content=current_chunk.strip(),
                    metadata={
                        "chunk_index": chunk_index,
                        "char_start": current_start,
                        "char_end": current_start + len(current_chunk),
                        "strategy": "paragraph",
                        "overlap_prev": False,
                        "overlap_next": False,
                    },
                )
            )

        logger.info(f"Paragraph chunking produced {len(chunks)} chunks")
        return chunks

    def _chunk_none(self, text: str, document_id: int) -> List[ChunkUploadItem]:
        """
        Return entire document as single chunk.

        Not recommended for most use cases.
        """
        if not text:
            return []

        chunk_id = f"chunk-{document_id}-0-{uuid.uuid4().hex[:8]}"
        return [
            ChunkUploadItem(
                chunk_id=chunk_id,
                content=text,
                metadata={
                    "chunk_index": 0,
                    "char_start": 0,
                    "char_end": len(text),
                    "strategy": "none",
                    "overlap_prev": False,
                    "overlap_next": False,
                },
            )
        ]


def get_naive_chunking_service() -> NaiveChunkingService:
    """Get naive chunking service instance."""
    return NaiveChunkingService()
