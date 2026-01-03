"""
Repository for matrix entity set members.

Manages the matrix_entity_set_members table, which links entities
(documents or questions) to entity sets with ordering.
"""

from typing import List, Optional, Dict
from sqlalchemy.future import select
from sqlalchemy import update

from common.repositories.base import BaseRepository
from packages.matrices.models.database.matrix_entity_set import (
    MatrixEntitySetMemberEntity,
)
from packages.matrices.models.domain.matrix_entity_set import (
    MatrixEntitySetMemberModel,
    MatrixEntitySetMemberCreateModel,
)
from packages.matrices.models.domain.matrix_enums import EntityType
from common.core.otel_axiom_exporter import trace_span, get_logger

logger = get_logger(__name__)


class EntitySetMemberRepository(
    BaseRepository[MatrixEntitySetMemberEntity, MatrixEntitySetMemberModel]
):
    """Repository for managing entity set members."""

    def __init__(self):
        super().__init__(MatrixEntitySetMemberEntity, MatrixEntitySetMemberModel)

    @trace_span
    async def get_by_entity_set_id(
        self, entity_set_id: int, company_id: Optional[int] = None
    ) -> List[MatrixEntitySetMemberModel]:
        """Get all members of an entity set, ordered by member_order."""
        async with self._get_session() as session:
            query = (
                select(self.entity_class)
                .where(
                    self.entity_class.entity_set_id == entity_set_id,
                    self.entity_class.deleted == False,  # noqa
                )
                .order_by(self.entity_class.member_order)
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_member_by_entity_id(
        self,
        entity_set_id: int,
        entity_id: int,
        entity_type: EntityType,
        company_id: Optional[int] = None,
    ) -> Optional[MatrixEntitySetMemberModel]:
        """Get a specific member by entity_set_id, entity_id, and entity_type."""
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.entity_set_id == entity_set_id,
                self.entity_class.entity_id == entity_id,
                self.entity_class.entity_type == entity_type.value,
                self.entity_class.deleted == False,  # noqa
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entity = result.scalar_one_or_none()
            return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def add_member(
        self, create_model: MatrixEntitySetMemberCreateModel
    ) -> MatrixEntitySetMemberModel:
        """Add a new member to an entity set."""
        return await self.create(create_model)

    @trace_span
    async def add_members_batch(
        self, create_models: List[MatrixEntitySetMemberCreateModel]
    ) -> List[MatrixEntitySetMemberModel]:
        """Add multiple members to an entity set in a batch."""
        created_members = []
        for create_model in create_models:
            member = await self.add_member(create_model)
            created_members.append(member)
        return created_members

    @trace_span
    async def get_member_id_mappings(
        self, entity_set_id: int, company_id: Optional[int] = None
    ) -> Dict[int, int]:
        """Get mapping of entity_id -> member_id for an entity set.

        Used by strategies to build entity references when creating cells.
        Returns: {entity_id: member_id}
        """
        members = await self.get_by_entity_set_id(entity_set_id, company_id)
        return {member.entity_id: member.id for member in members}

    @trace_span
    async def get_by_member_ids(
        self, member_ids: List[int], company_id: Optional[int] = None
    ) -> List[MatrixEntitySetMemberModel]:
        """Get multiple members by their member IDs."""
        if not member_ids:
            return []

        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.id.in_(member_ids),
                self.entity_class.deleted == False,  # noqa
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def get_member_ids_by_entity_ids(
        self,
        entity_set_id: int,
        entity_ids: List[int],
        company_id: Optional[int] = None,
    ) -> List[int]:
        """Get member IDs for given entity IDs in an entity set.

        Returns only IDs for performance (no full models).
        Used for finding cells that reference specific entities.
        """
        if not entity_ids:
            return []

        async with self._get_session() as session:
            query = select(self.entity_class.id).where(
                self.entity_class.entity_set_id == entity_set_id,
                self.entity_class.entity_id.in_(entity_ids),
                self.entity_class.deleted == False,  # noqa
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            return [row[0] for row in result.fetchall()]

    @trace_span
    async def get_members_by_entity_id(
        self,
        entity_id: int,
        entity_type: EntityType,
        company_id: Optional[int] = None,
    ) -> List[MatrixEntitySetMemberModel]:
        """Get all members across all entity sets for a given entity_id.

        Used for finding which matrices contain a specific document/question.
        """
        async with self._get_session() as session:
            query = select(self.entity_class).where(
                self.entity_class.entity_id == entity_id,
                self.entity_class.entity_type == entity_type.value,
                self.entity_class.deleted == False,  # noqa
            )

            if company_id is not None:
                query = self._add_company_filter(query, company_id)

            result = await session.execute(query)
            entities = result.scalars().all()
            return self._entities_to_domain(entities)

    @trace_span
    async def update_label(
        self,
        member_id: int,
        label: Optional[str],
        company_id: Optional[int] = None,
    ) -> Optional[MatrixEntitySetMemberModel]:
        """Update the label of an entity set member."""
        async with self._get_session() as session:
            query = (
                update(self.entity_class)
                .where(self.entity_class.id == member_id)
                .values(label=label)
                .returning(self.entity_class)
            )

            if company_id is not None:
                query = query.where(self.entity_class.company_id == company_id)

            result = await session.execute(query)
            entity = result.scalar_one_or_none()
            await session.flush()

            return self._entity_to_domain(entity) if entity else None
