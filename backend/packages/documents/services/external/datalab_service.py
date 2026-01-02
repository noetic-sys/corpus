import asyncio
import tempfile
import os
import aiohttp
import aiofiles

from common.core.config import settings
from common.core.otel_axiom_exporter import get_logger

logger = get_logger(__name__)


class DatalabService:
    """Service for interacting with Datalab API for document extraction."""

    def __init__(self):
        self.api_url = "https://www.datalab.to/api/v1/marker"
        self.api_key = settings.datalab_api_key

    async def extract_document(self, file_data: bytes, file_type: str) -> str:
        """Extract text content from a document using Datalab marker API."""
        if not self.supports_file_type(file_type):
            raise ValueError(f"File type '{file_type}' is not supported by Datalab")

        # Normalize file type for internal processing
        normalized_file_type = self._normalize_file_type(file_type)
        logger.info(
            f"Extracting {file_type} document using Datalab (normalized: {normalized_file_type})"
        )

        try:
            # Create a temporary file for upload
            with tempfile.NamedTemporaryFile(
                suffix=f".{normalized_file_type}", delete=False
            ) as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name

            try:
                # Upload file and extract
                return await self._upload_and_extract(
                    temp_file_path, normalized_file_type
                )

            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except Exception as e:
            logger.error(f"Error during document extraction: {e}")
            raise

    async def _upload_and_extract(self, file_path: str, file_type: str) -> str:
        """Upload file to Datalab and extract content."""
        logger.info("Starting file upload to Datalab")

        headers = {"X-API-Key": self.api_key}

        # Prepare form data based on the API documentation
        data = aiohttp.FormData()

        # Add file
        async with aiofiles.open(file_path, "rb") as f:
            file_content = await f.read()
            data.add_field(
                "file",
                file_content,
                filename=f"document.{file_type}",
                content_type=self._get_content_type(file_type),
            )

        # Add optional parameters for better extraction
        data.add_field("max_pages", "100")  # Reasonable limit
        data.add_field("force_ocr", "false")  # Use built-in text when possible
        data.add_field("paginate", "false")  # Don't add page separators
        data.add_field("output_format", "markdown")  # Get markdown output
        data.add_field("use_llm", "true")  # Use LLM for better accuracy

        async with aiohttp.ClientSession() as session:
            logger.info(f"Sending request to Datalab API: {self.api_url}")

            async with session.post(
                self.api_url,
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(total=300),  # 5 minute timeout
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Datalab API error {response.status}: {error_text}")
                    raise Exception(
                        f"Datalab extraction failed with status {response.status}: {error_text}"
                    )

                # Get the initial response with request_id
                initial_response = await response.json()

                if not initial_response.get("success"):
                    error_msg = initial_response.get("error", "Unknown error")
                    raise Exception(f"Datalab extraction failed: {error_msg}")

                request_check_url = initial_response.get("request_check_url")
                if not request_check_url:
                    raise Exception("Datalab response missing request_check_url")

                logger.info(
                    f"Datalab extraction initiated. Request ID: {initial_response.get('request_id')}"
                )

                # Poll for completion
                return await self._poll_extraction_result(request_check_url)

    async def _poll_extraction_result(self, request_check_url: str) -> str:
        """Poll the Datalab API for extraction completion and return markdown content."""
        max_attempts = 60  # 60 attempts with 2 second intervals = 2 minutes max
        attempt = 0

        async with aiohttp.ClientSession() as session:
            while attempt < max_attempts:
                logger.info(
                    f"Polling for extraction result... (attempt {attempt + 1}/{max_attempts})"
                )

                try:
                    result = await self._check_extraction_status_once(
                        request_check_url, session
                    )

                    if result["status"] == "completed":
                        return result["markdown_content"]
                    elif result["status"] == "failed":
                        raise Exception(result["error"])

                    # Still processing, wait and try again
                    await asyncio.sleep(2)
                    attempt += 1

                except Exception as e:
                    if attempt >= max_attempts - 1:
                        raise
                    logger.warning(
                        f"Error polling extraction status (attempt {attempt + 1}): {e}"
                    )
                    await asyncio.sleep(2)
                    attempt += 1

        raise Exception(
            f"Datalab extraction timed out after {max_attempts * 2} seconds"
        )

    async def _check_extraction_status_once(
        self, request_check_url: str, session: aiohttp.ClientSession = None
    ) -> dict:
        """
        Check extraction status once without looping.
        Returns dict with status, markdown_content (if complete), or error.
        """
        close_session = False
        if session is None:
            session = aiohttp.ClientSession()
            close_session = True

        try:
            async with session.get(
                request_check_url,
                headers={"X-API-Key": self.api_key},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        f"Error checking extraction status: {response.status} - {error_text}"
                    )
                    return {
                        "status": "failed",
                        "error": f"Status check failed: {error_text}",
                    }

                result = await response.json()
                status = result.get("status", "").lower()

                if status == "complete":
                    markdown_content = result.get("markdown", "")
                    if not markdown_content:
                        return {"status": "failed", "error": "Empty markdown content"}

                    logger.info(
                        f"Extraction completed successfully ({len(markdown_content)} characters)"
                    )
                    return {"status": "completed", "markdown_content": markdown_content}

                elif status in ["failed", "error"]:
                    error_msg = result.get("error", "Unknown error")
                    return {"status": "failed", "error": error_msg}

                else:
                    # Still processing
                    return {"status": "pending"}

        finally:
            if close_session:
                await session.close()

    async def check_extraction_status(self, request_check_url: str) -> dict:
        """
        Public method to check extraction status once for Temporal workflows.
        Returns dict with status: 'pending', 'completed', or 'failed'
        """
        return await self._check_extraction_status_once(request_check_url)

    async def start_async_extraction(
        self, file_data: bytes, file_type: str = "pdf"
    ) -> str:
        """
        Start async extraction and return request_check_url for polling.
        Used by Temporal workflows for async job management.
        """
        if not self.supports_file_type(file_type):
            raise ValueError(f"File type '{file_type}' is not supported by Datalab")

        # Normalize file type for internal processing
        normalized_file_type = self._normalize_file_type(file_type)
        logger.info(
            f"Starting async extraction for {file_type} document using Datalab (normalized: {normalized_file_type})"
        )

        try:
            # Create a temporary file for upload
            with tempfile.NamedTemporaryFile(
                suffix=f".{normalized_file_type}", delete=False
            ) as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name

            try:
                # Upload file and get job details
                return await self._upload_and_get_job_url(
                    temp_file_path, normalized_file_type
                )

            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except Exception as e:
            logger.error(f"Error starting async extraction: {e}")
            raise

    async def _upload_and_get_job_url(self, file_path: str, file_type: str) -> str:
        """Upload file to Datalab and return request_check_url for polling."""
        logger.info("Starting file upload to Datalab for async extraction")

        headers = {"X-API-Key": self.api_key}

        # Prepare form data based on the API documentation
        data = aiohttp.FormData()

        # Add file
        async with aiofiles.open(file_path, "rb") as f:
            file_content = await f.read()
            data.add_field(
                "file",
                file_content,
                filename=f"document.{file_type}",
                content_type=self._get_content_type(file_type),
            )

        # Add optional parameters for single page processing (for PDF pages)
        data.add_field("max_pages", "1")  # Single page for Temporal workflow
        data.add_field("force_ocr", "false")  # Use built-in text when possible
        data.add_field("paginate", "false")  # Don't add page separators
        data.add_field("output_format", "markdown")  # Get markdown output
        data.add_field("use_llm", "true")  # Use LLM for better accuracy

        async with aiohttp.ClientSession() as session:
            logger.info(f"Sending async request to Datalab API: {self.api_url}")

            async with session.post(
                self.api_url,
                headers=headers,
                data=data,
                timeout=aiohttp.ClientTimeout(
                    total=60
                ),  # Shorter timeout for job start
            ) as response:

                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Datalab API error {response.status}: {error_text}")
                    raise Exception(
                        f"Datalab extraction failed with status {response.status}: {error_text}"
                    )

                # Get the initial response with request_id
                initial_response = await response.json()

                if not initial_response.get("success"):
                    error_msg = initial_response.get("error", "Unknown error")
                    raise Exception(f"Datalab extraction failed: {error_msg}")

                request_check_url = initial_response.get("request_check_url")
                if not request_check_url:
                    raise Exception("Datalab response missing request_check_url")

                logger.info(
                    f"Datalab async extraction initiated. Request ID: {initial_response.get('request_id')}"
                )
                return request_check_url

    def _get_content_type(self, file_type: str) -> str:
        """Get the appropriate content type for the file extension."""
        content_type_map = {
            "pdf": "application/pdf",
        }
        return content_type_map.get(file_type.lower(), "application/octet-stream")

    def _normalize_file_type(self, file_type: str) -> str:
        """Normalize file type from MIME type to extension."""
        file_type_lower = file_type.lower()

        # Remove MIME type prefixes if present
        if file_type_lower.startswith("application/"):
            file_type_lower = file_type_lower.replace("application/", "")
        elif file_type_lower.startswith("text/"):
            file_type_lower = file_type_lower.replace("text/", "")

        # Map common MIME types to extensions
        mime_to_extension = {
            "pdf": "pdf",
            "plain": "txt",
            "markdown": "md",
            "x-markdown": "md",
        }

        return mime_to_extension.get(file_type_lower, file_type_lower)

    def supports_file_type(self, file_type: str) -> bool:
        """Check if the service supports the given file type."""
        normalized_type = self._normalize_file_type(file_type)
        # Datalab only supports PDF files
        return normalized_type == "pdf"
