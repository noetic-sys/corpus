"""deprecate_multi_select

Revision ID: 780989e7ddc5
Revises: da44f0635207
Create Date: 2025-08-26 17:13:11.939146

"""
from typing import Sequence, Union
from alembic import op



# revision identifiers, used by Alembic.
revision: str = '780989e7ddc5'
down_revision: Union[str, Sequence[str], None] = 'da44f0635207'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove MULTI_SELECT (id=6) and rename SINGLE_SELECT (id=5) to SELECT
    op.execute("""
        UPDATE question_types SET name = 'SELECT' WHERE id = 5 AND name = 'SINGLE_SELECT';
        DELETE FROM question_types WHERE id = 6 AND name = 'MULTI_SELECT';
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Restore SINGLE_SELECT and MULTI_SELECT
    op.execute("""
        UPDATE question_types SET name = 'SINGLE_SELECT' WHERE id = 5 AND name = 'SELECT';
        INSERT INTO question_types (id, name, description) VALUES (6, 'MULTI_SELECT', 'Multiple choice question allowing multiple selections') ON CONFLICT DO NOTHING;
    """)
