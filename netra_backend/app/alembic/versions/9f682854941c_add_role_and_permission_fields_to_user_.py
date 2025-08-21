"""Add role and permission fields to User model

Revision ID: 9f682854941c
Revises: cfb7e3adde23
Create Date: 2025-08-10 19:33:50.833896

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9f682854941c'
down_revision: Union[str, Sequence[str], None] = 'cfb7e3adde23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns to userbase table
    op.add_column('userbase', sa.Column('role', sa.String(), server_default='standard_user', nullable=True))
    op.add_column('userbase', sa.Column('permissions', sa.JSON(), server_default='{}', nullable=True))
    op.add_column('userbase', sa.Column('is_developer', sa.Boolean(), server_default='false', nullable=True))
    
    # Create index on role for faster queries
    op.create_index('ix_userbase_role', 'userbase', ['role'])


def downgrade() -> None:
    """Downgrade schema."""
    # Remove index
    op.drop_index('ix_userbase_role', 'userbase')
    
    # Remove columns
    op.drop_column('userbase', 'is_developer')
    op.drop_column('userbase', 'permissions')
    op.drop_column('userbase', 'role')
