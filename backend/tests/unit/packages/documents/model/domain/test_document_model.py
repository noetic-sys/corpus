from datetime import datetime
from packages.documents.models.domain.document import DocumentModel


class TestDocumentModel:
    """Unit tests for DocumentModel."""

    def test_document_model_creation(self):
        """Test creating a valid DocumentModel."""
        now = datetime.now()
        document = DocumentModel(
            id=1,
            company_id=1,
            filename="test.pdf",
            storage_key="documents/test.pdf",
            content_type="application/pdf",
            file_size=1024,
            checksum="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
            created_at=now,
            updated_at=now,
        )

        assert document.id == 1
        assert document.company_id == 1
        assert document.filename == "test.pdf"
        assert document.storage_key == "documents/test.pdf"
        assert document.content_type == "application/pdf"
        assert document.file_size == 1024
        assert (
            document.checksum
            == "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
        )
        assert document.created_at == now
        assert document.updated_at == now
