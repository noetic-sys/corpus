from datetime import datetime
from typing import Optional

from packages.documents.models.domain.document import DocumentModel
from packages.documents.models.database.document import DocumentEntity
from packages.documents.models.schemas.document import DocumentResponse


class DocumentFactory:
    """Factory for creating document test objects."""

    @staticmethod
    def create_document_model(
        id: int = 1,
        filename: str = "test_document.pdf",
        storage_key: str = "documents/1/test_document.pdf",
        content_type: str = "application/pdf",
        file_size: int = 1024,
        matrix_id: int = 1,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> DocumentModel:
        """Create a DocumentModel for testing."""
        now = datetime.now()
        return DocumentModel(
            id=id,
            filename=filename,
            storage_key=storage_key,
            content_type=content_type,
            file_size=file_size,
            matrix_id=matrix_id,
            created_at=created_at or now,
            updated_at=updated_at or now,
        )

    @staticmethod
    def create_document_entity(
        id: int = 1,
        filename: str = "test_document.pdf",
        storage_key: str = "documents/1/test_document.pdf",
        content_type: str = "application/pdf",
        file_size: int = 1024,
        matrix_id: int = 1,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> DocumentEntity:
        """Create a DocumentEntity for testing."""
        now = datetime.now()
        entity = DocumentEntity(
            filename=filename,
            storage_key=storage_key,
            content_type=content_type,
            file_size=file_size,
            matrix_id=matrix_id,
            created_at=created_at or now,
            updated_at=updated_at or now,
        )
        entity.id = id
        return entity

    @staticmethod
    def create_document_response(
        id: int = 1,
        filename: str = "test_document.pdf",
        storage_key: str = "documents/1/test_document.pdf",
        content_type: str = "application/pdf",
        file_size: int = 1024,
        matrix_id: int = 1,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> DocumentResponse:
        """Create a DocumentResponse for testing."""
        now = datetime.now()
        return DocumentResponse(
            id=id,
            filename=filename,
            storage_key=storage_key,
            content_type=content_type,
            file_size=file_size,
            matrix_id=matrix_id,
            created_at=created_at or now,
            updated_at=updated_at or now,
        )
