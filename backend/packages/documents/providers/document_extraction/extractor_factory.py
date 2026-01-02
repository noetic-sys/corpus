from common.core.otel_axiom_exporter import get_logger

from packages.documents.models.domain.document_types import DocumentType, ExtractorType
from .interface import DocumentExtractorInterface
from .passthrough_extractor import PassthroughExtractor
from .gemini import GeminiExtractor
from .excel_extractor import ExcelExtractor
from .powerpoint_extractor import PowerPointExtractor
from .word_extractor import WordExtractor
from .audio_extractor import AudioExtractor

logger = get_logger(__name__)


class ExtractorFactory:
    """Factory for creating appropriate document extractors based on file type."""

    # Mapping from extractor types to actual classes
    _EXTRACTOR_CLASSES = {
        ExtractorType.GEMINI: GeminiExtractor,
        ExtractorType.PASSTHROUGH: PassthroughExtractor,
        ExtractorType.WORD: WordExtractor,
        ExtractorType.POWERPOINT: PowerPointExtractor,
        ExtractorType.EXCEL: ExcelExtractor,
        ExtractorType.AUDIO: AudioExtractor,
    }

    @staticmethod
    def get_extractor(file_type: str) -> DocumentExtractorInterface:
        """
        Get the appropriate document extractor for the given file type.

        Args:
            file_type: The file extension (e.g., 'pdf', 'txt', 'md') or MIME type

        Returns:
            DocumentExtractorInterface: The appropriate extractor instance

        Raises:
            ValueError: If the file type is not supported
        """
        # Try to find document type by extension or MIME type
        doc_type = None

        # If it looks like a MIME type
        if "/" in file_type:
            doc_type = DocumentType.from_mime_type(file_type)
        else:
            # Try as extension (add dot if missing)
            ext = file_type if file_type.startswith(".") else f".{file_type}"
            doc_type = DocumentType.from_extension(ext)

        if not doc_type:
            supported_types = (
                DocumentType.get_all_extensions() + DocumentType.get_all_mime_types()
            )
            raise ValueError(
                f"Unsupported file type '{file_type}'. Supported types: {supported_types}"
            )

        if not doc_type.value.is_extractable:
            raise ValueError(f"File type '{file_type}' is not extractable")

        # Get the extractor class
        extractor_type = doc_type.value.extractor_type
        extractor_class = ExtractorFactory._EXTRACTOR_CLASSES.get(extractor_type)

        if not extractor_class:
            raise ValueError(f"No extractor class found for '{extractor_type}'")

        logger.info(f"Using {extractor_class.__name__} for {file_type} file")
        return extractor_class()

    @staticmethod
    def get_supported_file_types() -> list[str]:
        """Get a list of all supported file types (extensions and MIME types)."""
        return DocumentType.get_all_extensions() + DocumentType.get_all_mime_types()

    @staticmethod
    def get_supported_extensions() -> list[str]:
        """Get a list of all supported file extensions."""
        return DocumentType.get_all_extensions()

    @staticmethod
    def get_supported_mime_types() -> list[str]:
        """Get a list of all supported MIME types."""
        return DocumentType.get_all_mime_types()

    @staticmethod
    def get_extractable_extensions() -> list[str]:
        """Get a list of extractable file extensions."""
        return DocumentType.get_extractable_extensions()

    @staticmethod
    def is_supported_file_type(file_type: str) -> bool:
        """Check if a file type is supported."""
        if "/" in file_type:
            return DocumentType.from_mime_type(file_type) is not None
        else:
            ext = file_type if file_type.startswith(".") else f".{file_type}"
            return DocumentType.from_extension(ext) is not None

    @staticmethod
    def is_extractable_file_type(file_type: str) -> bool:
        """Check if a file type is extractable."""
        doc_type = None
        if "/" in file_type:
            doc_type = DocumentType.from_mime_type(file_type)
        else:
            ext = file_type if file_type.startswith(".") else f".{file_type}"
            doc_type = DocumentType.from_extension(ext)

        return doc_type is not None and doc_type.value.is_extractable


# Global function for easy access
def get_document_extractor(file_type: str) -> DocumentExtractorInterface:
    """
    Convenience function to get a document extractor.

    Args:
        file_type: The file extension (e.g., 'pdf', 'txt', 'md')

    Returns:
        DocumentExtractorInterface: The appropriate extractor instance
    """
    return ExtractorFactory.get_extractor(file_type)
