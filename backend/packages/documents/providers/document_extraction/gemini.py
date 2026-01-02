from typing import Dict, Any
import io

from .interface import DocumentExtractorInterface
from packages.documents.services.external.gemini_service import GeminiService
from common.providers.storage.factory import get_storage
from common.core.otel_axiom_exporter import get_logger
from packages.documents.models.domain.document import DocumentModel

logger = get_logger(__name__)


class GeminiExtractor(DocumentExtractorInterface):
    """Document extractor using Google Gemini API for PDF, Word, PowerPoint, and image files."""

    def __init__(self):
        self.gemini_service = GeminiService()
        self.storage_provider = get_storage()

    async def extract_text(self, document: DocumentModel) -> str:
        """Extract text content from a document file using Gemini."""
        logger.info(f"Extracting text from {file_type} file using Gemini")
        if not self.supports_file_type(file_type):
            supported_types = "PDF, Word (doc/docx), PowerPoint (ppt/pptx), and image files (jpg, png, gif, webp)"
            raise ValueError(
                f"File type '{file_type}' is not supported. Supported types: {supported_types}"
            )

        return await self.gemini_service.extract_document(file_data, file_type)

    async def get_metadata(self, document: DocumentModel) -> Dict[str, Any]:
        """Extract metadata from a document file."""
        return {
            "file_type": file_type,
            "file_size": len(file_data),
            "extraction_method": "gemini",
        }

    def supports_file_type(self, file_type: str) -> bool:
        """Check if the extractor supports the given file type."""
        return self.gemini_service.supports_file_type(file_type)

    async def extract_and_save_to_s3(
        self, file_data: bytes, file_type: str, s3_key: str
    ) -> str:
        """Extract text from document and save directly as markdown to S3."""
        await self._ensure_storage_initialized()

        try:
            logger.info(f"Extracting text from {file_type} file using Gemini")
            # Extract text content
            extracted_text = await self.extract_text(file_data, file_type)
            logger.info(
                f"Successfully extracted {len(extracted_text)} characters from Gemini"
            )

            # The extracted text should already be in markdown format
            markdown_content = extracted_text

            # Save to S3 (convert bytes to BytesIO for upload method)

            markdown_bytes = markdown_content.encode("utf-8")
            await self.storage_provider.upload(
                s3_key,
                io.BytesIO(markdown_bytes),
                metadata={"content_type": "text/markdown"},
            )

            logger.info(f"Extracted content saved to S3: {s3_key}")
            return s3_key

        except Exception as e:
            logger.error(f"Error extracting and saving to S3: {e}")
            raise
