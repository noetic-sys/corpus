import pytest
from packages.documents.models.database.document import DocumentEntity
from sqlalchemy.ext.asyncio import AsyncSession
from packages.qa.repositories.citation_repository import (
    CitationSetRepository,
    CitationRepository,
)
from packages.qa.models.database.citation import CitationSetEntity, CitationEntity
from packages.qa.models.domain.citation import (
    CitationSetCreateOnlyModel,
    CitationCreateModel,
)
from common.providers.caching import get_cache_provider


class TestCitationSetRepository:
    """Test CitationSetRepository methods."""

    @pytest.fixture(autouse=True)
    async def clear_cache(self):
        """Clear cache before each test."""
        try:
            cache_provider = get_cache_provider()
            await cache_provider.clear()
        except Exception:
            # If cache provider fails, continue with test
            pass

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return CitationSetRepository()

    async def test_create_citation_set(self, repository, sample_answer, sample_company):
        """Test creating a citation set."""
        citation_set_data = CitationSetCreateOnlyModel(
            answer_id=sample_answer.id,
            company_id=sample_company.id,
        )

        result = await repository.create(citation_set_data)

        assert result.answer_id == sample_answer.id
        assert result.company_id == sample_company.id
        assert result.id is not None

    async def test_get_by_answer_id(
        self, repository, sample_answer, sample_citation_set, sample_company, test_db
    ):
        """Test getting citation sets by answer ID."""
        # Create another citation set for the same answer
        citation_set2 = CitationSetEntity(
            answer_id=sample_answer.id, company_id=sample_company.id
        )
        test_db.add(citation_set2)
        await test_db.commit()

        citation_sets = await repository.get_by_answer_id(sample_answer.id)

        assert len(citation_sets) == 2
        assert all(cs.answer_id == sample_answer.id for cs in citation_sets)

    async def test_get_by_answer_id_empty(self, repository, sample_answer):
        """Test getting citation sets for answer with no citation sets."""
        citation_sets = await repository.get_by_answer_id(sample_answer.id)
        assert len(citation_sets) == 0

    async def test_get_with_citations(
        self, repository, sample_citation_set, sample_document, sample_company, test_db
    ):
        """Test getting citation set with citations loaded."""
        # Create citations for the set
        citation1 = CitationEntity(
            citation_set_id=sample_citation_set.id,
            document_id=sample_document.id,
            company_id=sample_company.id,
            quote_text="First quote",
            citation_order=1,
        )
        citation2 = CitationEntity(
            citation_set_id=sample_citation_set.id,
            document_id=sample_document.id,
            company_id=sample_company.id,
            quote_text="Second quote",
            citation_order=2,
        )
        test_db.add_all([citation1, citation2])
        await test_db.commit()

        result = await repository.get_with_citations(sample_citation_set.id)

        assert result is not None
        assert result.id == sample_citation_set.id
        assert len(result.citations) == 2

    async def test_get_with_citations_not_found(self, repository):
        """Test getting non-existent citation set."""
        result = await repository.get_with_citations(999)
        assert result is None


class TestCitationRepository:
    """Test CitationRepository methods."""

    @pytest.fixture(autouse=True)
    async def clear_cache(self):
        """Clear cache before each test."""
        try:
            cache_provider = get_cache_provider()
            await cache_provider.clear()
        except Exception:
            # If cache provider fails, continue with test
            pass

    @pytest.fixture
    async def repository(self, test_db: AsyncSession):
        """Create repository instance."""
        return CitationRepository()

    async def test_create_citation(
        self, repository, sample_citation_set, sample_document, sample_company
    ):
        """Test creating a citation."""
        citation_data = CitationCreateModel(
            citation_set_id=sample_citation_set.id,
            document_id=sample_document.id,
            company_id=sample_company.id,
            quote_text="This is a test quote",
            citation_order=1,
        )

        result = await repository.create(citation_data)

        assert result.citation_set_id == sample_citation_set.id
        assert result.document_id == sample_document.id
        assert result.company_id == sample_company.id
        assert result.quote_text == "This is a test quote"
        assert result.citation_order == 1

    async def test_get_by_citation_set_id(
        self, repository, sample_citation_set, sample_document, sample_company, test_db
    ):
        """Test getting citations by citation set ID, ordered by citation_order."""
        # Create multiple citations with different orders
        citation1 = CitationEntity(
            citation_set_id=sample_citation_set.id,
            document_id=sample_document.id,
            company_id=sample_company.id,
            quote_text="Third quote",
            citation_order=3,
        )
        citation2 = CitationEntity(
            citation_set_id=sample_citation_set.id,
            document_id=sample_document.id,
            company_id=sample_company.id,
            quote_text="First quote",
            citation_order=1,
        )
        citation3 = CitationEntity(
            citation_set_id=sample_citation_set.id,
            document_id=sample_document.id,
            company_id=sample_company.id,
            quote_text="Second quote",
            citation_order=2,
        )
        test_db.add_all([citation1, citation2, citation3])
        await test_db.commit()

        citations = await repository.get_by_citation_set_id(sample_citation_set.id)

        assert len(citations) == 3
        assert citations[0].citation_order == 1
        assert citations[1].citation_order == 2
        assert citations[2].citation_order == 3
        assert citations[0].quote_text == "First quote"
        assert citations[1].quote_text == "Second quote"
        assert citations[2].quote_text == "Third quote"

    async def test_get_by_citation_set_id_empty(self, repository, sample_citation_set):
        """Test getting citations for citation set with no citations."""
        citations = await repository.get_by_citation_set_id(sample_citation_set.id)
        assert len(citations) == 0

    async def test_get_by_document_id(
        self, repository, sample_citation_set, sample_document, sample_company, test_db
    ):
        """Test getting citations by document ID."""
        # Create another document

        document2 = DocumentEntity(
            filename="test2.pdf",
            storage_key="test_storage_key_2",
            checksum="test_checksum_hash_2",
            content_type="application/pdf",
            file_size=2048,
            company_id=sample_company.id,
        )
        test_db.add(document2)
        await test_db.commit()
        await test_db.refresh(document2)

        # Create citations for both documents
        citation1 = CitationEntity(
            citation_set_id=sample_citation_set.id,
            document_id=sample_document.id,
            company_id=sample_company.id,
            quote_text="Quote from doc 1",
            citation_order=1,
        )
        citation2 = CitationEntity(
            citation_set_id=sample_citation_set.id,
            document_id=sample_document.id,
            company_id=sample_company.id,
            quote_text="Another quote from doc 1",
            citation_order=2,
        )
        citation3 = CitationEntity(
            citation_set_id=sample_citation_set.id,
            document_id=document2.id,
            company_id=sample_company.id,
            quote_text="Quote from doc 2",
            citation_order=3,
        )
        test_db.add_all([citation1, citation2, citation3])
        await test_db.commit()

        # Get citations for first document
        citations = await repository.get_by_document_id(sample_document.id)

        assert len(citations) == 2
        assert all(c.document_id == sample_document.id for c in citations)
        quote_texts = [c.quote_text for c in citations]
        assert "Quote from doc 1" in quote_texts
        assert "Another quote from doc 1" in quote_texts

    async def test_get_by_document_id_empty(self, repository, sample_document):
        """Test getting citations for document with no citations."""
        citations = await repository.get_by_document_id(sample_document.id)
        assert len(citations) == 0
