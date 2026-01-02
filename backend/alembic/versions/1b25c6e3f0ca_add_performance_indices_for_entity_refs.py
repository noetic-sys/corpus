"""add_performance_indices_for_entity_refs

Revision ID: 1b25c6e3f0ca
Revises: 39b3d718d103
Create Date: 2025-10-29 00:51:31.386197

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '1b25c6e3f0ca'
down_revision: Union[str, Sequence[str], None] = '39b3d718d103'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indices for entity refs and related tables.

    These indices optimize common query patterns:
    1. get_by_matrix_id with deleted filter (used in deduplication)
    2. get_members_by_entity_id lookups for documents
    """
    # Index for CellEntityReferenceRepository.get_by_matrix_id with deleted filter
    # This query loads all refs for a matrix during cell creation deduplication
    op.create_index(
        'idx_cell_refs_matrix_deleted',
        'matrix_cell_entity_refs',
        ['matrix_id', 'deleted'],
        unique=False
    )

    # Index for entity set member lookups by entity_id and entity_type
    # Used when finding which matrices use a document
    op.create_index(
        'idx_member_entity_lookup',
        'matrix_entity_set_members',
        ['entity_id', 'entity_type', 'deleted'],
        unique=False
    )


def downgrade() -> None:
    """Remove performance indices."""
    op.drop_index('idx_member_entity_lookup', table_name='matrix_entity_set_members')
    op.drop_index('idx_cell_refs_matrix_deleted', table_name='matrix_cell_entity_refs')
