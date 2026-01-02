from __future__ import annotations

import asyncio
import fitz  # PyMuPDF
from typing import List
from io import BytesIO

from .interface import DocumentHighlightingInterface, HighlightData
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class PDFHighlightProvider(DocumentHighlightingInterface):
    """PDF-specific provider for highlighting text using PyMuPDF."""

    def __init__(self):
        self.supported_extensions = [".pdf"]

    @trace_span
    async def highlight_document(
        self,
        document_content: bytes,
        document_filename: str,
        highlights: List[HighlightData],
    ) -> bytes:
        """Highlight text in a PDF document using PyMuPDF."""
        if not self.supports_file_type(document_filename):
            raise NotImplementedError(f"File type not supported: {document_filename}")

        if not highlights:
            return document_content

        # Run the synchronous PDF processing in a thread pool
        return await asyncio.to_thread(
            self._highlight_pdf_sync, document_content, highlights
        )

    def _highlight_pdf_sync(
        self, document_content: bytes, highlights: List[HighlightData]
    ) -> bytes:
        """Synchronous PDF highlighting logic."""
        try:
            # Open PDF from bytes
            doc = fitz.open(stream=document_content, filetype="pdf")

            # Track processed highlights to avoid duplicates
            processed_texts = set()

            for highlight_data in highlights:
                text_to_find = highlight_data.text.strip()

                # Skip if we've already processed this exact text
                if text_to_find in processed_texts:
                    continue
                processed_texts.add(text_to_find)

                logger.info(
                    f"Searching for text to highlight: '{text_to_find[:50]}...'"
                )

                # Search for text across all pages
                found_instances = 0
                for page_num in range(len(doc)):
                    page = doc[page_num]

                    # Search for the text on this page
                    text_instances = page.search_for(text_to_find)

                    if text_instances:
                        logger.info(
                            f"Found {len(text_instances)} instances on page {page_num + 1}"
                        )

                        # Highlight each instance
                        for inst in text_instances:
                            # Create highlight annotation
                            highlight = page.add_highlight_annot(inst)
                            highlight.set_colors(stroke=highlight_data.color)
                            highlight.update()
                            found_instances += 1

                if found_instances == 0:
                    logger.warning(
                        f"Text not found in document: '{text_to_find[:50]}...'"
                    )
                else:
                    logger.info(
                        f"Highlighted {found_instances} instances of text: '{text_to_find[:50]}...'"
                    )

            # Save the modified PDF to bytes
            output_stream = BytesIO()
            doc.save(output_stream)
            doc.close()

            highlighted_content = output_stream.getvalue()
            output_stream.close()

            logger.info(
                f"Successfully highlighted PDF with {len(highlights)} highlight requests"
            )
            return highlighted_content

        except Exception as e:
            logger.error(f"Error highlighting PDF: {e}")
            raise

    def supports_file_type(self, filename: str) -> bool:
        """Check if the file is a PDF."""
        return any(filename.lower().endswith(ext) for ext in self.supported_extensions)

    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return self.supported_extensions.copy()
