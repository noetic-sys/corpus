from typing import Optional

from .interface import DocumentExtractorInterface
from .text_extractor import TextExtractor
from .extractor_factory import ExtractorFactory
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


def get_document_extractor_for_file_type(
    file_type: str,
) -> Optional[DocumentExtractorInterface]:
    """Get document extractor instance based on file type."""
    try:
        return ExtractorFactory.get_extractor(file_type)
    except ValueError as e:
        logger.warning(f"No extractor found for file type: {file_type} - {e}")
        return None


def get_document_extractor() -> DocumentExtractorInterface:
    """Get document extractor instance. Uses TextExtractor by default."""
    return TextExtractor()
