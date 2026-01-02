from abc import ABC, abstractmethod
from typing import Dict, Any

from packages.documents.models.domain.document import DocumentModel


class DocumentExtractorInterface(ABC):
    @abstractmethod
    async def extract_text(self, document: DocumentModel) -> str:
        """Extract text content from a document file."""
        pass

    @abstractmethod
    async def get_metadata(self, document: DocumentModel) -> Dict[str, Any]:
        """Extract metadata from a document file."""
        pass

    @abstractmethod
    def supports_file_type(self, file_type: str) -> bool:
        """Check if the extractor supports the given file type."""
        pass
