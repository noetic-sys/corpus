"""
Fetch full document content for citation validation.
"""

import asyncio
import logging
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


def _fetch_document_content_sync(api_endpoint: str, api_key: str, doc_id: int) -> str:
    """Synchronous document content fetching (runs in thread). Raises on failure."""
    # Use the /documents/{documentId}/content endpoint that returns {"content": "..."}
    url = f"{api_endpoint}/api/v1/documents/{doc_id}/content"
    headers = {"X-API-Key": api_key}

    logger.info(f"Fetching extracted content from {url}")

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    # Parse JSON response and extract content field
    data = response.json()
    extracted_text = data.get("content")

    if not extracted_text:
        raise ValueError(f"Document {doc_id} has no content field in response")

    logger.info(
        f"Fetched full content for document {doc_id} ({len(extracted_text)} chars)"
    )
    return extracted_text


async def fetch_document_chunks(
    api_endpoint: str,
    api_key: str,
    document_ids: List[int],
) -> Dict[int, str]:
    """
    Fetch full content for given documents.

    Runs synchronous requests in thread pool to avoid blocking event loop.

    Args:
        api_endpoint: API base URL
        api_key: Service account API key
        document_ids: List of document IDs to fetch content for

    Returns:
        Dict mapping document_id -> full_document_content

    Raises:
        Exception if any document fails to fetch
    """
    documents_content = {}

    logger.info(
        f"Fetching content for {len(document_ids)} documents from {api_endpoint}"
    )

    # Fetch each document's content in thread pool
    for doc_id in document_ids:
        try:
            logger.info(f"Fetching document {doc_id}...")
            content = await asyncio.to_thread(
                _fetch_document_content_sync, api_endpoint, api_key, doc_id
            )
            documents_content[doc_id] = content
            logger.info(
                f"Successfully fetched document {doc_id} ({len(content)} chars)"
            )
        except Exception as e:
            logger.error(f"Failed to fetch document {doc_id}: {e}")
            raise

    logger.info(
        f"Loaded content for {len(documents_content)}/{len(document_ids)} documents"
    )
    return documents_content
