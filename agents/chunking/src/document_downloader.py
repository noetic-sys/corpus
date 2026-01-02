"""
Document content downloader for chunking execution.

Downloads document content from API before agent execution.
"""

import requests


def download_document_content(api_endpoint: str, document_id: int, api_key: str) -> str:
    """
    Download document content from API.

    Args:
        api_endpoint: API base URL
        document_id: Document ID
        api_key: API key for authentication

    Returns:
        Document content string

    Raises:
        requests.HTTPError: If API request fails
    """
    url = f"{api_endpoint}/api/v1/documents/{document_id}/content"
    headers = {"X-Api-Key": api_key}

    print(f"Downloading document {document_id} content from API...")

    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        content = data.get("content")
        if not content:
            raise ValueError(f"No content returned for document {document_id}")

        print(f"Downloaded document content ({len(content)} chars)")
        return content

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to download document content: {e}")
        raise
