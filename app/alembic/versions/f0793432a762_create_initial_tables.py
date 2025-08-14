"""create initial tables

Revision ID: f0793432a762
Revises: 29d08736f8b7
Create Date: 2025-08-09 08:45:22.040879

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0793432a762'
down_revision: Union[str, Sequence[str], None] = '29d08736f8b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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


def _create_assistants() -> None:
    """Create assistants table."""
    op.create_table('assistants',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('object', sa.String(), nullable=False),
        sa.Column('created_at', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'))


def _add_assistants_cols() -> None:
    """Add assistants columns."""
    op.add_column('assistants', sa.Column('description', sa.String(), nullable=True))
    op.add_column('assistants', sa.Column('model', sa.String(), nullable=False))
    op.add_column('assistants', sa.Column('instructions', sa.String(), nullable=True))
    op.add_column('assistants', sa.Column('tools', sa.JSON(), nullable=False))


def _add_assistants_final_cols() -> None:
    """Add final assistants columns."""
    op.add_column('assistants', sa.Column('file_ids', sa.ARRAY(sa.String()), nullable=False))
    op.add_column('assistants', sa.Column('metadata_', sa.JSON(), nullable=True))


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


def _create_threads() -> None:
    """Create threads table."""
    op.create_table('threads',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('object', sa.String(), nullable=False),
        sa.Column('created_at', sa.Integer(), nullable=False),
        sa.Column('metadata_', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'))


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


def _create_runs() -> None:
    """Create runs table."""
    op.create_table('runs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('object', sa.String(), nullable=False),
        sa.Column('created_at', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'))


def _add_runs_cols1() -> None:
    """Add runs columns part 1."""
    op.add_column('runs', sa.Column('assistant_id', sa.String(), nullable=False))
    op.add_column('runs', sa.Column('status', sa.String(), nullable=False))
    op.add_column('runs', sa.Column('required_action', sa.JSON(), nullable=True))
    op.add_column('runs', sa.Column('last_error', sa.JSON(), nullable=True))


def _add_runs_cols2() -> None:
    """Add runs columns part 2."""
    op.add_column('runs', sa.Column('expires_at', sa.Integer(), nullable=True))
    op.add_column('runs', sa.Column('started_at', sa.Integer(), nullable=True))
    op.add_column('runs', sa.Column('cancelled_at', sa.Integer(), nullable=True))
    op.add_column('runs', sa.Column('failed_at', sa.Integer(), nullable=True))


def _add_runs_cols3() -> None:
    """Add runs columns part 3."""
    op.add_column('runs', sa.Column('completed_at', sa.Integer(), nullable=True))
    op.add_column('runs', sa.Column('model', sa.String(), nullable=True))
    op.add_column('runs', sa.Column('instructions', sa.String(), nullable=True))
    op.add_column('runs', sa.Column('tools', sa.JSON(), nullable=False))


def _add_runs_final() -> None:
    """Add runs final columns and foreign keys."""
    op.add_column('runs', sa.Column('file_ids', sa.ARRAY(sa.String()), nullable=False))
    op.add_column('runs', sa.Column('metadata_', sa.JSON(), nullable=True))
    op.create_foreign_key(None, 'runs', 'assistants', ['assistant_id'], ['id'])
    op.create_foreign_key(None, 'runs', 'threads', ['thread_id'], ['id'])


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


def _create_messages() -> None:
    """Create messages table."""
    op.create_table('messages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('object', sa.String(), nullable=False),
        sa.Column('created_at', sa.Integer(), nullable=False),
        sa.Column('thread_id', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'))


def _add_messages_cols() -> None:
    """Add messages columns."""
    op.add_column('messages', sa.Column('role', sa.String(), nullable=False))
    op.add_column('messages', sa.Column('content', sa.JSON(), nullable=False))
    op.add_column('messages', sa.Column('assistant_id', sa.String(), nullable=True))
    op.add_column('messages', sa.Column('run_id', sa.String(), nullable=True))


def _add_messages_final() -> None:
    """Add messages final columns and foreign keys."""
    op.add_column('messages', sa.Column('file_ids', sa.ARRAY(sa.String()), nullable=False))
    op.add_column('messages', sa.Column('metadata_', sa.JSON(), nullable=True))
    op.create_foreign_key(None, 'messages', 'assistants', ['assistant_id'], ['id'])
    op.create_foreign_key(None, 'messages', 'runs', ['run_id'], ['id'])


def _add_messages_thread_fk() -> None:
    """Add messages thread foreign key."""
    op.create_foreign_key(None, 'messages', 'threads', ['thread_id'], ['id'])


def _create_steps() -> None:
    """Create steps table."""
    op.create_table('steps',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('object', sa.String(), nullable=False),
        sa.Column('created_at', sa.Integer(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id'))


def _add_steps_cols1() -> None:
    """Add steps columns part 1."""
    op.add_column('steps', sa.Column('assistant_id', sa.String(), nullable=False))
    op.add_column('steps', sa.Column('thread_id', sa.String(), nullable=False))
    op.add_column('steps', sa.Column('type', sa.String(), nullable=False))
    op.add_column('steps', sa.Column('status', sa.String(), nullable=False))


def _add_steps_cols2() -> None:
    """Add steps columns part 2."""
    op.add_column('steps', sa.Column('step_details', sa.JSON(), nullable=False))
    op.add_column('steps', sa.Column('last_error', sa.JSON(), nullable=True))
    op.add_column('steps', sa.Column('expired_at', sa.Integer(), nullable=True))
    op.add_column('steps', sa.Column('cancelled_at', sa.Integer(), nullable=True))


def _add_steps_cols3() -> None:
    """Add steps columns part 3."""
    op.add_column('steps', sa.Column('failed_at', sa.Integer(), nullable=True))
    op.add_column('steps', sa.Column('completed_at', sa.Integer(), nullable=True))
    op.add_column('steps', sa.Column('metadata_', sa.JSON(), nullable=True))


def _add_steps_fks() -> None:
    """Add steps foreign keys."""
    op.create_foreign_key(None, 'steps', 'assistants', ['assistant_id'], ['id'])
    op.create_foreign_key(None, 'steps', 'runs', ['run_id'], ['id'])
    op.create_foreign_key(None, 'steps', 'threads', ['thread_id'], ['id'])


def create_user_tables() -> None:
    """Create user-related tables."""
    _create_users()
    _add_users_cols()
    _add_users_indexes()
    _create_secrets()
    _add_secrets_final()


def create_agent_tables() -> None:
    """Create agent and AI-related tables."""
    _create_assistants()
    _add_assistants_cols()
    _add_assistants_final_cols()
    _create_threads()
    _create_runs()
    create_agent_runs_extended()


def create_agent_runs_extended() -> None:
    """Create extended agent runs."""
    _add_runs_cols1()
    _add_runs_cols2()
    _add_runs_cols3()
    _add_runs_final()
    _create_messages()
    create_messages_extended()


def create_messages_extended() -> None:
    """Create extended message tables."""
    _add_messages_cols()
    _add_messages_final()
    _add_messages_thread_fk()
    _create_steps()
    create_steps_extended()


def create_steps_extended() -> None:
    """Create extended step tables."""
    _add_steps_cols1()
    _add_steps_cols2()
    _add_steps_cols3()


def create_metric_tables() -> None:
    """Create metric and analysis tables."""
    _create_apex_reports()
    _create_apex_runs()
    _add_apex_runs_cols()
    _create_analyses()
    create_analysis_extended()


def create_analysis_extended() -> None:
    """Create extended analysis tables."""
    _add_analyses_cols()
    _create_analysis_results()
    _add_analysis_results_fk()
    _create_corpora()
    create_supply_tables()


def create_supply_tables() -> None:
    """Create supply-related tables."""
    _add_corpora_cols()
    _create_supplies()
    _add_supplies_final()
    _create_supply_options()
    create_supply_options_extended()


def create_supply_options_extended() -> None:
    """Create extended supply options."""
    _add_supply_options_cols()
    _add_supply_options_final()
    _create_references()
    _add_references_cols()
    _add_references_final_cols()


def create_index_definitions() -> None:
    """Create all index definitions."""
    _add_apex_reports_idx()
    _add_apex_runs_idx()
    _add_analyses_index()


def add_foreign_keys() -> None:
    """Add foreign key constraints."""
    _add_steps_fks()


def add_constraints() -> None:
    """Add additional constraints."""
    _add_corpora_final()


def upgrade() -> None:
    """Upgrade schema with organized table creation."""
    create_user_tables()
    create_agent_tables()
    create_metric_tables()
    create_index_definitions()
    add_foreign_keys()
    add_constraints()


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('steps')
    op.drop_table('messages')
    op.drop_table('analysis_results')
    op.drop_table('secrets')
    _downgrade_p2()


def _downgrade_p2() -> None:
    """Downgrade part 2."""
    op.drop_table('runs')
    op.drop_index(op.f('ix_corpora_name'), table_name='corpora')
    op.drop_table('corpora')
    op.drop_index(op.f('ix_analyses_name'), table_name='analyses')
    _downgrade_p3()


def _downgrade_p3() -> None:
    """Downgrade part 3."""
    op.drop_table('analyses')
    op.drop_index(op.f('ix_users_full_name'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    _downgrade_p4()


def _downgrade_p4() -> None:
    """Downgrade part 4."""
    op.drop_table('threads')
    op.drop_index(op.f('ix_supply_options_name'), table_name='supply_options')
    op.drop_table('supply_options')
    op.drop_index(op.f('ix_supplies_name'), table_name='supplies')
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