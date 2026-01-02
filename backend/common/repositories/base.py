from typing import Generic, TypeVar, Optional, List, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from pydantic import BaseModel
from common.core.otel_axiom_exporter import trace_span

EntityType = TypeVar("EntityType")
DomainModelType = TypeVar("DomainModelType")
CreateModelType = TypeVar("CreateModelType", bound=BaseModel)
UpdateModelType = TypeVar("UpdateModelType", bound=BaseModel)


class BaseRepository(Generic[EntityType, DomainModelType]):
    def __init__(
        self,
        entity_class: Type[EntityType],
        domain_class: Type[DomainModelType],
        db_session: AsyncSession,
    ):
        self.entity_class = entity_class
        self.domain_class = domain_class
        self.db_session = db_session

    def _add_company_filter(self, query, company_id: int):
        """Add company filtering to any query."""
        return query.where(self.entity_class.company_id == company_id)

    def _entity_to_domain(self, entity: EntityType) -> DomainModelType:
        """Convert database entity to domain model."""
        return self.domain_class.model_validate(entity)

    def _entities_to_domain(self, entities: List[EntityType]) -> List[DomainModelType]:
        """Convert list of database entities to domain models."""
        return [self._entity_to_domain(entity) for entity in entities]

    @trace_span
    async def get(
        self, id: int, company_id: Optional[int] = None
    ) -> Optional[DomainModelType]:
        query = select(self.entity_class).where(self.entity_class.id == id)

        # Add deleted filter if the entity has a deleted column
        if hasattr(self.entity_class, "deleted"):
            query = query.where(self.entity_class.deleted == False)  # noqa

        if company_id is not None:
            query = self._add_company_filter(query, company_id)

        result = await self.db_session.execute(query)
        entity = result.scalar_one_or_none()
        return self._entity_to_domain(entity) if entity else None

    @trace_span
    async def get_multi(
        self, skip: int = 0, limit: int = 100, company_id: Optional[int] = None
    ) -> List[DomainModelType]:
        query = select(self.entity_class).offset(skip).limit(limit)

        # Add deleted filter if the entity has a deleted column
        if hasattr(self.entity_class, "deleted"):
            query = query.where(self.entity_class.deleted == False)  # noqa

        if company_id is not None:
            query = self._add_company_filter(query, company_id)

        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def get_by_ids(self, ids: List[int]) -> List[DomainModelType]:
        """Get multiple entities by their IDs."""
        if not ids:
            return []

        query = select(self.entity_class).where(self.entity_class.id.in_(ids))

        # Add deleted filter if the entity has a deleted column
        if hasattr(self.entity_class, "deleted"):
            query = query.where(self.entity_class.deleted == False)  # noqa

        result = await self.db_session.execute(query)
        entities = result.scalars().all()
        return self._entities_to_domain(entities)

    @trace_span
    async def create(self, create_model: CreateModelType) -> DomainModelType:
        """Create a new entity from a typed create model."""
        data = create_model.model_dump(exclude_none=True)
        db_obj = self.entity_class(**data)
        self.db_session.add(db_obj)
        await self.db_session.flush()
        await self.db_session.refresh(db_obj)
        return self._entity_to_domain(db_obj)

    @trace_span
    async def update(
        self, id: int, update_model: UpdateModelType
    ) -> Optional[DomainModelType]:
        """Update an entity with a typed update model."""
        data = update_model.model_dump(exclude_unset=True)
        if not data:
            return await self.get(id)

        await self.db_session.execute(
            update(self.entity_class).where(self.entity_class.id == id).values(data)
        )
        await self.db_session.flush()
        return await self.get(id)

    @trace_span
    async def delete(self, id: int) -> bool:
        result = await self.db_session.execute(
            delete(self.entity_class).where(self.entity_class.id == id)
        )
        await self.db_session.flush()
        return result.rowcount > 0

    @trace_span
    async def bulk_create(self, entities: List[EntityType]) -> List[DomainModelType]:
        """Bulk create entities and return domain models."""
        if not entities:
            return []

        self.db_session.add_all(entities)
        await self.db_session.flush()  # Flush to get IDs without committing
        return self._entities_to_domain(entities)

    @trace_span
    async def bulk_create_from_models(
        self, create_models: List[CreateModelType]
    ) -> List[DomainModelType]:
        """Bulk create from domain create models and return domain models."""
        if not create_models:
            return []

        # Convert create models to entities
        entities = []
        for create_model in create_models:
            # Convert pydantic model to dict, excluding None values
            # mode='json' ensures enums are serialized to their values
            model_data = create_model.model_dump(exclude_none=True, mode="json")
            entity = self.entity_class(**model_data)
            entities.append(entity)

        return await self.bulk_create(entities)

    @trace_span
    async def bulk_update_by_id(self, updates: List[UpdateModelType]) -> int:
        """Bulk update entities by ID. Each update model must have an 'id' field."""
        if not updates:
            return 0

        # Group updates by the values being updated to minimize queries
        updates_by_values = {}
        for update_model in updates:
            update_data = update_model.model_dump(exclude_unset=True)
            if "id" not in update_data:
                continue

            # Create a key from the non-id values
            values = {k: v for k, v in update_data.items() if k != "id"}
            values_key = tuple(sorted(values.items()))

            if values_key not in updates_by_values:
                updates_by_values[values_key] = {"values": values, "ids": []}
            updates_by_values[values_key]["ids"].append(update_data["id"])

        total_updated = 0
        for group in updates_by_values.values():
            result = await self.db_session.execute(
                update(self.entity_class)
                .where(self.entity_class.id.in_(group["ids"]))
                .values(group["values"])
            )
            total_updated += result.rowcount

        return total_updated

    @trace_span
    async def soft_delete(self, id: int) -> bool:
        """Soft delete an entity by setting deleted=True."""
        if hasattr(self.entity_class, "deleted"):
            result = await self.db_session.execute(
                update(self.entity_class)
                .where(self.entity_class.id == id)
                .values(deleted=True)
            )
            await self.db_session.flush()
            return result.rowcount > 0
        return False

    @trace_span
    async def bulk_soft_delete(self, ids: List[int]) -> int:
        """Bulk soft delete entities by setting deleted=True."""
        if not ids:
            return 0

        if hasattr(self.entity_class, "deleted"):
            result = await self.db_session.execute(
                update(self.entity_class)
                .where(
                    self.entity_class.id.in_(ids),
                    self.entity_class.deleted == False,  # noqa
                )
                .values(deleted=True)
            )
            await self.db_session.flush()
            return result.rowcount
        return 0
