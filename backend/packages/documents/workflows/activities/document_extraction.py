"""
Generic document extraction activities for all file types.
Uses the existing document extraction providers.
"""

import io

from temporalio import activity

from common.core.otel_axiom_exporter import create_span_with_context, get_logger
from common.providers.storage.factory import get_storage
from common.providers.storage.paths import get_document_extracted_path
from packages.documents.providers.document_extraction.extractor_factory import (
    ExtractorFactory,
)
from packages.documents.providers.document_search.factory import (
    get_document_search_provider,
)
from packages.documents.repositories.document_repository import DocumentRepository
from packages.documents.models.domain.document import DocumentModel
from packages.documents.services.document_service import get_document_service

logger = get_logger(__name__)


@activity.defn
async def extract_document_content_activity(
    document_id: int, trace_headers: dict = None
) -> str:
    """
    Extract content from any supported document type using appropriate extractor.
    Returns extracted content as markdown/text.
    """
    with create_span_with_context(
        "temporal::extract_document_content_activity", trace_headers
    ):
        logger.info(f"Extracting content from document {document_id}")

        try:
            document_service = get_document_service()
            document = await document_service.get_document(document_id)

            if not document:
                raise ValueError(f"Document {document_id} not found in database")

            logger.info(
                f"Extracting content from {document.content_type} document: {document.storage_key}"
            )
            file_type = document_service.get_file_type_from_document(document)

            # Get appropriate extractor for this file type
            extractor = ExtractorFactory.get_extractor(file_type or "")
            logger.info(
                f"Using {extractor.__class__.__name__} for {document.content_type} extraction"
            )

            # Extract content using the appropriate extractor
            extracted_content = await extractor.extract_text(document)

            logger.info(
                f"Successfully extracted content ({len(extracted_content)} characters)"
            )
            return extracted_content

        except Exception as e:
            logger.error(f"Error extracting document content: {e}")
            raise


@activity.defn
async def save_extracted_content_to_s3_activity(
    content: str, document_id: int, trace_headers: dict = None
) -> str:
    """Save extracted content to S3 and return the S3 key."""
    with create_span_with_context(
        "temporal::save_extracted_content_to_s3_activity", trace_headers
    ):
        logger.info(f"Saving extracted content for document {document_id}")

        storage_provider = get_storage()

        try:
            # Get company_id from document for path organization
            document_repo = DocumentRepository()
            document = await document_repo.get(document_id)

            if not document:
                raise ValueError(f"Document {document_id} not found in database")

            company_id = document.company_id

            # Generate S3 key with filesystem locality using centralized path utility
            s3_key = get_document_extracted_path(company_id, document_id)

            # Convert to bytes and upload
            content_bytes = content.encode("utf-8")
            success = await storage_provider.upload(
                s3_key,
                io.BytesIO(content_bytes),
                metadata={"content_type": "text/markdown"},
            )

            if not success:
                raise Exception("Failed to upload extracted content to S3")

            logger.info(f"Extracted content saved to S3: {s3_key}")
            return s3_key

        except Exception as e:
            logger.error(f"Error saving extracted content to S3: {e}")
            raise


@activity.defn
async def index_document_for_search_activity(
    document_id: int, extracted_content: str, trace_headers: dict = None
) -> bool:
    """Index document with extracted content in the search provider."""
    with create_span_with_context(
        "temporal::index_document_for_search_activity", trace_headers
    ):
        logger.info(
            f"Indexing document {document_id} for search with extracted content"
        )

        try:
            document_repo = DocumentRepository()
            document = await document_repo.get(document_id)

            if not document:
                raise ValueError(f"Document {document_id} not found in database")

            # Convert database entity to domain model
            document_model = DocumentModel.model_validate(document)

            # Get search provider and index
            search_provider = get_document_search_provider()
            success = await search_provider.index_document(
                document_model, extracted_content
            )

            if success:
                logger.info(f"Successfully indexed document {document_id} for search")
                return True
            else:
                logger.warning(f"Failed to index document {document_id} for search")
                return False

        except Exception as e:
            logger.error(f"Error indexing document {document_id} for search: {e}")
            # Don't raise - we don't want indexing failures to fail the entire extraction workflow
            return False
