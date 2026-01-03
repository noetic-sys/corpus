"""add_use_agentic_chunking_to_documents

Revision ID: d0cd218cc5eb
Revises: 5bd5e08b35df
Create Date: 2026-01-03 10:32:42.707634

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd0cd218cc5eb'
down_revision: Union[str, Sequence[str], None] = '5bd5e08b35df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add use_agentic_chunking column to documents table."""
    op.add_column(
        "documents",
        sa.Column(
            "use_agentic_chunking",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    """Remove use_agentic_chunking column from documents table."""
    op.drop_column("documents", "use_agentic_chunking")
