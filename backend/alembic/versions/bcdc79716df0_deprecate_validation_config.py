"""deprecate_validation_config

Revision ID: bcdc79716df0
Revises: 5f2eea6c488e
Create Date: 2025-09-16 00:13:04.048614

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcdc79716df0'
down_revision: Union[str, Sequence[str], None] = '5f2eea6c488e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Remove deprecated validation_config column from questions table."""
    # Drop the validation_config column as it's no longer used
    op.drop_column('questions', 'validation_config')


def downgrade() -> None:
    """Downgrade schema - Re-add validation_config column to questions table."""
    # Re-add the validation_config column if we need to rollback
    op.add_column('questions',
        sa.Column('validation_config', sa.JSON(), nullable=True)
    )
