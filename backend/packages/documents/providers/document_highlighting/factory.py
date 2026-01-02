from __future__ import annotations

from typing import List

from .interface import DocumentHighlightingInterface
from .pdf_provider import PDFHighlightProvider
from .powerpoint_provider import PowerPointHighlightProvider
from .word_provider import WordHighlightProvider
from .markdown_provider import MarkdownHighlightProvider
from .passthrough_provider import PassthroughHighlightProvider
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class DocumentHighlightProviderFactory:
    """Factory for creating appropriate document highlighting providers."""

    def __init__(self):
        # Initialize providers in order of preference
        self._providers = [
            PDFHighlightProvider(),
            PowerPointHighlightProvider(),
            WordHighlightProvider(),
            MarkdownHighlightProvider(),
            PassthroughHighlightProvider(),  # Always last as fallback
        ]

    @trace_span
    def get_provider(self, filename: str) -> DocumentHighlightingInterface:
        """
        Get the appropriate highlighting provider for the given file.

        Args:
            filename: Name of the file to highlight

        Returns:
            DocumentHighlightingInterface instance that can handle this file type
        """
        for provider in self._providers:
            if provider.supports_file_type(filename):
                logger.info(
                    f"Selected {provider.__class__.__name__} for file: {filename}"
                )
                return provider

        # This should never happen since PassthroughProvider supports everything
        logger.warning(f"No provider found for file: {filename}, using passthrough")
        return PassthroughHighlightProvider()

    def get_supported_extensions(self) -> List[str]:
        """Get all supported file extensions across all providers."""
        extensions = []
        for provider in self._providers:
            extensions.extend(provider.get_supported_extensions())
        return list(set(extensions))  # Remove duplicates


# Global factory instance
_factory = DocumentHighlightProviderFactory()


def get_highlight_provider(filename: str) -> DocumentHighlightingInterface:
    """
    Get the appropriate highlighting provider for the given file.

    Args:
        filename: Name of the file to highlight

    Returns:
        DocumentHighlightingInterface instance that can handle this file type
    """
    return _factory.get_provider(filename)


def get_supported_highlight_extensions() -> List[str]:
    """Get all supported file extensions for highlighting."""
    return _factory.get_supported_extensions()
