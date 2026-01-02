"""convert_enums_cols_to_strings

Revision ID: 5ce249d08456
Revises: 222a16db167a
Create Date: 2025-07-30 18:58:41.797094

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '5ce249d08456'
down_revision: Union[str, Sequence[str], None] = 'a8f1b8aee630'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Convert enum columns to string columns
    
    # Convert matrix_cells.status from enum to string
    op.alter_column('matrix_cells', 'status',
                    existing_type=sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='matrixcellstatus'),
                    type_=sa.String(),
                    existing_nullable=False)
    
    # Convert qa_jobs.status from enum to string  
    op.alter_column('qa_jobs', 'status',
                    existing_type=sa.Enum('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', name='qajobstatus'),
                    type_=sa.String(),
                    existing_nullable=False)
    
    # Drop the enum types (PostgreSQL specific)
    op.execute("DROP TYPE IF EXISTS matrixcellstatus")
    op.execute("DROP TYPE IF EXISTS qajobstatus")

def downgrade() -> None:
    """Downgrade schema."""
    # Recreate enum types (PostgreSQL specific)
    op.execute("CREATE TYPE matrixcellstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')")
    op.execute("CREATE TYPE qajobstatus AS ENUM ('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED')")
    
    # Convert string columns back to enum columns
    op.alter_column('qa_jobs', 'status',
                    existing_type=sa.String(),
                    type_=sa.Enum('QUEUED', 'PROCESSING', 'COMPLETED', 'FAILED', name='qajobstatus'),
                    existing_nullable=False,
                    postgresql_using='status::qajobstatus')
    
    op.alter_column('matrix_cells', 'status',
                    existing_type=sa.String(),
                    type_=sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='matrixcellstatus'),
                    existing_nullable=False,
                    postgresql_using='status::matrixcellstatus')
