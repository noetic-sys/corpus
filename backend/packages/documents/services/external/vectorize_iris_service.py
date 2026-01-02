import asyncio
import os
import urllib3
import tempfile

from common.core.config import settings
from common.core.otel_axiom_exporter import get_logger

import vectorize_client as v

logger = get_logger(__name__)


class VectorizeIrisService:
    """Service for interacting with Vectorize Iris API for PDF extraction."""

    def __init__(self):
        self.api_client = None
        self.files_api = None
        self.extraction_api = None

    async def _ensure_initialized(self):
        """Ensure the API client is initialized."""
        if self.api_client is None:
            self.api_client = v.ApiClient(
                v.Configuration(access_token=settings.vectorize_api_key)
            )
            self.files_api = v.FilesApi(self.api_client)
            self.extraction_api = v.ExtractionApi(self.api_client)

    async def extract_pdf(self, file_data: bytes) -> str:
        """Extract text content from a PDF using Vectorize Iris."""
        if not self.supports_file_type("pdf"):
            raise ValueError("Only PDF files are supported by Vectorize Iris")

        logger.info("Extracting PDF using Vectorize Iris")
        await self._ensure_initialized()

        try:
            logger.info("Creating temporary file for upload")
            # Create a temporary file for upload
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(file_data)
                temp_file_path = temp_file.name

            try:
                logger.info("Uploading file and starting extraction")
                # Upload file and start extraction
                file_id = await self._upload_file(temp_file_path)
                extraction_id = await self._start_extraction(file_id)

                logger.info(f"Extraction started. Extraction ID: {extraction_id}")
                # Poll for completion and return result
                return await self._poll_extraction_result(extraction_id)

            finally:
                logger.info("Cleaning up temporary file")
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        except Exception as e:
            logger.error(f"Error during PDF extraction: {e}")
            raise

    async def _upload_file(self, file_path: str) -> str:
        """Upload PDF file to Vectorize and return file ID."""
        logger.info("Starting PDF upload to Vectorize Iris")
        logger.info(f"Uploading file to {settings.vectorize_organization_id}")
        start_upload_response = self.files_api.start_file_upload(
            settings.vectorize_organization_id,
            start_file_upload_request=v.StartFileUploadRequest(
                content_type="application/pdf",
                name="document.pdf",
            ),
        )
        logger.info(f"Upload URL: {start_upload_response.upload_url}")
        # Upload the file using urllib3
        http = urllib3.PoolManager()
        file_size = os.path.getsize(file_path)
        logger.info(f"File size: {file_size}")
        with open(file_path, "rb") as f:
            response = http.request(
                "PUT",
                start_upload_response.upload_url,
                body=f,
                headers={
                    "Content-Type": "application/pdf",
                    "Content-Length": str(file_size),
                },
            )
            logger.info(f"Upload response: {response.status}")
            if response.status != 200:
                raise Exception(f"PDF upload failed: {response.data}")

        logger.info(
            f"PDF uploaded successfully. File ID: {start_upload_response.file_id}"
        )
        logger.info(f"File ID: {start_upload_response.file_id}")
        return start_upload_response.file_id

    async def _start_extraction(self, file_id: str) -> str:
        """Start extraction process and return extraction ID."""
        extraction_response = self.extraction_api.start_extraction(
            settings.vectorize_organization_id,
            start_extraction_request=v.StartExtractionRequest(file_id=file_id),
        )

        extraction_id = extraction_response.extraction_id
        logger.info(f"Extraction started. Extraction ID: {extraction_id}")
        return extraction_id

    async def _poll_extraction_result(self, extraction_id: str) -> str:
        """Poll for extraction completion and return the extracted text."""
        max_attempts = 180  # 6 minutes max (2 second intervals)
        attempt = 0

        while attempt < max_attempts:
            logger.info(
                f"Polling for extraction result... (attempt {attempt + 1}/{max_attempts})"
            )
            try:
                result_response = self.extraction_api.get_extraction_result(
                    settings.vectorize_organization_id, extraction_id
                )

                if result_response.ready:
                    if result_response.data.success:
                        logger.info(
                            f"Extraction completed successfully for extraction ID: {extraction_id}"
                        )
                        return result_response.data.text
                    else:
                        error_msg = f"Extraction failed: {result_response.data.error}"
                        logger.error(error_msg)
                        raise Exception(error_msg)

                logger.debug(
                    f"Extraction in progress... (attempt {attempt + 1}/{max_attempts})"
                )
                await asyncio.sleep(2)
                attempt += 1

            except Exception as e:
                if attempt >= max_attempts - 1:
                    raise
                logger.warning(
                    f"Error checking extraction status (attempt {attempt + 1}): {e}"
                )
                await asyncio.sleep(2)
                attempt += 1

        raise Exception(f"Extraction timed out after {max_attempts * 2} seconds")

    def supports_file_type(self, file_type: str) -> bool:
        """Check if the service supports the given file type. Only PDF is supported."""
        return file_type.lower() == "pdf"
