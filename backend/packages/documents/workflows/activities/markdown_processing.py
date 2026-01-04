import io
from typing import List

from temporalio import activity

from common.core.otel_axiom_exporter import create_span_with_context, get_logger
from common.db.session import get_db
from common.providers.storage.factory import get_storage
from common.providers.storage.paths import get_document_extracted_path
from packages.documents.workflows.common import MarkdownPage
from packages.documents.repositories.document_repository import DocumentRepository

logger = get_logger(__name__)


@activity.defn
async def combine_markdown_activity(
    pages: List[MarkdownPage], trace_headers: dict = None
) -> str:
    """Combine all markdown pages in order."""
    with create_span_with_context("temporal::combine_markdown_activity", trace_headers):
        combined = "\n\n---\n\n".join(page.content for page in pages)
        return combined


@activity.defn
async def save_markdown_to_s3_activity(
    markdown_content: str, document_id: int, trace_headers: dict = None
) -> str:
    """Save combined markdown content to S3 and return the S3 key."""
    with create_span_with_context(
        "temporal::save_markdown_to_s3_activity", trace_headers
    ):
        logger.info(f"Saving markdown content for document {document_id}")

        storage_provider = get_storage()

        try:
            # Get company_id from document for centralized path
            async for session in get_db():
                document_repo = DocumentRepository()
                document = await document_repo.get(document_id)

                if not document:
                    raise ValueError(f"Document {document_id} not found in database")

                company_id = document.company_id

            # Use centralized path utility
            s3_key = get_document_extracted_path(company_id, document_id)

            # Convert to bytes and upload
            markdown_bytes = markdown_content.encode("utf-8")
            success = await storage_provider.upload(
                s3_key,
                io.BytesIO(markdown_bytes),
                metadata={"content_type": "text/markdown"},
            )

            if not success:
                raise Exception("Failed to upload markdown to S3")

            logger.info(f"Markdown content saved to S3: {s3_key}")
            return s3_key

        except Exception as e:
            logger.error(f"Error saving markdown to S3: {e}")
            raise
