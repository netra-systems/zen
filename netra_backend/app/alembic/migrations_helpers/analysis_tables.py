"""
Analysis and Corpus Table Creation Functions
Handles creation of analysis, analysis_results, and corpora tables
"""

import sqlalchemy as sa

from alembic import op


def _create_analyses() -> None:
    """Create analyses table."""
    op.create_table('analyses',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'))


def _add_analyses_cols() -> None:
    """Add analyses columns."""
    op.add_column('analyses', sa.Column('created_by_id', sa.String(), nullable=True))
    op.add_column('analyses', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('analyses', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(None, 'analyses', 'users', ['created_by_id'], ['id'])


def _add_analyses_index() -> None:
    """Add analyses index."""
    op.create_index(op.f('ix_analyses_name'), 'analyses', ['name'], unique=False)


def _create_corpora() -> None:
    """Create corpora table."""
    op.create_table('corpora',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('table_name', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'))


def _add_corpora_cols() -> None:
    """Add corpora columns."""
    op.add_column('corpora', sa.Column('status', sa.String(), nullable=True))
    op.add_column('corpora', sa.Column('created_by_id', sa.String(), nullable=True))
    op.add_column('corpora', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('corpora', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def _add_corpora_final() -> None:
    """Add corpora foreign key and index."""
    op.create_foreign_key(None, 'corpora', 'users', ['created_by_id'], ['id'])
    op.create_index(op.f('ix_corpora_name'), 'corpora', ['name'], unique=True)


def _create_analysis_results() -> None:
    """Create analysis results table."""
    op.create_table('analysis_results',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('analysis_id', sa.String(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'))


def _add_analysis_results_fk() -> None:
    """Add analysis results foreign key."""
    op.create_foreign_key(None, 'analysis_results', 'analyses', ['analysis_id'], ['id'])