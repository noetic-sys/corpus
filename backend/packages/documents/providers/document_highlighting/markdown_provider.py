from __future__ import annotations

import asyncio
import re
from typing import List

from .interface import DocumentHighlightingInterface, HighlightData
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class MarkdownHighlightProvider(DocumentHighlightingInterface):
    """Markdown/text provider for highlighting using text formatting."""

    def __init__(self):
        self.supported_extensions = [".md", ".markdown", ".txt", ".text"]

    @trace_span
    async def highlight_document(
        self,
        document_content: bytes,
        document_filename: str,
        highlights: List[HighlightData],
    ) -> bytes:
        """Highlight text in a Markdown/text document using formatting."""
        if not self.supports_file_type(document_filename):
            raise NotImplementedError(f"File type not supported: {document_filename}")

        if not highlights:
            return document_content

        # Run the synchronous text processing in a thread pool
        return await asyncio.to_thread(
            self._highlight_markdown_sync,
            document_content,
            document_filename,
            highlights,
        )

    def _highlight_markdown_sync(
        self,
        document_content: bytes,
        document_filename: str,
        highlights: List[HighlightData],
    ) -> bytes:
        """Synchronous Markdown highlighting logic."""
        try:
            # Decode content to text
            try:
                text_content = document_content.decode("utf-8")
            except UnicodeDecodeError:
                text_content = document_content.decode("utf-8", errors="replace")

            # For plain text files, just treat them as markdown
            if document_filename.lower().endswith((".txt", ".text")):
                logger.info(
                    f"Treating {document_filename} as plain text for highlighting"
                )

            # Track processed highlights to avoid duplicates
            processed_texts = set()
            total_highlights_applied = 0

            # Sort highlights by length (longest first) to avoid partial replacements
            sorted_highlights = sorted(
                highlights, key=lambda h: len(h.text), reverse=True
            )

            for highlight_data in sorted_highlights:
                text_to_find = highlight_data.text.strip()

                # Skip if we've already processed this exact text
                if text_to_find in processed_texts:
                    continue
                processed_texts.add(text_to_find)

                logger.info(
                    f"Searching for text to highlight: '{text_to_find[:50]}...'"
                )

                # Create highlighted version with multiple formatting for visibility
                # Using a combination of bold, italic, and special markers
                highlighted_text = self._create_highlighted_text(
                    text_to_find, highlight_data
                )

                # Count occurrences
                occurrences = text_content.lower().count(text_to_find.lower())

                if occurrences > 0:
                    # Replace all occurrences (case-insensitive)
                    # Use regex for case-insensitive replacement while preserving original case
                    pattern = re.compile(re.escape(text_to_find), re.IGNORECASE)
                    text_content = pattern.sub(highlighted_text, text_content)

                    logger.info(
                        f"Highlighted {occurrences} instances of text: '{text_to_find[:50]}...'"
                    )
                    total_highlights_applied += occurrences
                else:
                    logger.warning(
                        f"Text not found in document: '{text_to_find[:50]}...'"
                    )

            # Convert back to bytes
            highlighted_content = text_content.encode("utf-8")

            logger.info(
                f"Successfully highlighted Markdown/text with {len(highlights)} highlight requests, {total_highlights_applied} instances highlighted"
            )
            return highlighted_content

        except Exception as e:
            logger.error(f"Error highlighting Markdown/text document: {e}")
            raise

    def _create_highlighted_text(self, text: str, highlight_data: HighlightData) -> str:
        """
        Create a highlighted version of text using Markdown formatting.
        Uses multiple formatting techniques to make it super obvious.
        """
        # Escape any existing markdown formatting in the text
        escaped_text = self._escape_markdown(text)

        # Create a super obvious highlight using multiple techniques:
        # 1. Wrap in bold and italic for emphasis
        # 2. Add visual markers
        # 3. Add citation number if provided

        if highlight_data.citation_number is not None:
            # Include citation number in the highlight
            highlighted = (
                f"==***【{escaped_text}】***==[{highlight_data.citation_number}]"
            )
        else:
            # No citation number, just highlight
            highlighted = f"==***【{escaped_text}】***=="

        return highlighted

    def _escape_markdown(self, text: str) -> str:
        """
        Escape special Markdown characters in text to prevent formatting issues.
        """
        # Characters that need escaping in Markdown
        special_chars = ["*", "_", "`", "[", "]", "#", "+", "-", ".", "!", "|", "\\"]

        escaped = text
        for char in special_chars:
            escaped = escaped.replace(char, f"\\{char}")

        return escaped

    def supports_file_type(self, filename: str) -> bool:
        """Check if the file is a Markdown or text document."""
        return any(filename.lower().endswith(ext) for ext in self.supported_extensions)

    def get_supported_extensions(self) -> List[str]:
        """Return list of supported file extensions."""
        return self.supported_extensions.copy()
