import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from packages.documents.repositories.document_repository import DocumentRepository
from packages.documents.models.database.document import DocumentEntity
from uuid import uuid4


class TestDocumentRepository:
    """Unit tests for DocumentRepository."""

    @pytest.fixture
    async def repo(self, test_db: AsyncSession):
        """Create a DocumentRepository instance."""
        return DocumentRepository()

    @pytest.fixture
    async def sample_document(self, test_db: AsyncSession, sample_company):
        """Create a sample document."""
        document = DocumentEntity(
            filename="test.pdf",
            storage_key="test-key",
            content_type="application/pdf",
            file_size=1024,
            company_id=sample_company.id,
            checksum=str(uuid4()),
        )
        test_db.add(document)
        await test_db.commit()
        await test_db.refresh(document)
        return document

    @pytest.mark.asyncio
    async def test_get_by_storage_key(self, repo, sample_document):
        """Test getting document by storage key."""
        result = await repo.get_by_storage_key("test-key", 1)

        assert result is not None
        assert result.id == sample_document.id
        assert result.filename == "test.pdf"

    @pytest.mark.asyncio
    async def test_get_by_storage_key_not_found(self, repo):
        """Test getting document by non-existent storage key."""
        result = await repo.get_by_storage_key("non-existent-key", 1)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_storage_key_excludes_deleted(
        self, repo, test_db, sample_company
    ):
        """Test that get_by_storage_key excludes soft deleted documents."""
        # Create a deleted document
        doc = DocumentEntity(
            filename="deleted.pdf",
            storage_key="deleted-key",
            content_type="application/pdf",
            file_size=1024,
            checksum=str(uuid4()),
            company_id=sample_company.id,
            deleted=True,
        )

        test_db.add(doc)
        await test_db.commit()

        # Try to get by storage key
        result = await repo.get_by_storage_key("deleted-key", 1)

        assert result is None

    @pytest.mark.asyncio
    async def test_soft_delete_functionality_inheritance(self, repo, sample_document):
        """Test that inherited soft delete methods work correctly."""
        # Test soft_delete method from base repository
        result = await repo.soft_delete(sample_document.id)
        assert result is True

        # Verify document is soft deleted
        retrieved = await repo.get(sample_document.id, 1)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_bulk_soft_delete_functionality_inheritance(
        self, repo, test_db, sample_company
    ):
        """Test that inherited bulk_soft_delete method works correctly."""
        # Create multiple documents
        docs = []
        for i in range(3):
            doc = DocumentEntity(
                filename=f"doc{i}.pdf",
                storage_key=f"key{i}",
                content_type="application/pdf",
                file_size=1024,
                checksum=f"checksum{i}",
                company_id=sample_company.id,
            )
            docs.append(doc)

        test_db.add_all(docs)
        await test_db.commit()

        for doc in docs:
            await test_db.refresh(doc)

        # Test bulk_soft_delete method from base repository
        doc_ids = [doc.id for doc in docs]
        result = await repo.bulk_soft_delete(doc_ids)

        assert result == 3

        # Verify all documents are soft deleted
        for doc in docs:
            retrieved = await repo.get(doc.id, 1)
            assert retrieved is None
