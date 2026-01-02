from typing import Dict, Any
import io

from .interface import DocumentExtractorInterface
from common.providers.storage.factory import get_storage
from common.core.otel_axiom_exporter import get_logger
from packages.documents.models.domain.document import DocumentModel

logger = get_logger(__name__)


class PassthroughExtractor(DocumentExtractorInterface):
    """Document extractor for text and markdown files that require no processing."""

    def __init__(self):
        self.storage_provider = get_storage()

    async def extract_text(self, document: DocumentModel) -> str:
        """Extract text content from text/markdown files (just decode bytes to string)."""
        file_type = document.content_type or ""
        if not self.supports_file_type(file_type):
            raise ValueError(
                f"File type '{file_type}' is not supported by PassthroughExtractor."
            )

        # Download file from storage
        file_data = await self.storage_provider.download(document.storage_key)
        if not file_data:
            raise ValueError(f"Failed to download file from {document.storage_key}")

        try:
            # Decode bytes to string, handling common encodings
            text_content = file_data.decode("utf-8")
            logger.info(
                f"Successfully decoded {file_type} file ({len(text_content)} characters)"
            )
            return text_content
        except UnicodeDecodeError:
            # Fallback to latin-1 if UTF-8 fails
            try:
                text_content = file_data.decode("latin-1")
                logger.warning(f"Decoded {file_type} file using latin-1 fallback")
                return text_content
            except UnicodeDecodeError as e:
                logger.error(f"Failed to decode {file_type} file: {e}")
                raise ValueError(f"Unable to decode {file_type} file as text")

    async def get_metadata(self, document: DocumentModel) -> Dict[str, Any]:
        """Extract metadata from a document file."""
        return {
            "file_type": document.content_type or "",
            "file_size": document.file_size or 0,
            "extraction_method": "passthrough",
        }

    def _normalize_file_type(self, file_type: str) -> str:
        """Normalize file type from MIME type to extension."""
        file_type_lower = file_type.lower()

        # Remove MIME type prefixes if present
        if file_type_lower.startswith("text/"):
            file_type_lower = file_type_lower.replace("text/", "")

        # Map common MIME types to extensions
        mime_to_extension = {
            "plain": "txt",
            "markdown": "md",
            "x-markdown": "md",
        }

        return mime_to_extension.get(file_type_lower, file_type_lower)

    def supports_file_type(self, file_type: str) -> bool:
        """Check if the extractor supports the given file type. Supports TXT and MD."""
        normalized_type = self._normalize_file_type(file_type)
        supported_types = {"txt", "md", "markdown"}
        return normalized_type in supported_types

    async def extract_and_save_to_s3(
        self, file_data: bytes, file_type: str, s3_key: str
    ) -> str:
        """Extract text and save as markdown to S3."""
        await self._ensure_storage_initialized()

        try:
            # Extract text content
            extracted_text = await self.extract_text(file_data, file_type)

            # Format content based on normalized file type
            normalized_type = self._normalize_file_type(file_type)
            if normalized_type in ["md", "markdown"]:
                # Markdown files: save as-is
                markdown_content = extracted_text
                logger.info(
                    f"Saving markdown file as-is ({len(extracted_text)} characters)"
                )
            else:
                # Text files: wrap in markdown
                markdown_content = f"# Document Content\n\n{extracted_text}"
                logger.info(
                    f"Wrapped text file in markdown formatting ({len(extracted_text)} characters)"
                )

            # Save to S3 (convert bytes to BytesIO for upload method)

            markdown_bytes = markdown_content.encode("utf-8")
            await self.storage_provider.upload(
                s3_key,
                io.BytesIO(markdown_bytes),
                metadata={"content_type": "text/markdown"},
            )

            logger.info(f"Passthrough extracted content saved to S3: {s3_key}")
            return s3_key

        except Exception as e:
            logger.error(f"Error in passthrough extraction and save to S3: {e}")
            raise
