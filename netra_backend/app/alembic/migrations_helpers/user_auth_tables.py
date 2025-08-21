"""
User and Authentication Table Creation Functions
Handles creation of user and authentication-related database tables
"""

from alembic import op
import sqlalchemy as sa


def _create_users() -> None:
    """Create users table."""
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('picture', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'))


def _add_users_cols() -> None:
    """Add users columns."""
    op.add_column('users', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.add_column('users', sa.Column('is_superuser', sa.Boolean(), nullable=True))


def _add_users_indexes() -> None:
    """Add users indexes."""
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_full_name'), 'users', ['full_name'], unique=False)


def _create_secrets() -> None:
    """Create secrets table."""
    op.create_table('secrets',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('encrypted_value', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'))


def _add_secrets_final() -> None:
    """Add secrets final columns and foreign key."""
    op.add_column('secrets', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('secrets', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(None, 'secrets', 'users', ['user_id'], ['id'])