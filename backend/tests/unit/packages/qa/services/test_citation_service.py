import pytest
from packages.qa.models.database.citation import CitationSetEntity
from sqlalchemy.ext.asyncio import AsyncSession
from packages.qa.services.citation_service import CitationService
from packages.qa.models.domain.citation import (
    CitationSetCreateModel,
    CitationCreateModel,
    CitationCreateWithoutSetIdModel,
)
from packages.qa.models.database.citation import CitationEntity
from packages.documents.models.database.document import DocumentEntity
from common.providers.caching import get_cache_provider


class TestCitationService:
    """Test CitationService methods."""

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
    async def service(self, test_db: AsyncSession):
        """Create service instance."""
        return CitationService(test_db)

    async def test_create_citation_set_with_citations_success(
        self, service, sample_answer, sample_document, sample_company
    ):
        """Test creating a citation set with citations successfully."""
        citation_data = CitationSetCreateModel(
            answer_id=sample_answer.id,
            company_id=sample_company.id,
            citations=[
                CitationCreateWithoutSetIdModel(
                    document_id=sample_document.id,
                    company_id=sample_company.id,
                    quote_text="This is the first quote",
                    citation_order=1,
                ),
                CitationCreateWithoutSetIdModel(
                    document_id=sample_document.id,
                    company_id=sample_company.id,
                    quote_text="This is the second quote",
                    citation_order=2,
                ),
            ],
        )

        result = await service.create_citation_set_with_citations(
            citation_data, sample_company.id
        )

        assert result is not None
        assert result.answer_id == sample_answer.id
        assert result.company_id == sample_company.id
        assert len(result.citations) == 2
        assert result.citations[0].quote_text == "This is the first quote"
        assert result.citations[0].citation_order == 1
        assert result.citations[1].quote_text == "This is the second quote"
        assert result.citations[1].citation_order == 2

    async def test_create_citation_set_with_no_citations(
        self, service, sample_answer, sample_company
    ):
        """Test creating a citation set with no citations."""
        citation_data = CitationSetCreateModel(
            answer_id=sample_answer.id, company_id=sample_company.id, citations=[]
        )

        result = await service.create_citation_set_with_citations(
            citation_data, sample_company.id
        )

        assert result is not None
        assert result.answer_id == sample_answer.id
        assert result.company_id == sample_company.id
        assert len(result.citations) == 0

    async def test_get_citation_set(self, service, sample_citation_set):
        """Test getting a citation set by ID."""
        result = await service.get_citation_set(sample_citation_set.id)

        assert result is not None
        assert result.id == sample_citation_set.id
        assert result.answer_id == sample_citation_set.answer_id

    async def test_get_citation_set_not_found(self, service):
        """Test getting non-existent citation set."""
        result = await service.get_citation_set(999)
        assert result is None

    async def test_get_citation_set_with_citations(
        self, service, sample_citation_set, sample_document, sample_company
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
        service.db_session.add_all([citation1, citation2])
        await service.db_session.commit()

        result = await service.get_citation_set_with_citations(sample_citation_set.id)

        assert result is not None
        assert result.id == sample_citation_set.id
        assert len(result.citations) == 2
        assert result.citations[0].citation_order == 1
        assert result.citations[1].citation_order == 2

    async def test_get_citation_sets_for_answer(
        self, service, sample_answer, sample_company, test_db
    ):
        """Test getting all citation sets for an answer."""

        # Create multiple citation sets for the same answer
        citation_set1 = CitationSetEntity(
            answer_id=sample_answer.id, company_id=sample_company.id
        )
        citation_set2 = CitationSetEntity(
            answer_id=sample_answer.id, company_id=sample_company.id
        )
        test_db.add_all([citation_set1, citation_set2])
        await test_db.commit()

        results = await service.get_citation_sets_for_answer(sample_answer.id)

        # Should include the original sample_citation_set plus the 2 new ones
        assert len(results) >= 2
        assert all(cs.answer_id == sample_answer.id for cs in results)

    async def test_get_citations_for_set(
        self, service, sample_citation_set, sample_document, sample_company
    ):
        """Test getting citations for a citation set."""
        # Create citations with different orders
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
        service.db_session.add_all([citation1, citation2])
        await service.db_session.commit()

        citations = await service.get_citations_for_set(sample_citation_set.id)

        assert len(citations) == 2
        # Should be ordered by citation_order
        assert citations[0].citation_order == 1
        assert citations[1].citation_order == 3
        assert citations[0].quote_text == "First quote"
        assert citations[1].quote_text == "Third quote"

    async def test_get_citations_for_document(
        self, service, sample_citation_set, sample_document, sample_company, test_db
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
        service.db_session.add_all([citation1, citation2, citation3])
        await service.db_session.commit()

        # Get citations for first document
        citations = await service.get_citations_for_document(sample_document.id)

        assert len(citations) == 2
        assert all(c.document_id == sample_document.id for c in citations)
        quote_texts = [c.quote_text for c in citations]
        assert "Quote from doc 1" in quote_texts
        assert "Another quote from doc 1" in quote_texts

    async def test_create_citation(
        self, service, sample_citation_set, sample_document, sample_company
    ):
        """Test creating a single citation."""
        citation_data = CitationCreateModel(
            citation_set_id=sample_citation_set.id,
            document_id=sample_document.id,
            company_id=sample_company.id,
            quote_text="Single citation quote",
            citation_order=1,
        )

        result = await service.create_citation(
            citation_data, sample_citation_set.id, sample_company.id
        )

        assert result.citation_set_id == sample_citation_set.id
        assert result.document_id == sample_document.id
        assert result.company_id == sample_company.id
        assert result.quote_text == "Single citation quote"
        assert result.citation_order == 1

    async def test_service_initialization(self, test_db):
        """Test service properly initializes all repositories."""
        service = CitationService(test_db)

        assert service.db_session == test_db
        assert service.citation_set_repo is not None
        assert service.citation_repo is not None
