"""Rename users table to userbase

Revision ID: a12de78b4ee4
Revises: f0793432a762
Create Date: 2025-08-09 09:06:14.576239

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a12de78b4ee4'
down_revision: Union[str, Sequence[str], None] = 'f0793432a762'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table('users', 'userbase')
    op.drop_constraint('secrets_user_id_fkey', 'secrets', type_='foreignkey')
    op.create_foreign_key('secrets_user_id_fkey', 'secrets', 'userbase', ['user_id'], ['id'])
    op.drop_constraint('analyses_created_by_id_fkey', 'analyses', type_='foreignkey')
    op.create_foreign_key('analyses_created_by_id_fkey', 'analyses', 'userbase', ['created_by_id'], ['id'])
    op.drop_constraint('corpora_created_by_id_fkey', 'corpora', type_='foreignkey')
    op.create_foreign_key('corpora_created_by_id_fkey', 'corpora', 'userbase', ['created_by_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.rename_table('userbase', 'users')
    op.drop_constraint('secrets_user_id_fkey', 'secrets', type_='foreignkey')
    op.create_foreign_key('secrets_user_id_fkey', 'secrets', 'users', ['user_id'], ['id'])
    op.drop_constraint('analyses_created_by_id_fkey', 'analyses', type_='foreignkey')
    op.create_foreign_key('analyses_created_by_id_fkey', 'analyses', 'users', ['created_by_id'], ['id'])
    op.drop_constraint('corpora_created_by_id_fkey', 'corpora', type_='foreignkey')
    op.create_foreign_key('corpora_created_by_id_fkey', 'corpora', 'users', ['created_by_id'], ['id'])
