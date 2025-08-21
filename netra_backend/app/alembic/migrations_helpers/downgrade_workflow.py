"""
Database Downgrade Workflow Functions
Handles the teardown process during migration downgrade
"""

from alembic import op


def _drop_initial_tables() -> None:
    """Drop initial tables."""
    op.drop_table('steps')
    op.drop_table('messages')
    op.drop_table('analysis_results')
    op.drop_table('secrets')

def downgrade() -> None:
    """Downgrade schema."""
    _drop_initial_tables()
    _downgrade_p2()


def _drop_corpora_analyses() -> None:
    """Drop corpora and analyses tables."""
    op.drop_index(op.f('ix_corpora_name'), table_name='corpora')
    op.drop_table('corpora')
    op.drop_index(op.f('ix_analyses_name'), table_name='analyses')

def _downgrade_p2() -> None:
    """Downgrade part 2."""
    op.drop_table('runs')
    _drop_corpora_analyses()
    _downgrade_p3()


def _downgrade_p3() -> None:
    """Downgrade part 3."""
    op.drop_table('analyses')
    op.drop_index(op.f('ix_users_full_name'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    _downgrade_p4()


def _drop_supply_tables() -> None:
    """Drop supply-related tables."""
    op.drop_index(op.f('ix_supply_options_name'), table_name='supply_options')
    op.drop_table('supply_options')
    op.drop_index(op.f('ix_supplies_name'), table_name='supplies')

def _downgrade_p4() -> None:
    """Downgrade part 4."""
    op.drop_table('threads')
    _drop_supply_tables()
    _downgrade_p5()


def _downgrade_p5() -> None:
    """Downgrade part 5."""
    op.drop_table('supplies')
    op.drop_index(op.f('ix_references_name'), table_name='references')
    op.drop_table('references')
    op.drop_table('assistants')
    _downgrade_p6()


def _downgrade_p6() -> None:
    """Downgrade part 6."""
    op.drop_index(op.f('ix_apex_optimizer_agent_runs_run_id'), table_name='apex_optimizer_agent_runs')
    op.drop_table('apex_optimizer_agent_runs')
    op.drop_index(op.f('ix_apex_optimizer_agent_run_reports_run_id'), table_name='apex_optimizer_agent_run_reports')
    op.drop_table('apex_optimizer_agent_run_reports')