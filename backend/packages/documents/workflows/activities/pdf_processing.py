from typing import List

from temporalio import activity

from common.core.otel_axiom_exporter import create_span_with_context, get_logger
from common.core.config import settings
from common.db.session import get_db
from packages.documents.services.pdf_service import PdfService
from packages.documents.services.document_service import get_document_service

logger = get_logger(__name__)


@activity.defn
async def split_pdf_activity(document_id: int, trace_headers: dict = None) -> List[str]:
    """
    Split PDF into individual page URLs.
    Downloads the PDF, splits it into individual pages, uploads each page to S3,
    and returns URLs for each page.
    """
    with create_span_with_context("temporal::split_pdf_activity", trace_headers):
        # Get document from database (minimal session usage)
        document = None
        async for db_session in get_db():
            document_service = get_document_service(db_session)
            document = await document_service.get_document(document_id)
            break

        if not document:
            raise ValueError(f"Document {document_id} not found")

        pdf_service = PdfService()
        return await pdf_service.split_pdf(
            document.storage_key, settings.pdf_page_split_size
        )


@activity.defn
async def convert_page_to_markdown_activity(
    page_url: str, trace_headers: dict = None
) -> str:
    """
    Convert PDF page to markdown using Gemini (synchronous).
    Returns markdown content directly.
    """
    with create_span_with_context(
        "temporal::convert_page_to_markdown_activity", trace_headers
    ):
        pdf_service = PdfService()
        return await pdf_service.convert_page_to_markdown(page_url)
