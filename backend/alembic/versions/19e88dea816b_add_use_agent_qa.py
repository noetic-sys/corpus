"""add_use_agent_qa

Revision ID: 19e88dea816b
Revises: 760f9b6a1075
Create Date: 2025-10-30 16:12:28.115708

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "19e88dea816b"
down_revision: Union[str, Sequence[str], None] = "f6bd3a58325a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add use_agent_qa column to questions table."""
    op.add_column(
        "questions",
        sa.Column("use_agent_qa", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Remove use_agent_qa column from questions table."""
    op.drop_column("questions", "use_agent_qa")
