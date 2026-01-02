import pytest
from datetime import datetime
from pydantic import ValidationError

from packages.documents.models.schemas.document import DocumentResponse


class TestDocumentSchemas:
    """Unit tests for document schemas."""

    def test_document_response_creation(self):
        """Test creating a valid DocumentResponse."""
        now = datetime.now()
        response = DocumentResponse(
            id=1,
            company_id=1,
            filename="test.pdf",
            storage_key="documents/test.pdf",
            content_type="application/pdf",
            file_size=1024,
            checksum="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            extraction_status="completed",
            extracted_content_path="extracted/test.md",
            extraction_started_at=now,
            extraction_completed_at=now,
            created_at=now,
            updated_at=now,
        )

        assert response.id == 1
        assert response.company_id == 1
        assert response.filename == "test.pdf"
        assert response.storage_key == "documents/test.pdf"
        assert response.content_type == "application/pdf"
        assert response.file_size == 1024
        assert (
            response.checksum
            == "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
        )
        assert response.extraction_status == "completed"
        assert response.extracted_content_path == "extracted/test.md"
        assert response.extraction_started_at == now
        assert response.extraction_completed_at == now
        assert response.created_at == now
        assert response.updated_at == now

    def test_document_response_validation(self):
        """Test DocumentResponse validation."""
        with pytest.raises(ValidationError):
            DocumentResponse()  # Missing required fields
