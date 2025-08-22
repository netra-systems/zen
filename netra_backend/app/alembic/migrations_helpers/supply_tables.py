"""
Supply and Reference Table Creation Functions
Handles creation of supplies, supply_options, and references tables
"""

import sqlalchemy as sa

from alembic import op


def _create_references() -> None:
    """Create references table."""
    op.create_table('references',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('friendly_name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'))


def _add_references_cols() -> None:
    """Add references columns."""
    op.add_column('references', sa.Column('type', sa.String(), nullable=False))
    op.add_column('references', sa.Column('value', sa.String(), nullable=False))
    op.add_column('references', sa.Column('version', sa.String(), nullable=False))
    op.add_column('references', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))


def _add_references_final_cols() -> None:
    """Add final references columns and index."""
    op.add_column('references', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_references_name'), 'references', ['name'], unique=False)


def _create_supplies() -> None:
    """Create supplies table."""
    op.create_table('supplies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'))


def _add_supplies_final() -> None:
    """Add supplies final column and index."""
    op.add_column('supplies', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_supplies_name'), 'supplies', ['name'], unique=False)


def _create_supply_options() -> None:
    """Create supply options table."""
    op.create_table('supply_options',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('family', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'))


def _add_supply_options_cols() -> None:
    """Add supply options columns."""
    op.add_column('supply_options', sa.Column('hosting_type', sa.String(), nullable=True))
    op.add_column('supply_options', sa.Column('cost_per_million_tokens_usd', sa.JSON(), nullable=False))
    op.add_column('supply_options', sa.Column('quality_score', sa.Float(), nullable=False))
    op.add_column('supply_options', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))


def _add_supply_options_final() -> None:
    """Add supply options final column and index."""
    op.add_column('supply_options', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_supply_options_name'), 'supply_options', ['name'], unique=True)