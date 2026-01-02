from __future__ import annotations

from typing import List

from .interface import DocumentHighlightingInterface, HighlightData
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class PassthroughHighlightProvider(DocumentHighlightingInterface):
    """Passthrough provider that returns documents unchanged when highlighting is not supported."""

    @trace_span
    async def highlight_document(
        self,
        document_content: bytes,
        document_filename: str,
        highlights: List[HighlightData],
    ) -> bytes:
        """Return the document unchanged."""
        logger.info(f"Passthrough for unsupported file type: {document_filename}")
        return document_content

    def supports_file_type(self, filename: str) -> bool:
        """Always returns True as this is the fallback provider."""
        return True

    def get_supported_extensions(self) -> List[str]:
        """Return empty list as this handles all remaining file types."""
        return []
