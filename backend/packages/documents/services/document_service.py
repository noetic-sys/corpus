import asyncio
import hashlib
import os
from typing import List, Optional, Tuple, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile, HTTPException

from common.providers.storage.factory import get_storage
from common.providers.bloom_filter.factory import get_bloom_filter_provider
from packages.documents.providers.document_search.factory import (
    get_document_search_provider,
)
from packages.documents.providers.document_search.interface import (
    DocumentSearchFilters,
    DocumentSearchResult,
)
from packages.documents.repositories.document_repository import DocumentRepository
from packages.documents.models.domain.document import DocumentModel, DocumentCreateModel
from packages.documents.models.domain.document_types import DocumentType
from packages.documents.models.database.document import ExtractionStatus
from packages.documents.services.document_indexing_job_service import (
    DocumentIndexingJobService,
)
from packages.documents.utils.url_helpers import (
    create_temp_file_from_url,
    cleanup_temp_file,
)
from packages.documents.services.chunk_search_service import get_chunk_search_service
from packages.documents.providers.document_search.types import ChunkSearchFilters
from packages.documents.models.domain.document_search import (
    HybridDocumentSearchResult,
    DocumentSearchHit,
    DocumentMatchSnippet,
    DocumentMatchData,
    MatchType,
)
from packages.billing.services.quota_service import QuotaService
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class DocumentService:
    """Service for handling document operations."""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.document_repo = DocumentRepository(db_session)
        self.storage = get_storage()
        self.bloom_filter = get_bloom_filter_provider()
        self.search_provider = get_document_search_provider(db_session)
        self.indexing_job_service = DocumentIndexingJobService()

    async def _calculate_checksum_from_stream(self, file: UploadFile) -> str:
        """Calculate SHA256 checksum of file content using streaming."""
        sha256_hash = hashlib.sha256()
        chunk_size = 8192  # 8KB chunks

        while chunk := await file.read(chunk_size):
            sha256_hash.update(chunk)

        await file.seek(0)  # Reset file pointer
        return sha256_hash.hexdigest()

    @trace_span
    async def _check_for_duplicate(
        self, checksum: str, company_id: int
    ) -> Optional[DocumentModel]:
        """Check if document with this checksum already exists within the company."""
        # First check bloom filter for fast negative lookup
        filter_name = f"document_checksums_{company_id}"
        might_exist = await self.bloom_filter.exists(filter_name, checksum)

        if not might_exist:
            # Definitely doesn't exist
            logger.debug(
                f"Bloom filter confirms checksum {checksum} is new for company {company_id}"
            )
            return None

        # Might exist, check database
        existing_doc = await self.document_repo.get_by_checksum(checksum, company_id)
        if existing_doc:
            logger.info(
                f"Found duplicate document with checksum {checksum}: {existing_doc.id} in company {company_id}"
            )
            return existing_doc

        logger.debug(
            f"Bloom filter false positive for checksum {checksum} in company {company_id}"
        )
        return None

    @trace_span
    async def upload_document(
        self, file: UploadFile, company_id: int
    ) -> Tuple[DocumentModel, bool]:
        """
        Upload a document as a standalone entity within a company.

        Returns:
            Tuple of (document, is_duplicate) where is_duplicate indicates if this was a duplicate
        """
        logger.info(f"Uploading document {file.filename} for company {company_id}")

        # Calculate checksum using streaming to handle large files
        checksum = await self._calculate_checksum_from_stream(file)
        logger.info(f"Calculated checksum for {file.filename}: {checksum}")

        # Check for duplicates within the company
        existing_doc = await self._check_for_duplicate(checksum, company_id)
        if existing_doc:
            logger.info(
                f"Document {file.filename} is a duplicate of existing document {existing_doc.id} in company {company_id}"
            )
            return existing_doc, True

        # Upload to storage with company prefix
        # TODO: change this for an malicious filenames
        storage_key = f"documents/company_{company_id}/{file.filename}"

        success = await self.storage.upload(
            storage_key,
            file.file,
            {
                "filename": file.filename,
                "content_type": file.content_type or "application/octet-stream",
            },
        )

        if not success:
            raise HTTPException(status_code=500, detail="Failed to upload file")

        # Create document record
        document_create = DocumentCreateModel(
            filename=file.filename,
            storage_key=storage_key,
            content_type=file.content_type,
            file_size=file.size,
            checksum=checksum,
            company_id=company_id,
            extraction_status=ExtractionStatus.PENDING,
        )
        document = await self.document_repo.create(document_create)

        logger.info(f"Created document with ID: {document.id} for company {company_id}")

        # Add checksum to company-specific bloom filter
        filter_name = f"document_checksums_{company_id}"
        await self.bloom_filter.add(filter_name, checksum)
        logger.debug(
            f"Added checksum {checksum} to bloom filter for company {company_id}"
        )

        # IMPORTANT: Commit the document before queueing extraction and indexing
        # so the workers can see it when processing the messages
        await self.db_session.commit()
        logger.info(
            "Committed document to database before queueing extraction and indexing"
        )

        # Queue document for async indexing instead of synchronous indexing
        try:
            indexing_job = await self.indexing_job_service.create_and_queue_job(
                document.id
            )
            if indexing_job:
                logger.info(
                    f"Queued document {document.id} for async indexing (job {indexing_job.id})"
                )
            else:
                logger.warning(f"Failed to queue document {document.id} for indexing")
            # Don't fail the upload if indexing queue fails
        except Exception as e:
            logger.warning(f"Failed to queue document {document.id} for indexing: {e}")
            # Don't fail the upload if indexing queue fails

        return document, False

    @trace_span
    async def get_document(
        self, document_id: int, company_id: Optional[int] = None
    ) -> Optional[DocumentModel]:
        """Get a document by ID with company access control."""
        return await self.document_repo.get(document_id, company_id)

    @trace_span
    async def get_documents_by_ids(
        self, document_ids: List[int], company_id: Optional[int] = None
    ) -> List[DocumentModel]:
        """Get multiple documents by their IDs with company access control."""
        if not document_ids:
            return []

        documents = await self.document_repo.get_by_ids(document_ids, company_id)
        logger.info(
            f"Retrieved {len(documents)} documents out of {len(document_ids)} requested for company {company_id}"
        )
        return documents

    @trace_span
    async def delete_document(self, document_id: int, company_id: int) -> bool:
        """Delete a document and remove from storage with company access control."""
        document = await self.get_document(document_id, company_id)
        if not document:
            return False

        # Delete from storage
        await self.storage.delete(document.storage_key)

        # Delete from search index
        try:
            await self.search_provider.delete_document_from_index(document.id)
            logger.info(f"Removed document {document_id} from search index")
        except Exception as e:
            logger.warning(
                f"Failed to remove document {document_id} from search index: {e}"
            )
            # Continue with database deletion even if search index deletion fails

        # Delete from database (cascade will handle matrix_cells)
        await self.document_repo.delete(document.id, company_id)

        logger.info(f"Deleted document {document_id} for company {company_id}")
        return True

    @trace_span
    async def get_extracted_content(self, document: DocumentModel) -> Optional[str]:
        """Get extracted content for a document, downloading from S3 if available."""
        if not document.extracted_content_path:
            logger.warning(f"Document {document.id} has no extracted content path")
            return None

        if document.extraction_status != ExtractionStatus.COMPLETED:
            logger.warning(
                f"Document {document.id} extraction not completed (status: {document.extraction_status})"
            )
            return None

        try:
            # Download extracted content from S3
            content_bytes = await self.storage.download(document.extracted_content_path)
            if not content_bytes:
                logger.error(
                    f"Failed to download extracted content from {document.extracted_content_path}"
                )
                return None

            # Decode bytes to string
            content = content_bytes.decode("utf-8")
            logger.info(f"Downloaded {len(content)} characters of extracted content")
            return content

        except Exception as e:
            logger.error(
                f"Error getting extracted content for document {document.id}: {e}"
            )
            return None

    @trace_span
    async def search_documents(
        self,
        company_id: int,
        query: Optional[str] = None,
        content_type: Optional[str] = None,
        extraction_status: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> DocumentSearchResult:
        """Search documents using the configured search provider with company filtering."""
        filters = DocumentSearchFilters(
            company_id=company_id,
            content_type=content_type,
            extraction_status=extraction_status,
            created_after=created_after,
            created_before=created_before,
        )

        return await self.search_provider.search_documents(
            query=query, filters=filters, skip=skip, limit=limit
        )

    @trace_span
    async def list_all_documents(
        self,
        company_id: int,
        content_type: Optional[str] = None,
        extraction_status: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> DocumentSearchResult:
        """List all documents using the configured search provider with company filtering."""
        filters = DocumentSearchFilters(
            company_id=company_id,
            content_type=content_type,
            extraction_status=extraction_status,
            created_after=created_after,
            created_before=created_before,
        )

        return await self.search_provider.list_documents(
            filters=filters, skip=skip, limit=limit
        )

    @trace_span
    async def get_document_content(self, document: DocumentModel) -> Optional[bytes]:
        """Get original document content as bytes from storage."""
        try:
            content_bytes = await self.storage.download(document.storage_key)
            if not content_bytes:
                logger.error(
                    f"Failed to download document content from {document.storage_key}"
                )
                return None

            logger.info(f"Downloaded {len(content_bytes)} bytes of document content")
            return content_bytes

        except Exception as e:
            logger.error(
                f"Error getting document content for document {document.id}: {e}"
            )
            return None

    @staticmethod
    def get_supported_file_extensions() -> List[str]:
        """Get all supported file extensions for document uploads."""
        return DocumentType.get_all_extensions()

    @staticmethod
    def get_file_type_from_document(document: DocumentModel) -> str:
        """Extract file type from document for extractor routing."""
        # Try to find by MIME type first
        if document.content_type:
            doc_type = DocumentType.from_mime_type(document.content_type)
            if doc_type and doc_type.value.extensions:
                return doc_type.value.extensions[0][1:]  # Remove the dot

        # Fallback to filename extension
        if document.filename:
            doc_type = DocumentType.from_filename(document.filename)
            if doc_type and doc_type.value.extensions:
                return doc_type.value.extensions[0][1:]  # Remove the dot
            # Legacy fallback
            return document.filename.split(".")[-1].lower()

        return "unknown"

    @trace_span
    async def get_extraction_stats_for_document_ids(
        self, document_ids: List[int], company_id: Optional[int] = None
    ):
        """Get extraction statistics for a list of document IDs."""
        return await self.document_repo.get_extraction_stats_by_document_ids(
            document_ids, company_id
        )

    @trace_span
    async def upload_documents_from_urls(
        self, urls: List[str], company_id: int
    ) -> Tuple[List[DocumentModel], List[str]]:
        """
        Upload multiple documents from URLs in parallel.

        Returns:
            Tuple of (successful_documents, error_messages)
        """
        logger.info(f"Starting bulk URL upload for {len(urls)} URLs")

        # Download all URLs in parallel OUTSIDE transaction
        download_results = await asyncio.gather(
            *[create_temp_file_from_url(url) for url in urls], return_exceptions=True
        )

        # Process results and upload to storage
        documents = []
        errors = []

        for i, result in enumerate(download_results):
            url = urls[i]

            if isinstance(result, Exception):
                errors.append(f"Failed to download {url}: {str(result)}")
                continue

            if result is None:
                errors.append(f"Failed to download {url}")
                continue

            temp_file_path, filename, content_type = result

            try:
                document = await self._upload_from_temp_file(
                    temp_file_path, filename, content_type, company_id
                )
                documents.append(document)

            except Exception as e:
                logger.error(f"Error uploading document from {url}: {e}")
                errors.append(f"Failed to upload {url}: {str(e)}")

            finally:
                cleanup_temp_file(temp_file_path)

        logger.info(
            f"Bulk upload complete: {len(documents)} documents, {len(errors)} errors"
        )
        return documents, errors

    async def _upload_from_temp_file(
        self, temp_file_path: str, filename: str, content_type: str, company_id: int
    ) -> DocumentModel:
        """Upload a document from a temporary file."""
        file_size = os.path.getsize(temp_file_path)

        # Check storage quota with actual file size before uploading
        quota_service = QuotaService(self.db_session)
        quota_check = await quota_service.check_storage_quota(
            company_id=company_id,
            file_size_bytes=file_size,
        )
        if not quota_check.allowed:
            raise HTTPException(status_code=402, detail=quota_check.get_user_message())

        with open(temp_file_path, "rb") as f:
            upload_file = UploadFile(
                filename=filename,
                file=f,
                headers={"content-type": content_type},
            )
            upload_file.size = file_size

            document, _ = await self.upload_document(upload_file, company_id)
            return document

    @trace_span
    async def hybrid_search_documents(
        self,
        company_id: int,
        query: str,
        skip: int = 0,
        limit: int = 20,
        snippets_per_doc: int = 3,
    ) -> HybridDocumentSearchResult:
        """Search documents using hybrid: filename + chunk content (BM25 + vector)."""
        # Run chunk search and filename search in parallel
        chunk_task = self._search_chunks_for_documents(
            company_id, query, limit, snippets_per_doc
        )
        filename_task = self.search_documents(
            company_id=company_id, query=query, skip=0, limit=limit * 2
        )

        chunk_matches, filename_result = await asyncio.gather(chunk_task, filename_task)

        # Merge results
        merged = self._merge_filename_and_chunk_matches(
            chunk_matches, filename_result.documents
        )

        # Fetch documents for chunk-only matches
        missing_doc_ids = [m.document_id for m in merged.values() if m.document is None]
        if missing_doc_ids:
            missing_docs = await self.get_documents_by_ids(missing_doc_ids, company_id)
            doc_map = {doc.id: doc for doc in missing_docs}
            for match in merged.values():
                if match.document is None and match.document_id in doc_map:
                    match.document = doc_map[match.document_id]

        # Sort and paginate
        sorted_hits = sorted(merged.values(), key=lambda m: m.best_score, reverse=True)
        paginated = sorted_hits[skip : skip + limit]

        # Convert to final hits
        final_results = [
            DocumentSearchHit(
                document=match.document,
                match_score=match.best_score,
                match_type=match.match_type,
                snippets=match.snippets,
            )
            for match in paginated
            if match.document
        ]

        return HybridDocumentSearchResult(
            results=final_results,
            total_count=len(sorted_hits),
            has_more=skip + limit < len(sorted_hits),
        )

    async def _search_chunks_for_documents(
        self, company_id: int, query: str, limit: int, snippets_per_doc: int
    ) -> Dict[int, DocumentMatchData]:
        """Search chunks and group by document."""
        chunk_search_service = get_chunk_search_service(self.db_session)
        filters = ChunkSearchFilters(company_id=company_id)

        result = await chunk_search_service.hybrid_search_chunks(
            query=query, filters=filters, skip=0, limit=limit * 10, use_vector=True
        )

        # Group by document
        doc_matches: Dict[int, DocumentMatchData] = {}
        for chunk in result.chunks:
            if chunk.document_id not in doc_matches:
                doc_matches[chunk.document_id] = DocumentMatchData(
                    document_id=chunk.document_id,
                    best_score=chunk.score,
                    match_type=MatchType.HYBRID,
                    snippets=[],
                )

            match_data = doc_matches[chunk.document_id]
            if len(match_data.snippets) < snippets_per_doc:
                snippet = DocumentMatchSnippet(
                    chunk_id=chunk.chunk_id,
                    content=chunk.content[:300],
                    score=chunk.score,
                    metadata=chunk.metadata,
                )
                match_data.snippets.append(snippet)

        return doc_matches

    def _merge_filename_and_chunk_matches(
        self,
        chunk_matches: Dict[int, DocumentMatchData],
        filename_docs: List[DocumentModel],
    ) -> Dict[int, DocumentMatchData]:
        """Merge filename matches with chunk matches."""
        # Add filename matches
        for doc in filename_docs:
            if doc.id not in chunk_matches:
                chunk_matches[doc.id] = DocumentMatchData(
                    document_id=doc.id,
                    best_score=1.0,
                    match_type=MatchType.FILENAME,
                    snippets=[],
                    document=doc,
                )
            else:
                # Boost score and update type
                match_data = chunk_matches[doc.id]
                match_data.best_score *= 1.5
                match_data.match_type = MatchType.FILENAME_AND_CONTENT
                match_data.document = doc

        return chunk_matches


def get_document_service(db_session: AsyncSession) -> DocumentService:
    """Get document service instance."""
    return DocumentService(db_session)
