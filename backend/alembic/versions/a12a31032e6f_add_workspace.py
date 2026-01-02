"""add_workspace

Revision ID: a12a31032e6f
Revises: 14802c835b3a
Create Date: 2025-08-05 11:39:41.558051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a12a31032e6f'
down_revision: Union[str, Sequence[str], None] = '00b46a442b7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create workspaces table
    op.create_table('workspaces',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspaces_deleted'), 'workspaces', ['deleted'], unique=False)
    op.create_index(op.f('ix_workspaces_id'), 'workspaces', ['id'], unique=False)
    op.create_index(op.f('ix_workspaces_name'), 'workspaces', ['name'], unique=False)

    # Add workspace_id column to matrices table
    op.add_column('matrices', sa.Column('workspace_id', sa.BigInteger(), nullable=False))
    
    # Create index and foreign key
    op.create_index(op.f('ix_matrices_workspace_id'), 'matrices', ['workspace_id'], unique=False)
    op.create_foreign_key('fk_matrices_workspace_id', 'matrices', 'workspaces', ['workspace_id'], ['id'])

def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key and index
    op.drop_constraint('fk_matrices_workspace_id', 'matrices', type_='foreignkey')
    op.drop_index(op.f('ix_matrices_workspace_id'), table_name='matrices')
    
    # Drop workspace_id column from matrices
    op.drop_column('matrices', 'workspace_id')
    
    # Drop workspaces table
    op.drop_index(op.f('ix_workspaces_name'), table_name='workspaces')
    op.drop_index(op.f('ix_workspaces_id'), table_name='workspaces')
    op.drop_index(op.f('ix_workspaces_deleted'), table_name='workspaces')
    op.drop_table('workspaces')
