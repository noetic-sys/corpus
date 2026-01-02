"""add_ai_models_providers

Revision ID: 14802c835b3a
Revises: 38c7f6b94a1f
Create Date: 2025-08-03 14:42:52.085874

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '14802c835b3a'
down_revision: Union[str, Sequence[str], None] = '32bd92b38258'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create ai_providers table
    op.create_table('ai_providers',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_providers_enabled'), 'ai_providers', ['enabled'], unique=False)
    op.create_index(op.f('ix_ai_providers_id'), 'ai_providers', ['id'], unique=False)
    op.create_index(op.f('ix_ai_providers_name'), 'ai_providers', ['name'], unique=False)
    op.create_unique_constraint('uq_ai_providers_name', 'ai_providers', ['name'])
    
    # Create ai_models table
    op.create_table('ai_models',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('provider_id', sa.BigInteger(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('default_temperature', sa.Float(), nullable=False),
        sa.Column('default_max_tokens', sa.Integer(), nullable=True),
        sa.Column('enabled', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['provider_id'], ['ai_providers.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_models_enabled'), 'ai_models', ['enabled'], unique=False)
    op.create_index(op.f('ix_ai_models_id'), 'ai_models', ['id'], unique=False)
    op.create_index(op.f('ix_ai_models_model_name'), 'ai_models', ['model_name'], unique=False)
    op.create_index(op.f('ix_ai_models_provider_id'), 'ai_models', ['provider_id'], unique=False)
    
    # Add ai_model_id and ai_config_override columns to questions table
    op.add_column('questions', sa.Column('ai_model_id', sa.BigInteger(), nullable=True))
    op.add_column('questions', sa.Column('ai_config_override', sa.JSON(), nullable=True))
    op.create_index(op.f('ix_questions_ai_model_id'), 'questions', ['ai_model_id'], unique=False)
    op.create_foreign_key('fk_questions_ai_model_id', 'questions', 'ai_models', ['ai_model_id'], ['id'])
    
    # Insert default providers
    providers_table = sa.table('ai_providers',
        sa.column('name', sa.String),
        sa.column('display_name', sa.String),
        sa.column('enabled', sa.Boolean)
    )
    
    op.bulk_insert(providers_table, [
        {'name': 'openai', 'display_name': 'OpenAI', 'enabled': True},
        {'name': 'anthropic', 'display_name': 'Anthropic', 'enabled': True}
    ])
    
    # Insert default models
    models_table = sa.table('ai_models',
        sa.column('provider_id', sa.BigInteger),
        sa.column('model_name', sa.String),
        sa.column('display_name', sa.String),
        sa.column('default_temperature', sa.Float),
        sa.column('default_max_tokens', sa.Integer),
        sa.column('enabled', sa.Boolean)
    )
    
    op.bulk_insert(models_table, [
        # OpenAI models (provider_id = 1)
        {'provider_id': 1, 'model_name': 'gpt-4o', 'display_name': 'GPT-4o', 'default_temperature': 0.7, 'default_max_tokens': None, 'enabled': True},
        {'provider_id': 1, 'model_name': 'gpt-4o-mini', 'display_name': 'GPT-4o Mini', 'default_temperature': 0.7, 'default_max_tokens': None, 'enabled': True},
        {'provider_id': 1, 'model_name': 'gpt-4-turbo', 'display_name': 'GPT-4 Turbo', 'default_temperature': 0.7, 'default_max_tokens': None, 'enabled': True},
        {'provider_id': 1, 'model_name': 'gpt-4', 'display_name': 'GPT-4', 'default_temperature': 0.7, 'default_max_tokens': None, 'enabled': True},
        {'provider_id': 1, 'model_name': 'gpt-3.5-turbo', 'display_name': 'GPT-3.5 Turbo', 'default_temperature': 0.7, 'default_max_tokens': None, 'enabled': True},
        
        # Anthropic models (provider_id = 2)
        {'provider_id': 2, 'model_name': 'claude-3-5-sonnet-20241022', 'display_name': 'Claude 3.5 Sonnet (New)', 'default_temperature': 0.7, 'default_max_tokens': 4096, 'enabled': True},
        {'provider_id': 2, 'model_name': 'claude-3-5-sonnet-20240620', 'display_name': 'Claude 3.5 Sonnet', 'default_temperature': 0.7, 'default_max_tokens': 4096, 'enabled': True},
        {'provider_id': 2, 'model_name': 'claude-3-opus-20240229', 'display_name': 'Claude 3 Opus', 'default_temperature': 0.7, 'default_max_tokens': 4096, 'enabled': True},
        {'provider_id': 2, 'model_name': 'claude-3-sonnet-20240229', 'display_name': 'Claude 3 Sonnet', 'default_temperature': 0.7, 'default_max_tokens': 4096, 'enabled': True},
        {'provider_id': 2, 'model_name': 'claude-3-haiku-20240307', 'display_name': 'Claude 3 Haiku', 'default_temperature': 0.7, 'default_max_tokens': 4096, 'enabled': True}
    ]) 

def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key and columns from questions table
    op.drop_constraint('fk_questions_ai_model_id', 'questions', type_='foreignkey')
    op.drop_index(op.f('ix_questions_ai_model_id'), table_name='questions')
    op.drop_column('questions', 'ai_config_override')
    op.drop_column('questions', 'ai_model_id')
    
    # Drop ai_models table
    op.drop_index(op.f('ix_ai_models_provider_id'), table_name='ai_models')
    op.drop_index(op.f('ix_ai_models_model_name'), table_name='ai_models')
    op.drop_index(op.f('ix_ai_models_id'), table_name='ai_models')
    op.drop_index(op.f('ix_ai_models_enabled'), table_name='ai_models')
    op.drop_table('ai_models')
    
    # Drop ai_providers table
    op.drop_constraint('uq_ai_providers_name', 'ai_providers', type_='unique')
    op.drop_index(op.f('ix_ai_providers_name'), table_name='ai_providers')
    op.drop_index(op.f('ix_ai_providers_id'), table_name='ai_providers')
    op.drop_index(op.f('ix_ai_providers_enabled'), table_name='ai_providers')
    op.drop_table('ai_providers')
