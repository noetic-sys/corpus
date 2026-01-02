import io
from typing import Dict, Any
from markitdown import MarkItDown
from markitdown._stream_info import StreamInfo

from .interface import DocumentExtractorInterface
from common.core.otel_axiom_exporter import get_logger
from common.providers.storage.factory import get_storage
from packages.documents.models.domain.document import DocumentModel

logger = get_logger(__name__)


class ExcelExtractor(DocumentExtractorInterface):
    """Document extractor for Excel files using MarkItDown."""

    SUPPORTED_TYPES = {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/vnd.ms-excel": "xls",
        "text/csv": "csv",
    }

    def __init__(self):
        self.markitdown = MarkItDown(enable_plugins=True)
        self.storage = get_storage()

    def supports_file_type(self, file_type: str) -> bool:
        """Check if the extractor supports the given file type."""
        return file_type.lower() in self.SUPPORTED_TYPES

    async def extract_text(self, document: DocumentModel) -> str:
        """Extract text content from an Excel file."""
        try:
            # Download file from storage
            file_data = await self.storage.download(document.storage_key)
            if not file_data:
                raise ValueError(f"Failed to download file from {document.storage_key}")

            file_type = document.content_type or ""
            if file_type.lower() not in self.SUPPORTED_TYPES:
                raise ValueError(f"Unsupported file type: {file_type}")

            file_stream = io.BytesIO(file_data)
            # Use appropriate extension based on file type
            extension = ".xlsx" if "openxml" in file_type.lower() else ".xls"
            stream_info = StreamInfo(
                mimetype=file_type, extension=extension, filename=document.filename
            )
            result = self.markitdown.convert_stream(
                file_stream, stream_info=stream_info
            )

            if result and result.text_content:
                logger.info(f"Extracted text from Excel file ({file_type})")
                return result.text_content.strip()
            else:
                logger.warning(
                    f"No text content extracted from Excel file ({file_type})"
                )
                return ""

        except Exception as e:
            logger.error(f"Error extracting text from Excel file ({file_type}): {e}")
            raise Exception(f"Failed to extract text from Excel file: {str(e)}")

    async def get_metadata(self, document: DocumentModel) -> Dict[str, Any]:
        """Extract metadata from an Excel file."""
        try:
            # Download file from storage
            file_data = await self.storage.download(document.storage_key)
            if not file_data:
                raise ValueError(f"Failed to download file from {document.storage_key}")

            file_type = document.content_type or ""
            metadata = {
                "file_size": len(file_data),
                "file_type": file_type,
                "extractor": "ExcelExtractor",
            }

            if file_type.lower() not in self.SUPPORTED_TYPES:
                raise ValueError(f"Unsupported file type: {file_type}")

            file_stream = io.BytesIO(file_data)
            # Use appropriate extension based on file type
            extension = ".xlsx" if "openxml" in file_type.lower() else ".xls"
            stream_info = StreamInfo(
                mimetype=file_type, extension=extension, filename=document.filename
            )
            result = self.markitdown.convert_stream(
                file_stream, stream_info=stream_info
            )

            if result:
                if hasattr(result, "title") and result.title:
                    metadata["title"] = result.title

                # Add character and line count from extracted text
                if result.text_content:
                    metadata["character_count"] = len(result.text_content)
                    metadata["line_count"] = len(result.text_content.splitlines())

            return metadata

        except Exception as e:
            logger.error(
                f"Error extracting metadata from Excel file ({file_type}): {e}"
            )
            return {
                "file_size": document.file_size or 0,
                "file_type": document.content_type or "",
                "extractor": "ExcelExtractor",
                "error": str(e),
            }
