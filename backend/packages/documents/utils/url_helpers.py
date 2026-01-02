import tempfile
import os
from typing import Optional, Tuple
from urllib.parse import urlparse
import httpx

from common.providers.web_search import get_web_search_provider
from common.core.otel_axiom_exporter import get_logger
from packages.documents.models.domain.document_types import DocumentType

logger = get_logger(__name__)


def generate_filename_from_url(url: str, default_extension: str = ".txt") -> str:
    """Generate a sensible filename from a URL."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace("www.", "")
    path_parts = [p for p in parsed_url.path.split("/") if p]

    if path_parts:
        # If path has a filename with extension, use it
        last_part = path_parts[-1]
        if "." in last_part:
            return last_part
        # Otherwise create one from domain and path
        return f"{domain}_{last_part}{default_extension}"

    return f"{domain}_page{default_extension}"


async def is_binary_url(url: str) -> bool:
    """
    Detect if URL points to a binary file by checking Content-Type header.
    Does a HEAD request to avoid downloading the full content.
    Falls back to extension-based check if HEAD request fails.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.head(url, follow_redirects=True)
            content_type = response.headers.get("content-type", "").lower()

            # Strip charset and other params from content-type
            content_type = content_type.split(";")[0].strip()

            # Check if content type matches any non-text document types
            doc_type = DocumentType.from_mime_type(content_type)
            if doc_type:
                # Check if it's NOT a passthrough text type (txt, markdown)
                is_binary = doc_type.value.extractor_type.value != "passthrough"
                logger.info(
                    f"URL {url} has Content-Type: {content_type}, matched {doc_type.name}, is_binary: {is_binary}"
                )
                return is_binary

            # If no match, check if it's text/html (web page) - use Exa
            if content_type.startswith("text/"):
                logger.info(
                    f"URL {url} has text Content-Type: {content_type}, is_binary: False"
                )
                return False

            # Unknown content type, assume binary to be safe
            logger.info(
                f"URL {url} has unknown Content-Type: {content_type}, assuming binary"
            )
            return True

    except Exception as e:
        logger.warning(
            f"Failed to check Content-Type for {url}: {e}, falling back to extension check"
        )
        # Fallback to extension-based check if HEAD request fails
        doc_type = DocumentType.from_filename(url)
        if doc_type:
            return doc_type.value.extractor_type.value != "passthrough"
        # If can't determine, assume text (use Exa)
        return False


async def fetch_text_content_from_url(url: str) -> str:
    """Fetch text content from URL using web search provider extraction."""
    logger.info(f"Fetching text content from {url}")
    web_search_provider = get_web_search_provider()
    content = await web_search_provider.get_page_content(url)
    logger.info(f"Extracted {len(content)} characters from {url}")
    return content


async def fetch_binary_content_from_url(url: str) -> Tuple[bytes, str]:
    """
    Fetch binary content from URL using httpx.

    Returns:
        Tuple of (content_bytes, content_type)
    """
    logger.info(f"Downloading binary content from {url}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        content_bytes = response.content
        content_type = response.headers.get("content-type", "application/octet-stream")

    logger.info(f"Downloaded {len(content_bytes)} bytes from {url}")
    return content_bytes, content_type


async def create_temp_file_from_url(url: str) -> Optional[Tuple[str, str, str]]:
    """
    Download URL content and create temporary file.

    Returns:
        Tuple of (temp_file_path, filename, content_type) or None on error
    """
    try:
        if await is_binary_url(url):
            content_bytes, content_type = await fetch_binary_content_from_url(url)
            filename = generate_filename_from_url(url, default_extension="")

            with tempfile.NamedTemporaryFile(
                mode="wb", suffix=f"_{filename}", delete=False
            ) as tmp_file:
                tmp_file.write(content_bytes)
                temp_file_path = tmp_file.name

            return temp_file_path, filename, content_type
        else:
            content = await fetch_text_content_from_url(url)
            filename = generate_filename_from_url(url, default_extension=".txt")

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as tmp_file:
                tmp_file.write(content)
                temp_file_path = tmp_file.name

            return temp_file_path, filename, "text/plain"

    except Exception as e:
        logger.error(f"Error creating temp file from URL {url}: {e}")
        return None


def cleanup_temp_file(file_path: str) -> None:
    """Safely clean up a temporary file."""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.debug(f"Cleaned up temp file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to clean up temp file {file_path}: {e}")
