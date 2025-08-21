"""
Agent and AI System Table Creation Functions
Handles creation of agent, assistant, thread, run, message, and step tables
"""

from alembic import op
import sqlalchemy as sa


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


def _create_threads() -> None:
    """Create threads table."""
    op.create_table('threads',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('object', sa.String(), nullable=False),
        sa.Column('created_at', sa.Integer(), nullable=False),
        sa.Column('metadata_', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'))


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