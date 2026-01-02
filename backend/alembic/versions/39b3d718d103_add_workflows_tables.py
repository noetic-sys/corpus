"""add_workflows_tables

Revision ID: 39b3d718d103
Revises: 8f2589078d89
Create Date: 2025-10-21 22:59:15.946944

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39b3d718d103'
down_revision: Union[str, Sequence[str], None] = '8f2589078d89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create workflows table
    op.create_table(
        'workflows',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('company_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('trigger_type', sa.String(50), nullable=False),
        sa.Column('workspace_id', sa.BigInteger(), nullable=False),
        sa.Column('output_type', sa.String(50), nullable=False),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflows_id', 'workflows', ['id'])
    op.create_index('ix_workflows_company_id', 'workflows', ['company_id'])
    op.create_index('ix_workflows_trigger_type', 'workflows', ['trigger_type'])
    op.create_index('ix_workflows_workspace_id', 'workflows', ['workspace_id'])

    # Create workflow_executions table
    op.create_table(
        'workflow_executions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('workflow_id', sa.BigInteger(), nullable=False),
        sa.Column('company_id', sa.BigInteger(), nullable=False),
        sa.Column('trigger_type', sa.String(50), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('output_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('execution_log', sa.JSON(), nullable=True),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id']),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_executions_id', 'workflow_executions', ['id'])
    op.create_index('ix_workflow_executions_workflow_id', 'workflow_executions', ['workflow_id'])
    op.create_index('ix_workflow_executions_company_id', 'workflow_executions', ['company_id'])
    op.create_index('ix_workflow_executions_status', 'workflow_executions', ['status'])

    # Create workflow_input_files table
    op.create_table(
        'workflow_input_files',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('workflow_id', sa.BigInteger(), nullable=False),
        sa.Column('company_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('storage_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_input_files_id', 'workflow_input_files', ['id'])
    op.create_index('ix_workflow_input_files_workflow_id', 'workflow_input_files', ['workflow_id'])
    op.create_index('ix_workflow_input_files_company_id', 'workflow_input_files', ['company_id'])

    # Create workflow_execution_files table
    op.create_table(
        'workflow_execution_files',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('execution_id', sa.BigInteger(), nullable=False),
        sa.Column('company_id', sa.BigInteger(), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('storage_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['execution_id'], ['workflow_executions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workflow_execution_files_id', 'workflow_execution_files', ['id'])
    op.create_index('ix_workflow_execution_files_execution_id', 'workflow_execution_files', ['execution_id'])
    op.create_index('ix_workflow_execution_files_company_id', 'workflow_execution_files', ['company_id'])
    op.create_index('ix_workflow_execution_files_file_type', 'workflow_execution_files', ['file_type'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_workflow_execution_files_file_type', table_name='workflow_execution_files')
    op.drop_index('ix_workflow_execution_files_company_id', table_name='workflow_execution_files')
    op.drop_index('ix_workflow_execution_files_execution_id', table_name='workflow_execution_files')
    op.drop_index('ix_workflow_execution_files_id', table_name='workflow_execution_files')
    op.drop_table('workflow_execution_files')

    op.drop_index('ix_workflow_input_files_company_id', table_name='workflow_input_files')
    op.drop_index('ix_workflow_input_files_workflow_id', table_name='workflow_input_files')
    op.drop_index('ix_workflow_input_files_id', table_name='workflow_input_files')
    op.drop_table('workflow_input_files')

    op.drop_index('ix_workflow_executions_status', table_name='workflow_executions')
    op.drop_index('ix_workflow_executions_company_id', table_name='workflow_executions')
    op.drop_index('ix_workflow_executions_workflow_id', table_name='workflow_executions')
    op.drop_index('ix_workflow_executions_id', table_name='workflow_executions')
    op.drop_table('workflow_executions')

    op.drop_index('ix_workflows_workspace_id', table_name='workflows')
    op.drop_index('ix_workflows_trigger_type', table_name='workflows')
    op.drop_index('ix_workflows_company_id', table_name='workflows')
    op.drop_index('ix_workflows_id', table_name='workflows')
    op.drop_table('workflows')
