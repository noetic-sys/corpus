"""user_lookup_indicies

Revision ID: 937a7f8179e0
Revises: a40cb53a0189
Create Date: 2025-09-10 10:51:27.788488

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '937a7f8179e0'
down_revision: Union[str, Sequence[str], None] = 'a40cb53a0189'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create composite index for email + deleted lookups
    # This optimizes get_by_email() queries
    op.create_index(
        'ix_users_email_deleted', 
        'users', 
        ['email', 'deleted']
    )
    
    # Create composite index for SSO provider + user ID + deleted lookups  
    # This optimizes get_by_sso() queries
    op.create_index(
        'ix_users_sso_provider_user_id_deleted',
        'users',
        ['sso_provider', 'sso_user_id', 'deleted']
    )
    
    # Create composite index for company_id + deleted lookups
    # This optimizes get_by_company_id() queries  
    op.create_index(
        'ix_users_company_id_deleted',
        'users', 
        ['company_id', 'deleted']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indices in reverse order
    op.drop_index('ix_users_company_id_deleted', 'users')
    op.drop_index('ix_users_sso_provider_user_id_deleted', 'users')
    op.drop_index('ix_users_email_deleted', 'users')
