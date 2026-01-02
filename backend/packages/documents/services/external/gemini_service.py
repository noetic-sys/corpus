import tempfile
import os

import google.generativeai as genai

from common.core.otel_axiom_exporter import get_logger
from common.core.config import settings
from common.providers.api_keys import get_rotator, APIProviderType

logger = get_logger(__name__)


class GeminiService:
    """Service for interacting with Google Gemini API for document extraction."""

    def __init__(self):
        self.model_name = settings.gemini_model
        self.rotator = get_rotator(APIProviderType.GEMINI)

    async def extract_document(self, file_data: bytes, file_type: str) -> str:
        """Extract text content from a document using Gemini API."""
        if not self.supports_file_type(file_type):
            raise ValueError(f"File type '{file_type}' is not supported by Gemini")

        normalized_file_type = self._normalize_file_type(file_type)
        logger.info(
            f"Extracting {file_type} document using Gemini (normalized: {normalized_file_type})"
        )

        try:
            return await self._extract_from_bytes(file_data, normalized_file_type)

        except Exception as e:
            logger.error(f"Error during Gemini document extraction: {e}")
            raise

    async def _extract_from_bytes(self, file_data: bytes, file_type: str) -> str:
        """Extract content from file bytes using Gemini API."""
        logger.info("Starting Gemini extraction from file bytes")

        prompt = """You are a very professional document summarization and extraction specialist.
Please extract all the text content from the given document in a structured markdown format.
Preserve the document structure, headings, and formatting as much as possible.
Return only the extracted content without any additional commentary."""

        # Get rotated API key
        api_key = self.rotator.get_next_key()

        try:
            # Configure the API with the rotated key
            genai.configure(api_key=api_key)

            # Initialize the Gemini model with rotated key
            model = genai.GenerativeModel(self.model_name)

            # Create a temporary file for upload
            with tempfile.NamedTemporaryFile(
                suffix=f".{self._normalize_file_type(file_type)}", delete=False
            ) as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name

            try:
                # Upload file to Gemini
                logger.info("Uploading file to Gemini...")
                uploaded_file = genai.upload_file(
                    path=temp_file_path, display_name="Document"
                )
                logger.info(f"Uploaded file as: {uploaded_file.uri}")

                # Generate content using the uploaded document
                response = model.generate_content([uploaded_file, prompt])

                if not response.text:
                    raise Exception("Gemini returned empty text content")

                logger.info(
                    f"Gemini extraction completed successfully ({len(response.text)} characters)"
                )

                # Report success
                self.rotator.report_success(api_key)

                return response.text

            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except Exception as e:
            # Report failure
            self.rotator.report_failure(api_key)
            logger.error(f"Error calling Gemini API: {e}")
            raise Exception(f"Gemini extraction failed: {e}")

    def _get_mime_type(self, file_type: str) -> str:
        """Get the appropriate MIME type for the file extension."""
        mime_type_map = {
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "ppt": "application/vnd.ms-powerpoint",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        return mime_type_map.get(file_type.lower(), "application/octet-stream")

    def _normalize_file_type(self, file_type: str) -> str:
        """Normalize file type from MIME type to extension."""
        file_type_lower = file_type.lower()

        # Remove MIME type prefixes if present
        if file_type_lower.startswith("application/"):
            file_type_lower = file_type_lower.replace("application/", "")
        elif file_type_lower.startswith("image/"):
            file_type_lower = file_type_lower.replace("image/", "")

        # Map common MIME types to extensions
        mime_to_extension = {
            "pdf": "pdf",
            "msword": "doc",
            "vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
            "vnd.ms-powerpoint": "ppt",
            "vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
            "jpeg": "jpg",
            "png": "png",
            "gif": "gif",
            "webp": "webp",
        }

        return mime_to_extension.get(file_type_lower, file_type_lower)

    def supports_file_type(self, file_type: str) -> bool:
        """Check if the service supports the given file type."""
        normalized_type = self._normalize_file_type(file_type)
        # Gemini supports PDF, Word, PowerPoint, and common image formats
        supported_types = {
            "pdf",
            "doc",
            "docx",
            "ppt",
            "pptx",
            "jpg",
            "jpeg",
            "png",
            "gif",
            "webp",
        }
        return normalized_type in supported_types
