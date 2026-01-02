"""
Routes for entity set operations.

Handles entity set management, member operations, and label updates.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from common.db.session import get_db
from common.db.transaction_utils import transaction
from packages.auth.dependencies import get_current_active_user
from packages.auth.models.domain.authenticated_user import AuthenticatedUser
from packages.matrices.services.entity_set_service import get_entity_set_service
from packages.matrices.models.schemas.matrix_entity_set import (
    EntitySetMemberResponse,
    EntitySetMemberLabelUpdate,
)
from common.core.otel_axiom_exporter import trace_span, get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.patch(
    "/entity-sets/{entitySetId}/members/{memberId}/label",
    response_model=EntitySetMemberResponse,
)
@trace_span
async def update_entity_set_member_label(
    entity_set_id: Annotated[int, Path(alias="entitySetId")],
    member_id: Annotated[int, Path(alias="memberId")],
    label_update: EntitySetMemberLabelUpdate,
    current_user: AuthenticatedUser = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the label of an entity set member.

    Labels are per-matrix context - the same entity (document/question) can have
    different labels in different entity sets/matrices.
    """
    async with transaction(db):
        entity_set_service = get_entity_set_service(db)

        updated_member = await entity_set_service.update_member_label(
            entity_set_id=entity_set_id,
            member_id=member_id,
            label=label_update.label,
            company_id=current_user.company_id,
        )

        logger.info(
            f"Updated label for member {member_id} in entity set {entity_set_id}"
        )
        return EntitySetMemberResponse.model_validate(updated_member)
