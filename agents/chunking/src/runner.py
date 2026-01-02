"""
Document Chunker Runner

Entry point for document chunking in isolated containers.
"""

import asyncio
import os
import shutil
import sys
import tempfile
from pathlib import Path

from agent_executor import execute_chunking_agent
from chunk_uploader import (
    load_chunks_from_temp_dir,
    upload_chunks,
)
from document_downloader import download_document_content
from env_validator import (
    cleanup_sensitive_env_vars,
    validate_environment,
)
from chunking_strategy import decide_chunking_strategy
from pageindex_chunker import chunk_with_pageindex


async def main():
    """Main entry point for document chunking."""
    # Validate environment
    try:
        document_id, company_id, api_endpoint, api_key = validate_environment()
        print(f"Starting document chunking for document {document_id}")
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Download document content from API
    try:
        document_content = download_document_content(api_endpoint, document_id, api_key)
    except Exception as e:
        print(f"ERROR: Failed to download document content: {e}")
        sys.exit(1)

    # Create temporary directory for chunking
    temp_dir = tempfile.mkdtemp(prefix=f"chunks_{document_id}_")
    try:
        # Write document to temp file
        doc_path = os.path.join(temp_dir, "original.txt")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(document_content)
        print(f"Saved document to {doc_path} ({len(document_content)} chars)")

        # Decide chunking strategy based on document structure
        decision = decide_chunking_strategy(Path(doc_path))
        print(f"\nChunking Strategy: {decision.strategy_name}")
        print(f"Reason: {decision.reason}")
        print(f"Document stats: {decision.stats.total_headers} headers, levels {decision.stats.header_levels}\n")

        # Clear sensitive environment variables before agent execution
        cleanup_sensitive_env_vars()

        # Run appropriate chunking strategy
        try:
            if decision.use_pageindex:
                # Use PageIndex-enhanced chunking
                print("Using PageIndex-enhanced chunking...")
                await chunk_with_pageindex(
                    document_path=Path(doc_path),
                    document_id=document_id,
                    output_dir=Path(temp_dir)
                )
            else:
                # Use semantic chunking with Claude agent
                print("Using semantic chunking with Claude agent...")
                result_message = await execute_chunking_agent(
                    document_id, doc_path, temp_dir
                )

                if result_message and result_message.is_error:
                    print("ERROR: Chunking agent failed (is_error=True)")
                    sys.exit(1)
        except Exception as e:
            print(f"ERROR: Chunking failed: {e}")
            sys.exit(1)

        # Load chunks from temp directory
        try:
            chunks, manifest_doc_id = load_chunks_from_temp_dir(temp_dir)
            print(f"Loaded {len(chunks)} chunks from temp directory")

            if manifest_doc_id != document_id:
                print(
                    f"WARNING: Manifest document_id ({manifest_doc_id}) doesn't match expected ({document_id})"
                )
        except Exception as e:
            print(f"ERROR: Failed to load chunks: {e}")
            sys.exit(1)

        # Upload chunks to API (api_key still in scope, not in env)
        try:
            upload_chunks(api_endpoint, document_id, company_id, chunks, api_key)
        except Exception as e:
            print(f"ERROR: Failed to upload chunks to API: {e}")
            sys.exit(1)

    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("Cleaned up temporary directory")

    print("Document chunking completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
