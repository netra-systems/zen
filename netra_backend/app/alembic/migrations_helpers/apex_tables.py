"""
Apex Optimizer Table Creation Functions
Handles creation of Apex-related database tables
"""

from alembic import op
import sqlalchemy as sa


def _create_apex_reports() -> None:
    """Create apex optimizer reports table."""
    op.create_table('apex_optimizer_agent_run_reports',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('report', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'))


def _add_apex_reports_idx() -> None:
    """Add apex reports index."""
    op.create_index(op.f('ix_apex_optimizer_agent_run_reports_run_id'),
                   'apex_optimizer_agent_run_reports', ['run_id'], unique=True)


def _create_apex_runs() -> None:
    """Create apex optimizer runs table."""
    op.create_table('apex_optimizer_agent_runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('step_name', sa.String(), nullable=False),
        sa.Column('step_input', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'))


def _add_apex_runs_cols() -> None:
    """Add remaining apex runs columns."""
    op.add_column('apex_optimizer_agent_runs',
                 sa.Column('step_output', sa.JSON(), nullable=True))
    op.add_column('apex_optimizer_agent_runs',
                 sa.Column('run_log', sa.String(), nullable=True))
    op.add_column('apex_optimizer_agent_runs',
                 sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True))


def _add_apex_runs_idx() -> None:
    """Add apex runs index."""
    op.create_index(op.f('ix_apex_optimizer_agent_runs_run_id'),
                   'apex_optimizer_agent_runs', ['run_id'], unique=False)