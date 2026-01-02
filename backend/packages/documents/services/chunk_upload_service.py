"""
Service for processing chunk uploads from chunking agents.

Handles receiving chunks from agents and uploading to S3 and creating DB records.
"""

import io
import json
from typing import List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from common.providers.storage.factory import get_storage
from common.providers.storage.paths import get_document_chunks_prefix
from common.core.otel_axiom_exporter import trace_span, get_logger
from packages.documents.models.schemas.chunk import ChunkUploadItem
from packages.documents.services.chunk_set_service import ChunkSetService
from packages.documents.services.chunk_service import ChunkService
from packages.documents.models.domain.chunk_set import ChunkSetCreateModel
from packages.documents.models.domain.chunk import ChunkCreateModel
from packages.documents.models.domain.chunking_strategy import ChunkingStrategy

logger = get_logger(__name__)


class ChunkUploadService:
    """Service for processing chunk uploads from chunking agents."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.storage = get_storage()
        self.chunk_set_service = ChunkSetService(db_session)
        self.chunk_service = ChunkService(db_session)

    @trace_span
    async def process_chunk_upload(
        self,
        document_id: int,
        company_id: int,
        chunks: List[ChunkUploadItem],
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.AGENTIC,
    ) -> str:
        """
        Process chunk upload from chunking agent or naive chunking.

        Uploads all chunks and manifest to S3 and creates database records.

        Args:
            document_id: Document ID
            company_id: Company ID
            chunks: List of chunks to upload
            chunking_strategy: Strategy used for chunking

        Returns:
            S3 prefix where chunks are stored

        Raises:
            Exception: If upload fails
        """
        s3_prefix = get_document_chunks_prefix(company_id, document_id)

        logger.info(
            f"Uploading {len(chunks)} chunks for document {document_id} to {s3_prefix}"
        )

        # Upload each chunk to S3
        for chunk in chunks:
            # Upload chunk content
            chunk_key = f"{s3_prefix}/{chunk.chunk_id}.md"
            await self.storage.upload(
                chunk_key,
                io.BytesIO(chunk.content.encode("utf-8")),
                metadata={"content_type": "text/markdown"},
            )

            # Upload chunk metadata
            meta_key = f"{s3_prefix}/{chunk.chunk_id}.meta.json"
            meta_json = json.dumps(chunk.metadata)
            await self.storage.upload(
                meta_key,
                io.BytesIO(meta_json.encode("utf-8")),
                metadata={"content_type": "application/json"},
            )

        # Create and upload manifest
        manifest_data = {
            "document_id": document_id,
            "created_at": datetime.utcnow().isoformat(),
            "total_chunks": len(chunks),
            "chunks": [
                {"chunk_id": chunk.chunk_id, "metadata": chunk.metadata}
                for chunk in chunks
            ],
        }

        manifest_key = f"{s3_prefix}/manifest.json"
        manifest_json = json.dumps(manifest_data, indent=2)
        await self.storage.upload(
            manifest_key,
            io.BytesIO(manifest_json.encode("utf-8")),
            metadata={"content_type": "application/json"},
        )

        logger.info(f"Successfully uploaded {len(chunks)} chunks and manifest to S3")

        # Create chunk_set in database
        chunk_set = await self.chunk_set_service.create_chunk_set(
            ChunkSetCreateModel(
                document_id=document_id,
                company_id=company_id,
                chunking_strategy=chunking_strategy.value,
                total_chunks=len(chunks),
                s3_prefix=s3_prefix,
            )
        )

        logger.info(f"Created chunk set {chunk_set.id} for document {document_id}")

        # Create chunk records in database
        chunk_models = []
        for idx, chunk in enumerate(chunks):
            chunk_key = f"{s3_prefix}/{chunk.chunk_id}.md"
            chunk_model = await self.chunk_service.create_chunk(
                ChunkCreateModel(
                    chunk_set_id=chunk_set.id,
                    chunk_id=chunk.chunk_id,
                    document_id=document_id,
                    company_id=company_id,
                    s3_key=chunk_key,
                    chunk_metadata=chunk.metadata,
                    chunk_order=idx,
                )
            )
            chunk_models.append(chunk_model)

        logger.info(
            f"Created {len(chunk_models)} chunk records in database for document {document_id}"
        )

        return s3_prefix


def get_chunk_upload_service(db_session: AsyncSession) -> ChunkUploadService:
    """Get chunk upload service instance."""
    return ChunkUploadService(db_session)
