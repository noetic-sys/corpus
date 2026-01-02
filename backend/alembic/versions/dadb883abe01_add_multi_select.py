"""add_multi_select

Revision ID: dadb883abe01
Revises: 6c70f9022cbf
Create Date: 2025-07-28 01:27:59.708367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'dadb883abe01'
down_revision: Union[str, Sequence[str], None] = '6c70f9022cbf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add MULTI_SELECT question type."""
    # Insert MULTI_SELECT question type
    question_types_table = sa.table('question_types',
        sa.column('id', sa.BIGINT()),
        sa.column('name', sa.VARCHAR()),
        sa.column('description', sa.TEXT()),
        sa.column('validation_schema', sa.JSON())
    )
    
    op.bulk_insert(question_types_table, [
        {'id': 6, 'name': 'MULTI_SELECT', 'description': 'Choose multiple options from predefined values', 'validation_schema': {'type': 'array', 'options': []}},
    ])


def downgrade() -> None:
    """Remove MULTI_SELECT question type."""
    # Delete MULTI_SELECT question type (CASCADE will handle dependent questions)
    op.execute("DELETE FROM question_types WHERE id = 6 AND name = 'MULTI_SELECT'")