"""
Chunk uploader for document chunking execution.

Uploads chunks directly via API after agent completes chunking.
"""

import json
import os
from typing import Any, Dict, List

import requests
from documents.chunk import ChunkManifest


def load_chunks_from_temp_dir(temp_dir: str) -> tuple[List[Dict[str, Any]], int]:
    """
    Load chunks from temporary directory after agent execution.

    Args:
        temp_dir: Temporary directory containing chunks and manifest

    Returns:
        Tuple of (list of chunk dicts, document_id)

    Raises:
        FileNotFoundError: If manifest.json not found
    """
    manifest_path = os.path.join(temp_dir, "manifest.json")

    if not os.path.exists(manifest_path):
        raise FileNotFoundError(
            f"No manifest found at {manifest_path}. Chunking may have failed."
        )

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    manifest = ChunkManifest(**manifest_data)

    chunks = []
    for chunk_info in manifest.chunks:
        chunk_id = chunk_info.chunk_id
        chunk_path = os.path.join(temp_dir, f"{chunk_id}.md")
        meta_path = os.path.join(temp_dir, f"{chunk_id}.meta.json")

        if not os.path.exists(chunk_path):
            print(f"WARNING: Chunk file not found: {chunk_path}")
            continue

        with open(chunk_path, "r", encoding="utf-8") as f:
            content = f.read()

        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        chunks.append({"chunk_id": chunk_id, "content": content, "metadata": metadata})

    return chunks, manifest.document_id


def upload_chunks(
    api_endpoint: str,
    document_id: int,
    company_id: int,
    chunks: List[Dict[str, Any]],
    api_key: str,
) -> None:
    """
    Upload chunks to API (API handles S3 storage).

    Args:
        api_endpoint: API base URL
        document_id: Document ID
        company_id: Company ID
        chunks: List of chunk dictionaries
        api_key: API key for authentication

    Raises:
        requests.HTTPError: If API request fails
    """
    url = f"{api_endpoint}/api/v1/documents/{document_id}/chunks"

    payload = {"document_id": document_id, "company_id": company_id, "chunks": chunks}

    headers = {"X-Api-Key": api_key, "Content-Type": "application/json"}

    print(f"Uploading {len(chunks)} chunks to API...")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()

        print(f"✓ Successfully uploaded {len(chunks)} chunks")

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to upload chunks: {e}")
        raise
