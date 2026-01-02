from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from common.core.otel_axiom_exporter import trace_span
from common.repositories.base import BaseRepository
from common.providers.caching import cache
from packages.qa.models.database.citation import CitationSetEntity, CitationEntity
from packages.qa.models.domain.citation import (
    CitationSetModel,
    CitationModel,
    CitationSetWithCitationsModel,
)
from packages.qa.cache_keys import (
    citation_sets_by_answer_key,
    citation_set_by_id_key,
    citations_by_set_key,
    citations_by_document_key,
)


class CitationSetRepository(BaseRepository[CitationSetEntity, CitationSetModel]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(CitationSetEntity, CitationSetModel, db_session)

    @trace_span
    @cache(CitationSetModel, ttl=14400, key_generator=citation_sets_by_answer_key)
    async def get_by_answer_id(
        self, answer_id: int, company_id: Optional[int] = None
    ) -> List[CitationSetModel]:
        """Get all citation sets for an answer."""
        query = select(CitationSetEntity).where(
            CitationSetEntity.answer_id == answer_id
        )
        if company_id is not None:
            query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    @cache(CitationSetModel, ttl=14400, key_generator=citation_set_by_id_key)
    async def get_by_id(
        self, citation_set_id: int, company_id: Optional[int] = None
    ) -> Optional[CitationSetModel]:
        """Get citation set by ID without loading citations."""
        query = select(CitationSetEntity).where(CitationSetEntity.id == citation_set_id)
        if company_id is not None:
            query = query.where(CitationSetEntity.company_id == company_id)
        result = await self.db_session.execute(query)
        entity = result.scalar_one_or_none()
        return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def get_with_citations(
        self, citation_set_id: int, company_id: Optional[int] = None
    ) -> Optional[CitationSetWithCitationsModel]:
        """Get citation set with all its citations loaded."""
        # First get the citation set
        citation_set = await self.get_by_id(citation_set_id, company_id)
        if not citation_set:
            return None

        # Then get all citations for this set
        citations = await self.get_citations_by_set_id(citation_set_id, company_id)

        # Build the combined model
        return CitationSetWithCitationsModel(
            **citation_set.model_dump(), citations=citations
        )

    @trace_span
    @cache(CitationModel, ttl=14400, key_generator=citations_by_set_key)
    async def get_citations_by_set_id(
        self, citation_set_id: int, company_id: Optional[int] = None
    ) -> List[CitationModel]:
        """Get all citations for a citation set, ordered by citation_order."""
        query = (
            select(CitationEntity)
            .where(CitationEntity.citation_set_id == citation_set_id)
            .order_by(CitationEntity.citation_order)
        )
        if company_id is not None:
            query = query.where(CitationEntity.company_id == company_id)
        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return [CitationModel.model_validate(entity) for entity in entities]


class CitationRepository(BaseRepository[CitationEntity, CitationModel]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(CitationEntity, CitationModel, db_session)

    @trace_span
    @cache(CitationModel, ttl=14400, key_generator=citations_by_set_key)
    async def get_by_citation_set_id(
        self, citation_set_id: int, company_id: Optional[int] = None
    ) -> List[CitationModel]:
        """Get all citations for a citation set, ordered by citation_order."""
        query = (
            select(CitationEntity)
            .where(CitationEntity.citation_set_id == citation_set_id)
            .order_by(CitationEntity.citation_order)
        )
        if company_id is not None:
            query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    @cache(CitationModel, ttl=14400, key_generator=citations_by_document_key)
    async def get_by_document_id(
        self, document_id: int, company_id: Optional[int] = None
    ) -> List[CitationModel]:
        """Get all citations for a specific document."""
        query = select(CitationEntity).where(CitationEntity.document_id == document_id)
        if company_id is not None:
            query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def get_by_citation_set_ids(
        self, citation_set_ids: List[int], company_id: Optional[int] = None
    ) -> List[CitationModel]:
        """Batch fetch all citations for multiple citation sets."""
        if not citation_set_ids:
            return []

        query = (
            select(CitationEntity)
            .where(CitationEntity.citation_set_id.in_(citation_set_ids))
            .order_by(CitationEntity.citation_set_id, CitationEntity.citation_order)
        )
        if company_id is not None:
            query = self._add_company_filter(query, company_id)
        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)
