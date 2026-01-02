from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple


class HighlightData:
    """Data structure for text to highlight in a document."""

    def __init__(
        self,
        text: str,
        color: Tuple[float, float, float] = (1.0, 1.0, 0.0),  # Yellow by default
        citation_number: Optional[int] = None,
    ):
        self.text = text
        self.color = color  # RGB values 0.0-1.0
        self.citation_number = citation_number


class DocumentHighlightingInterface(ABC):
    """Interface for document highlighting providers."""

    @abstractmethod
    async def highlight_document(
        self,
        document_content: bytes,
        document_filename: str,
        highlights: List[HighlightData],
    ) -> bytes:
        """
        Highlight specified text in the document and return the modified document bytes.

        Args:
            document_content: Original document content as bytes
            document_filename: Filename to determine document type
            highlights: List of text strings to highlight

        Returns:
            Modified document bytes with highlights applied

        Raises:
            NotImplementedError: If the document type is not supported
        """
        pass

    @abstractmethod
    def supports_file_type(self, filename: str) -> bool:
        """
        Check if this provider supports highlighting for the given file type.

        Args:
            filename: Name of the file to check

        Returns:
            True if this provider can highlight this file type
        """
        pass

    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of supported file extensions.

        Returns:
            List of supported file extensions (e.g., ['.pdf', '.docx'])
        """
        pass
