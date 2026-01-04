from __future__ import annotations

from packages.documents.providers.document_highlighting.factory import (
    get_highlight_provider,
)
from packages.documents.providers.document_highlighting.interface import HighlightData
from packages.qa.services.citation_service import CitationService
from packages.documents.services.document_service import DocumentService
from packages.qa.services.answer_service import AnswerService
from packages.qa.services.answer_set_service import AnswerSetService
from packages.matrices.services.matrix_service import MatrixService
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class DocumentHighlightingService:
    """Service for highlighting documents with citations."""

    def __init__(self):
        self.citation_service = CitationService()
        self.document_service = DocumentService()
        self.answer_service = AnswerService()
        self.answer_set_service = AnswerSetService()
        self.matrix_service = MatrixService()

    @trace_span
    async def get_document_with_citations_highlighted(
        self,
        document_id: int,
        answer_set_id: int,
    ) -> bytes:
        """
        Get a document with citations from a specific answer set highlighted.

        Args:
            document_id: ID of the document to highlight
            answer_set_id: ID of the answer set whose citations should be highlighted

        Returns:
            Document bytes with citations highlighted

        Raises:
            ValueError: If document or citations not found
        """
        # Get the document
        document = await self.document_service.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Get document content
        document_content = await self.document_service.get_document_content(document)
        if not document_content:
            raise ValueError(f"Document content not found for document {document_id}")

        # Get citations for the answer set
        citations = await self.citation_service.get_citations_for_answer_set(
            self.answer_service, answer_set_id
        )
        if not citations:
            logger.info(
                f"No citations found for answer set {answer_set_id}, returning original document"
            )
            return document_content

        # Convert citations to highlight data
        highlights = []
        for i, citation in enumerate(citations):
            # Use different colors for different citations (cycling through a few colors)
            colors = [
                (1.0, 1.0, 0.0),  # Yellow
                (0.0, 1.0, 0.0),  # Green
                (0.0, 0.8, 1.0),  # Light Blue
                (1.0, 0.5, 0.0),  # Orange
                (1.0, 0.0, 1.0),  # Magenta
            ]
            color = colors[i % len(colors)]

            highlight_data = HighlightData(
                text=citation.quote_text,
                color=color,
                citation_number=citation.citation_order,
            )
            highlights.append(highlight_data)

        # Get appropriate highlighting provider
        provider = get_highlight_provider(document.filename)

        # Highlight the document
        try:
            highlighted_content = await provider.highlight_document(
                document_content, document.filename, highlights
            )

            logger.info(
                f"Successfully highlighted document {document_id} with {len(citations)} citations"
            )
            return highlighted_content

        except Exception as e:
            logger.error(f"Error highlighting document {document_id}: {e}")
            # Return original document if highlighting fails
            return document_content

    @trace_span
    async def get_document_with_cell_citations_highlighted(
        self,
        document_id: int,
        matrix_cell_id: int,
    ) -> bytes:
        """
        Get a document with citations from a matrix cell's current answer set highlighted.

        Args:
            document_id: ID of the document to highlight
            matrix_cell_id: ID of the matrix cell whose answer citations should be highlighted

        Returns:
            Document bytes with citations highlighted

        Raises:
            ValueError: If document or cell not found
        """
        # Get the matrix cell and its current answer set
        matrix_cell = await self.matrix_service.get_matrix_cell(matrix_cell_id)
        if not matrix_cell:
            raise ValueError(f"Matrix cell {matrix_cell_id} not found")

        if not matrix_cell.current_answer_set_id:
            raise ValueError(
                f"No current answer set found for matrix cell {matrix_cell_id}"
            )

        return await self.get_document_with_citations_highlighted(
            document_id, matrix_cell.current_answer_set_id
        )


def get_document_highlighting_service() -> DocumentHighlightingService:
    """Get document highlighting service instance."""
    return DocumentHighlightingService()
