import io
from typing import List
from PyPDF2 import PdfReader, PdfWriter
from markitdown import MarkItDown
from markitdown._stream_info import StreamInfo

from common.core.config import settings
from common.providers.storage.factory import get_storage
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class PdfService:
    def __init__(self):
        self.storage_provider = get_storage()
        self.markitdown = MarkItDown(enable_plugins=True)

    @trace_span
    async def split_pdf(self, storage_key: str, pages_per_split: int = 1) -> List[str]:
        """
        Split PDF into chunks with specified number of pages per split.
        Downloads the PDF, splits it into chunks, uploads each chunk to S3,
        and returns URLs for each chunk.
        """
        logger.info(
            f"Starting PDF split for storage key: {storage_key} with {pages_per_split} pages per split"
        )

        try:
            # Download the PDF file
            pdf_data = await self.storage_provider.download(storage_key)
            if not pdf_data:
                raise ValueError(f"Failed to download PDF from {storage_key}")

            # Read PDF using PyPDF2
            pdf_reader = PdfReader(io.BytesIO(pdf_data))
            total_pages = len(pdf_reader.pages)

            logger.info(
                f"PDF has {total_pages} pages, splitting into chunks of {pages_per_split} pages"
            )

            chunk_urls = []

            # Split into chunks
            base_key = storage_key.replace(".pdf", "")

            for chunk_start in range(0, total_pages, pages_per_split):
                chunk_end = min(chunk_start + pages_per_split, total_pages)

                chunk_buffer = self._create_chunk_pdf(
                    pdf_reader, chunk_start, chunk_end
                )
                chunk_key, page_range = self._generate_chunk_key(
                    base_key, chunk_start, chunk_end, pages_per_split
                )

                success = await self.storage_provider.upload(
                    chunk_key,
                    chunk_buffer,
                    metadata={
                        "content_type": "application/pdf",
                        "page_range": page_range,
                        "pages_per_split": str(pages_per_split),
                    },
                )

                if not success:
                    raise Exception(f"Failed to upload chunk {page_range} to S3")

                chunk_s3_url = f"s3://{settings.s3_bucket_name}/{chunk_key}"
                chunk_urls.append(chunk_s3_url)

                logger.info(f"Pages {page_range} uploaded to {chunk_s3_url}")

            logger.info(f"Successfully split PDF into {len(chunk_urls)} chunks")
            return chunk_urls

        except Exception as e:
            logger.error(f"Error splitting PDF: {e}")
            raise

    def _create_chunk_pdf(
        self, pdf_reader: PdfReader, chunk_start: int, chunk_end: int
    ) -> io.BytesIO:
        """Create a PDF chunk with specified page range."""
        pdf_writer = PdfWriter()
        for page_idx in range(chunk_start, chunk_end):
            pdf_writer.add_page(pdf_reader.pages[page_idx])

        chunk_buffer = io.BytesIO()
        pdf_writer.write(chunk_buffer)
        chunk_buffer.seek(0)
        return chunk_buffer

    def _generate_chunk_key(
        self, base_key: str, chunk_start: int, chunk_end: int, pages_per_split: int
    ) -> tuple[str, str]:
        """Generate S3 key and page range string for a chunk."""
        if pages_per_split == 1:
            chunk_key = f"{base_key}_page_{chunk_start + 1}.pdf"
            page_range = str(chunk_start + 1)
        else:
            chunk_key = f"{base_key}_pages_{chunk_start + 1}-{chunk_end}.pdf"
            page_range = f"{chunk_start + 1}-{chunk_end}"

        return chunk_key, page_range

    @trace_span
    async def convert_page_to_markdown(self, page_url: str) -> str:
        """
        Convert PDF page to markdown using MarkItDown.
        Returns markdown content directly.
        """
        logger.info(f"Converting page to markdown: {page_url}")

        try:
            # Download the page PDF
            page_key = page_url.replace(f"s3://{settings.s3_bucket_name}/", "")
            page_data = await self.storage_provider.download(page_key)

            if not page_data:
                raise ValueError(f"Failed to download page PDF from {page_url}")

            # Use MarkItDown to extract markdown
            file_stream = io.BytesIO(page_data)
            stream_info = StreamInfo(
                mimetype="application/pdf",
                extension=".pdf",
                filename=page_key.split("/")[-1],
            )
            result = self.markitdown.convert_stream(
                file_stream, stream_info=stream_info
            )

            if result and result.text_content:
                markdown_content = result.text_content.strip()
                logger.info(
                    f"Successfully converted page to markdown ({len(markdown_content)} characters)"
                )
                return markdown_content
            else:
                logger.warning(f"No text content extracted from PDF page")
                return ""

        except Exception as e:
            logger.error(f"Error converting page to markdown: {e}")
            raise
