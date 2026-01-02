from typing import Dict, Any
import io

from .interface import DocumentExtractorInterface
from packages.documents.services.external.datalab_service import DatalabService
from common.providers.storage.factory import get_storage
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class DatalabExtractor(DocumentExtractorInterface):
    """Document extractor using Datalab API for PDF, Word, PowerPoint, and image files."""

    def __init__(self):
        self.datalab_service = DatalabService()
        self.storage_provider = None

    async def _ensure_storage_initialized(self):
        """Ensure the storage provider is initialized."""
        if self.storage_provider is None:
            self.storage_provider = get_storage()

    async def extract_text(self, file_data: bytes, file_type: str) -> str:
        """Extract text content from a document file using Datalab."""
        logger.info(f"Extracting text from {file_type} file using Datalab")
        if not self.supports_file_type(file_type):
            raise ValueError(
                f"File type '{file_type}' is not supported. Only PDF files are supported by Datalab."
            )

        return await self.datalab_service.extract_document(file_data, file_type)

    async def get_metadata(self, file_data: bytes, file_type: str) -> Dict[str, Any]:
        """Extract metadata from a document file."""
        return {
            "file_type": file_type,
            "file_size": len(file_data),
            "extraction_method": "datalab",
        }

    def supports_file_type(self, file_type: str) -> bool:
        """Check if the extractor supports the given file type."""
        return self.datalab_service.supports_file_type(file_type)

    async def extract_and_save_to_s3(
        self, file_data: bytes, file_type: str, s3_key: str
    ) -> str:
        """Extract text from document and save directly as markdown to S3."""
        await self._ensure_storage_initialized()

        try:
            logger.info(f"Extracting text from {file_type} file using Datalab")
            # Extract text content
            extracted_text = await self.extract_text(file_data, file_type)
            logger.info(
                f"Successfully extracted {len(extracted_text)} characters from Datalab"
            )

            # Convert to markdown format (Datalab already returns markdown)
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
