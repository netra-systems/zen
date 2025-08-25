"""add_missing_tables_and_columns_complete

Revision ID: 66e0e5d9662d
Revises: bb39e1c49e2d
Create Date: 2025-08-17 20:08:36.994517

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '66e0e5d9662d'
down_revision: Union[str, Sequence[str], None] = 'bb39e1c49e2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def create_mcp_tables() -> None:
    """Create MCP external server tables."""
    _create_mcp_external_servers_table()
    _create_mcp_resource_and_tool_tables()


def _create_mcp_external_servers_table() -> None:
    """Create MCP external servers table and columns."""
    _create_mcp_external_servers()
    _add_mcp_external_servers_remaining_columns()
    _add_mcp_external_servers_constraints()


def _create_mcp_resource_and_tool_tables() -> None:
    """Create MCP resource and tool tables."""
    _create_mcp_resource_access()
    _create_mcp_tool_executions()
    _add_mcp_tool_executions_remaining_columns()
    _add_mcp_tool_executions_constraints()


def _create_mcp_external_servers() -> None:
    """Create mcp_external_servers table."""
    _create_mcp_external_servers_core()
    _create_mcp_external_servers_auth()


def _create_mcp_external_servers_core() -> None:
    """Create mcp_external_servers core structure."""
    op.create_table('mcp_external_servers',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('transport', sa.String(length=20), nullable=False))


def _create_mcp_external_servers_auth() -> None:
    """Add auth and metadata columns to mcp_external_servers."""
    op.add_column('mcp_external_servers', sa.Column('auth_type', sa.String(length=50), nullable=True))
    op.add_column('mcp_external_servers', sa.Column('credentials', sa.JSON(), nullable=True))
    op.add_column('mcp_external_servers', sa.Column('capabilities', sa.JSON(), nullable=True))
    op.add_column('mcp_external_servers', sa.Column('metadata_', sa.JSON(), nullable=True))


def _add_mcp_external_servers_remaining_columns() -> None:
    """Add remaining columns to mcp_external_servers."""
    op.add_column('mcp_external_servers', sa.Column('status', sa.String(length=20), nullable=False))
    op.add_column('mcp_external_servers', sa.Column('last_health_check', sa.DateTime(), nullable=True))
    op.add_column('mcp_external_servers', sa.Column('created_at', sa.DateTime(), nullable=False))
    op.add_column('mcp_external_servers', sa.Column('updated_at', sa.DateTime(), nullable=False))


def _add_mcp_external_servers_constraints() -> None:
    """Add constraints to mcp_external_servers."""
    op.create_primary_key('mcp_external_servers_pkey', 'mcp_external_servers', ['id'])
    op.create_unique_constraint('mcp_external_servers_name_key', 'mcp_external_servers', ['name'])


def _add_mcp_tool_executions_remaining_columns() -> None:
    """Add remaining columns to mcp_tool_executions."""
    op.add_column('mcp_tool_executions', sa.Column('user_id', sa.String(), nullable=True))
    op.add_column('mcp_tool_executions', sa.Column('created_at', sa.DateTime(), nullable=False))


def _add_mcp_tool_executions_constraints() -> None:
    """Add constraints to mcp_tool_executions."""
    op.create_primary_key('mcp_tool_executions_pkey', 'mcp_tool_executions', ['id'])


def _create_mcp_resource_access() -> None:
    """Create mcp_resource_access table."""
    _create_mcp_resource_access_core()
    _create_mcp_resource_access_metadata()


def _create_mcp_resource_access_core() -> None:
    """Create mcp_resource_access core structure."""
    op.create_table('mcp_resource_access',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('server_name', sa.String(length=255), nullable=False),
        sa.Column('resource_uri', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=True))


def _create_mcp_resource_access_metadata() -> None:
    """Add metadata columns to mcp_resource_access."""
    op.add_column('mcp_resource_access', sa.Column('status', sa.String(length=20), nullable=False))
    op.add_column('mcp_resource_access', sa.Column('user_id', sa.String(), nullable=True))
    op.add_column('mcp_resource_access', sa.Column('created_at', sa.DateTime(), nullable=False))
    op.create_primary_key('mcp_resource_access_pkey', 'mcp_resource_access', ['id'])


def _create_mcp_tool_executions() -> None:
    """Create mcp_tool_executions table."""
    _create_mcp_tool_executions_core()
    _create_mcp_tool_executions_metadata()


def _create_mcp_tool_executions_core() -> None:
    """Create mcp_tool_executions core structure."""
    op.create_table('mcp_tool_executions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('server_name', sa.String(length=255), nullable=False),
        sa.Column('tool_name', sa.String(length=255), nullable=False),
        sa.Column('arguments', sa.JSON(), nullable=False))


def _create_mcp_tool_executions_metadata() -> None:
    """Add metadata columns to mcp_tool_executions."""
    op.add_column('mcp_tool_executions', sa.Column('result', sa.JSON(), nullable=True))
    op.add_column('mcp_tool_executions', sa.Column('status', sa.String(length=20), nullable=False))
    op.add_column('mcp_tool_executions', sa.Column('execution_time_ms', sa.Integer(), nullable=True))
    op.add_column('mcp_tool_executions', sa.Column('error_message', sa.Text(), nullable=True))


def create_agent_state_tables() -> None:
    """Create agent state management tables."""
    _create_agent_snapshots_table()
    _create_audit_logs_table()


def _create_agent_snapshots_table() -> None:
    """Create agent state snapshots table."""
    _create_agent_state_snapshots()
    _create_agent_state_snapshots_columns()
    _create_agent_state_snapshots_constraints()
    _create_agent_state_snapshots_indexes()


def _create_audit_logs_table() -> None:
    """Create corpus audit logs table."""
    _create_corpus_audit_logs()
    _create_corpus_audit_logs_columns()
    _create_corpus_audit_logs_constraints()
    _create_corpus_audit_logs_indexes()


def _create_all_agent_tables() -> None:
    """Create remaining agent tables."""
    _create_recovery_logs_table()
    _create_state_transactions_table()


def _create_recovery_logs_table() -> None:
    """Create agent recovery logs table."""
    _create_agent_recovery_logs()
    _create_agent_recovery_logs_columns()
    _create_agent_recovery_logs_constraints()
    _create_agent_recovery_logs_indexes()


def _create_state_transactions_table() -> None:
    """Create agent state transactions table."""
    _create_agent_state_transactions()
    _create_agent_state_transactions_columns()
    _create_agent_state_transactions_constraints()
    _create_agent_state_transactions_indexes()


def _create_agent_state_snapshots() -> None:
    """Create agent_state_snapshots table."""
    _create_agent_state_snapshots_core()
    _create_agent_state_snapshots_identifiers()


def _create_agent_state_snapshots_core() -> None:
    """Create agent_state_snapshots core structure."""
    op.create_table('agent_state_snapshots',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('thread_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False))


def _create_agent_state_snapshots_identifiers() -> None:
    """Add identifier columns to agent_state_snapshots."""
    op.add_column('agent_state_snapshots', sa.Column('version', sa.String(), nullable=False))
    op.add_column('agent_state_snapshots', sa.Column('schema_version', sa.String(), nullable=False))
    op.add_column('agent_state_snapshots', sa.Column('checkpoint_type', sa.String(), nullable=False))


def _create_agent_state_snapshots_columns() -> None:
    """Add remaining columns to agent_state_snapshots."""
    _add_agent_state_snapshots_core_columns()
    _add_agent_state_snapshots_meta_columns()


def _add_agent_state_snapshots_core_columns() -> None:
    """Add core columns to agent_state_snapshots."""
    op.add_column('agent_state_snapshots', sa.Column('state_data', sa.JSON(), nullable=False))
    op.add_column('agent_state_snapshots', sa.Column('serialization_format', sa.String(), nullable=False))
    op.add_column('agent_state_snapshots', sa.Column('compression_type', sa.String(), nullable=True))
    op.add_column('agent_state_snapshots', sa.Column('step_count', sa.Integer(), nullable=False))


def _add_agent_state_snapshots_meta_columns() -> None:
    """Add metadata columns to agent_state_snapshots."""
    op.add_column('agent_state_snapshots', sa.Column('agent_phase', sa.String(), nullable=True))
    op.add_column('agent_state_snapshots', sa.Column('execution_context', sa.JSON(), nullable=True))
    op.add_column('agent_state_snapshots', sa.Column('created_at', sa.DateTime(timezone=True), nullable=True))


def _create_agent_state_snapshots_constraints() -> None:
    """Add constraints to agent_state_snapshots."""
    _add_agent_state_snapshots_recovery_columns()
    _add_agent_state_snapshots_constraints_final()


def _add_agent_state_snapshots_recovery_columns() -> None:
    """Add recovery columns to agent_state_snapshots."""
    op.add_column('agent_state_snapshots', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agent_state_snapshots', sa.Column('is_recovery_point', sa.Boolean(), nullable=True))
    op.add_column('agent_state_snapshots', sa.Column('recovery_reason', sa.String(), nullable=True))
    op.add_column('agent_state_snapshots', sa.Column('parent_snapshot_id', sa.String(), nullable=True))


def _add_agent_state_snapshots_constraints_final() -> None:
    """Add final constraints to agent_state_snapshots."""
    # Create primary key FIRST before foreign keys
    op.create_primary_key('agent_state_snapshots_pkey', 'agent_state_snapshots', ['id'])
    # Now create foreign keys that reference the primary key
    op.create_foreign_key(None, 'agent_state_snapshots', 'agent_state_snapshots', ['parent_snapshot_id'], ['id'])
    op.create_foreign_key(None, 'agent_state_snapshots', 'userbase', ['user_id'], ['id'])


def _create_agent_state_snapshots_indexes() -> None:
    """Create indexes for agent_state_snapshots."""
    _create_agent_state_custom_indexes()
    _create_agent_state_standard_indexes()


def _create_agent_state_custom_indexes() -> None:
    """Create custom indexes for agent_state_snapshots."""
    op.create_index('idx_agent_state_expires', 'agent_state_snapshots', ['expires_at'], unique=False)
    op.create_index('idx_agent_state_recovery', 'agent_state_snapshots', ['is_recovery_point', 'created_at'], unique=False)
    op.create_index('idx_agent_state_run_created', 'agent_state_snapshots', ['run_id', 'created_at'], unique=False)
    op.create_index('idx_agent_state_thread_created', 'agent_state_snapshots', ['thread_id', 'created_at'], unique=False)


def _create_agent_state_standard_indexes() -> None:
    """Create standard indexes for agent_state_snapshots."""
    op.create_index(op.f('ix_agent_state_snapshots_created_at'), 'agent_state_snapshots', ['created_at'], unique=False)
    op.create_index(op.f('ix_agent_state_snapshots_expires_at'), 'agent_state_snapshots', ['expires_at'], unique=False)
    op.create_index(op.f('ix_agent_state_snapshots_run_id'), 'agent_state_snapshots', ['run_id'], unique=False)
    op.create_index(op.f('ix_agent_state_snapshots_thread_id'), 'agent_state_snapshots', ['thread_id'], unique=False)


def _create_corpus_audit_logs() -> None:
    """Create corpus_audit_logs table."""
    _create_corpus_audit_logs_core()
    _create_corpus_audit_logs_status()


def _create_corpus_audit_logs_core() -> None:
    """Create corpus_audit_logs core structure."""
    op.create_table('corpus_audit_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('action', sa.String(), nullable=False))


def _create_corpus_audit_logs_status() -> None:
    """Add status columns to corpus_audit_logs."""
    op.add_column('corpus_audit_logs', sa.Column('status', sa.String(), nullable=False))
    op.add_column('corpus_audit_logs', sa.Column('corpus_id', sa.String(), nullable=True))
    op.add_column('corpus_audit_logs', sa.Column('resource_type', sa.String(), nullable=False))


def _create_corpus_audit_logs_columns() -> None:
    """Add remaining columns to corpus_audit_logs."""
    _add_corpus_audit_logs_tracking_columns()
    _add_corpus_audit_logs_request_columns()


def _add_corpus_audit_logs_tracking_columns() -> None:
    """Add tracking columns to corpus_audit_logs."""
    op.add_column('corpus_audit_logs', sa.Column('resource_id', sa.String(), nullable=True))
    op.add_column('corpus_audit_logs', sa.Column('operation_duration_ms', sa.Float(), nullable=True))
    op.add_column('corpus_audit_logs', sa.Column('result_data', sa.JSON(), nullable=True))
    op.add_column('corpus_audit_logs', sa.Column('user_agent', sa.String(), nullable=True))


def _add_corpus_audit_logs_request_columns() -> None:
    """Add request tracking columns to corpus_audit_logs."""
    op.add_column('corpus_audit_logs', sa.Column('ip_address', sa.String(), nullable=True))
    op.add_column('corpus_audit_logs', sa.Column('request_id', sa.String(), nullable=True))
    op.add_column('corpus_audit_logs', sa.Column('session_id', sa.String(), nullable=True))


def _create_corpus_audit_logs_constraints() -> None:
    """Add constraints to corpus_audit_logs."""
    _add_corpus_audit_logs_metadata_columns()
    _add_corpus_audit_logs_final_constraints()


def _add_corpus_audit_logs_metadata_columns() -> None:
    """Add metadata columns to corpus_audit_logs."""
    op.add_column('corpus_audit_logs', sa.Column('configuration', sa.JSON(), nullable=True))
    op.add_column('corpus_audit_logs', sa.Column('performance_metrics', sa.JSON(), nullable=True))
    op.add_column('corpus_audit_logs', sa.Column('error_details', sa.JSON(), nullable=True))
    op.add_column('corpus_audit_logs', sa.Column('compliance_flags', sa.ARRAY(sa.String()), nullable=True))


def _add_corpus_audit_logs_final_constraints() -> None:
    """Add final constraints to corpus_audit_logs."""
    op.create_foreign_key(None, 'corpus_audit_logs', 'userbase', ['user_id'], ['id'])
    op.create_primary_key('corpus_audit_logs_pkey', 'corpus_audit_logs', ['id'])


def _create_corpus_audit_logs_indexes() -> None:
    """Create indexes for corpus_audit_logs."""
    _create_corpus_audit_action_indexes()
    _create_corpus_audit_tracking_indexes()


def _create_corpus_audit_action_indexes() -> None:
    """Create action-related indexes for corpus_audit_logs."""
    op.create_index(op.f('ix_corpus_audit_logs_action'), 'corpus_audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_corpus_audit_logs_corpus_id'), 'corpus_audit_logs', ['corpus_id'], unique=False)
    op.create_index(op.f('ix_corpus_audit_logs_resource_type'), 'corpus_audit_logs', ['resource_type'], unique=False)
    op.create_index(op.f('ix_corpus_audit_logs_status'), 'corpus_audit_logs', ['status'], unique=False)


def _create_corpus_audit_tracking_indexes() -> None:
    """Create tracking indexes for corpus_audit_logs."""
    op.create_index(op.f('ix_corpus_audit_logs_ip_address'), 'corpus_audit_logs', ['ip_address'], unique=False)
    op.create_index(op.f('ix_corpus_audit_logs_request_id'), 'corpus_audit_logs', ['request_id'], unique=False)
    op.create_index(op.f('ix_corpus_audit_logs_resource_id'), 'corpus_audit_logs', ['resource_id'], unique=False)
    op.create_index(op.f('ix_corpus_audit_logs_session_id'), 'corpus_audit_logs', ['session_id'], unique=False)


def _create_agent_recovery_logs() -> None:
    """Create agent_recovery_logs table."""
    _create_agent_recovery_logs_core()
    _create_agent_recovery_logs_snapshots()


def _create_agent_recovery_logs_core() -> None:
    """Create agent_recovery_logs core structure."""
    op.create_table('agent_recovery_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('thread_id', sa.String(), nullable=False),
        sa.Column('recovery_type', sa.String(), nullable=False))


def _create_agent_recovery_logs_snapshots() -> None:
    """Add snapshot columns to agent_recovery_logs."""
    op.add_column('agent_recovery_logs', sa.Column('source_snapshot_id', sa.String(), nullable=True))
    op.add_column('agent_recovery_logs', sa.Column('target_snapshot_id', sa.String(), nullable=True))
    op.add_column('agent_recovery_logs', sa.Column('failure_reason', sa.String(), nullable=True))


def _create_agent_recovery_logs_columns() -> None:
    """Add remaining columns to agent_recovery_logs."""
    _add_agent_recovery_logs_status_columns()
    _add_agent_recovery_logs_data_columns()


def _add_agent_recovery_logs_status_columns() -> None:
    """Add status columns to agent_recovery_logs."""
    op.add_column('agent_recovery_logs', sa.Column('trigger_event', sa.String(), nullable=False))
    op.add_column('agent_recovery_logs', sa.Column('auto_recovery', sa.Boolean(), nullable=True))
    op.add_column('agent_recovery_logs', sa.Column('recovery_status', sa.String(), nullable=False))
    op.add_column('agent_recovery_logs', sa.Column('recovery_time_ms', sa.Integer(), nullable=True))


def _add_agent_recovery_logs_data_columns() -> None:
    """Add data tracking columns to agent_recovery_logs."""
    op.add_column('agent_recovery_logs', sa.Column('recovered_data', sa.JSON(), nullable=True))
    op.add_column('agent_recovery_logs', sa.Column('lost_data', sa.JSON(), nullable=True))
    op.add_column('agent_recovery_logs', sa.Column('data_integrity_score', sa.Integer(), nullable=True))


def _create_agent_recovery_logs_constraints() -> None:
    """Add constraints to agent_recovery_logs."""
    _add_agent_recovery_logs_timing_columns()
    _add_agent_recovery_logs_final_constraints()


def _add_agent_recovery_logs_timing_columns() -> None:
    """Add timing columns to agent_recovery_logs."""
    op.add_column('agent_recovery_logs', sa.Column('data_size_kb', sa.Integer(), nullable=True))
    op.add_column('agent_recovery_logs', sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agent_recovery_logs', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))


def _add_agent_recovery_logs_final_constraints() -> None:
    """Add final constraints to agent_recovery_logs."""
    op.create_foreign_key(None, 'agent_recovery_logs', 'agent_state_snapshots', ['source_snapshot_id'], ['id'])
    op.create_foreign_key(None, 'agent_recovery_logs', 'agent_state_snapshots', ['target_snapshot_id'], ['id'])
    op.create_primary_key('agent_recovery_logs_pkey', 'agent_recovery_logs', ['id'])


def _create_agent_recovery_logs_indexes() -> None:
    """Create indexes for agent_recovery_logs."""
    op.create_index('idx_recovery_auto', 'agent_recovery_logs', ['auto_recovery', 'initiated_at'], unique=False)
    op.create_index('idx_recovery_run_initiated', 'agent_recovery_logs', ['run_id', 'initiated_at'], unique=False)
    op.create_index('idx_recovery_status', 'agent_recovery_logs', ['recovery_status'], unique=False)
    op.create_index(op.f('ix_agent_recovery_logs_run_id'), 'agent_recovery_logs', ['run_id'], unique=False)
    op.create_index(op.f('ix_agent_recovery_logs_thread_id'), 'agent_recovery_logs', ['thread_id'], unique=False)


def _create_agent_state_transactions() -> None:
    """Create agent_state_transactions table."""
    _create_agent_state_transactions_core()
    _create_agent_state_transactions_changes()


def _create_agent_state_transactions_core() -> None:
    """Create agent_state_transactions core structure."""
    op.create_table('agent_state_transactions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('snapshot_id', sa.String(), nullable=False),
        sa.Column('run_id', sa.String(), nullable=False),
        sa.Column('operation_type', sa.String(), nullable=False))


def _create_agent_state_transactions_changes() -> None:
    """Add change tracking columns to agent_state_transactions."""
    op.add_column('agent_state_transactions', sa.Column('field_changes', sa.JSON(), nullable=True))
    op.add_column('agent_state_transactions', sa.Column('previous_values', sa.JSON(), nullable=True))
    op.add_column('agent_state_transactions', sa.Column('triggered_by', sa.String(), nullable=False))


def _create_agent_state_transactions_columns() -> None:
    """Add remaining columns to agent_state_transactions."""
    _add_agent_state_transactions_execution_columns()
    _add_agent_state_transactions_timing_columns()


def _add_agent_state_transactions_execution_columns() -> None:
    """Add execution columns to agent_state_transactions."""
    op.add_column('agent_state_transactions', sa.Column('execution_phase', sa.String(), nullable=True))
    op.add_column('agent_state_transactions', sa.Column('execution_time_ms', sa.Integer(), nullable=True))
    op.add_column('agent_state_transactions', sa.Column('memory_usage_mb', sa.Integer(), nullable=True))
    op.add_column('agent_state_transactions', sa.Column('status', sa.String(), nullable=False))


def _add_agent_state_transactions_timing_columns() -> None:
    """Add timing columns to agent_state_transactions."""
    op.add_column('agent_state_transactions', sa.Column('error_message', sa.Text(), nullable=True))
    op.add_column('agent_state_transactions', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('agent_state_transactions', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))


def _create_agent_state_transactions_constraints() -> None:
    """Add constraints to agent_state_transactions."""
    op.create_foreign_key(None, 'agent_state_transactions', 'agent_state_snapshots', ['snapshot_id'], ['id'])
    op.create_primary_key('agent_state_transactions_pkey', 'agent_state_transactions', ['id'])


def _create_agent_state_transactions_indexes() -> None:
    """Create indexes for agent_state_transactions."""
    op.create_index('idx_state_tx_run_status', 'agent_state_transactions', ['run_id', 'status'], unique=False)
    op.create_index('idx_state_tx_started', 'agent_state_transactions', ['started_at'], unique=False)
    op.create_index(op.f('ix_agent_state_transactions_run_id'), 'agent_state_transactions', ['run_id'], unique=False)
    op.create_index(op.f('ix_agent_state_transactions_snapshot_id'), 'agent_state_transactions', ['snapshot_id'], unique=False)


def modify_existing_tables() -> None:
    """Modify existing database tables."""
    _modify_ai_supply_items_table()
    _modify_corpora_table()
    _modify_research_sessions_table()
    _modify_supply_update_logs_table()
    _modify_tool_usage_logs_table()
    _modify_userbase_table()


def _modify_ai_supply_items_table() -> None:
    """Modify ai_supply_items table structure."""
    _add_ai_supply_items_columns()
    _add_ai_supply_items_metadata_columns()
    _alter_ai_supply_items_columns()
    _create_ai_supply_items_indexes()
    _drop_ai_supply_items_columns()


def _add_ai_supply_items_columns() -> None:
    """Add new columns to ai_supply_items."""
    _add_ai_supply_items_pricing_columns()
    _add_ai_supply_items_capability_columns()


def _add_ai_supply_items_pricing_columns() -> None:
    """Add pricing columns to ai_supply_items."""
    op.add_column('ai_supply_items', sa.Column('model_version', sa.String(), nullable=True))
    op.add_column('ai_supply_items', sa.Column('pricing_input', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('ai_supply_items', sa.Column('pricing_output', sa.Numeric(precision=10, scale=4), nullable=True))
    op.add_column('ai_supply_items', sa.Column('pricing_currency', sa.String(), nullable=True))


def _add_ai_supply_items_capability_columns() -> None:
    """Add capability columns to ai_supply_items."""
    op.add_column('ai_supply_items', sa.Column('context_window', sa.Integer(), nullable=True))
    op.add_column('ai_supply_items', sa.Column('max_output_tokens', sa.Integer(), nullable=True))
    op.add_column('ai_supply_items', sa.Column('capabilities', sa.JSON(), nullable=True))
    op.add_column('ai_supply_items', sa.Column('availability_status', sa.String(), nullable=True))


def _add_ai_supply_items_metadata_columns() -> None:
    """Add metadata columns to ai_supply_items."""
    op.add_column('ai_supply_items', sa.Column('api_endpoints', sa.JSON(), nullable=True))
    op.add_column('ai_supply_items', sa.Column('performance_metrics', sa.JSON(), nullable=True))
    op.add_column('ai_supply_items', sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True))
    op.add_column('ai_supply_items', sa.Column('research_source', sa.String(), nullable=True))
    op.add_column('ai_supply_items', sa.Column('confidence_score', sa.Float(), nullable=True))


def _alter_ai_supply_items_columns() -> None:
    """Alter existing ai_supply_items columns."""
    op.alter_column('ai_supply_items', 'created_at',
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        nullable=True,
        existing_server_default=sa.text('now()'))


def _create_ai_supply_items_indexes() -> None:
    """Create indexes for ai_supply_items."""
    op.create_index(op.f('ix_ai_supply_items_model_name'), 'ai_supply_items', ['model_name'], unique=False)
    op.create_index(op.f('ix_ai_supply_items_provider'), 'ai_supply_items', ['provider'], unique=False)


def _drop_ai_supply_items_columns() -> None:
    """Drop obsolete ai_supply_items columns."""
    op.drop_column('ai_supply_items', 'cost_per_token')
    op.drop_column('ai_supply_items', 'metadata_')
    op.drop_column('ai_supply_items', 'updated_at')
    op.drop_column('ai_supply_items', 'name')


def _modify_corpora_table() -> None:
    """Modify corpora table structure."""
    op.add_column('corpora', sa.Column('domain', sa.String(), nullable=True))
    op.add_column('corpora', sa.Column('metadata_', sa.JSON(), nullable=True))


def _modify_research_sessions_table() -> None:
    """Modify research_sessions table structure."""
    _add_research_sessions_columns()
    _alter_research_sessions_columns()
    _drop_research_sessions_columns()


def _add_research_sessions_columns() -> None:
    """Add new columns to research_sessions."""
    _add_research_sessions_core_columns()
    _add_research_sessions_data_columns()


def _add_research_sessions_core_columns() -> None:
    """Add core columns to research_sessions."""
    op.add_column('research_sessions', sa.Column('query', sa.Text(), nullable=False))
    op.add_column('research_sessions', sa.Column('session_id', sa.String(), nullable=True))
    op.add_column('research_sessions', sa.Column('research_plan', sa.JSON(), nullable=True))
    op.add_column('research_sessions', sa.Column('questions_answered', sa.JSON(), nullable=True))


def _add_research_sessions_data_columns() -> None:
    """Add data columns to research_sessions."""
    op.add_column('research_sessions', sa.Column('raw_results', sa.JSON(), nullable=True))
    op.add_column('research_sessions', sa.Column('processed_data', sa.JSON(), nullable=True))
    op.add_column('research_sessions', sa.Column('citations', sa.JSON(), nullable=True))
    op.add_column('research_sessions', sa.Column('initiated_by', sa.String(), nullable=True))


def _add_research_sessions_completion_columns() -> None:
    """Add completion tracking columns to research_sessions."""
    op.add_column('research_sessions', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('research_sessions', sa.Column('error_message', sa.Text(), nullable=True))


def _alter_research_sessions_columns() -> None:
    """Alter existing research_sessions columns."""
    op.alter_column('research_sessions', 'created_at',
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        nullable=True,
        existing_server_default=sa.text('now()'))


def _drop_research_sessions_columns() -> None:
    """Drop obsolete research_sessions columns."""
    op.drop_column('research_sessions', 'topic')
    op.drop_column('research_sessions', 'updated_at')
    op.drop_column('research_sessions', 'user_id')
    op.drop_column('research_sessions', 'findings')


def _modify_supply_update_logs_table() -> None:
    """Modify supply_update_logs table structure."""
    _add_supply_update_logs_columns()
    _alter_supply_update_logs_columns()
    _create_supply_update_logs_foreign_keys()
    _drop_supply_update_logs_columns()


def _add_supply_update_logs_columns() -> None:
    """Add new columns to supply_update_logs."""
    op.add_column('supply_update_logs', sa.Column('field_updated', sa.String(), nullable=False))
    op.add_column('supply_update_logs', sa.Column('research_session_id', sa.String(), nullable=True))
    op.add_column('supply_update_logs', sa.Column('update_reason', sa.String(), nullable=True))
    op.add_column('supply_update_logs', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def _alter_supply_update_logs_columns() -> None:
    """Alter existing supply_update_logs columns."""
    op.alter_column('supply_update_logs', 'supply_item_id',
        existing_type=sa.VARCHAR(),
        nullable=False)
    op.alter_column('supply_update_logs', 'updated_by',
        existing_type=sa.VARCHAR(),
        nullable=False)


def _create_supply_update_logs_foreign_keys() -> None:
    """Create foreign key constraints for supply_update_logs."""
    op.create_foreign_key(None, 'supply_update_logs', 'ai_supply_items', ['supply_item_id'], ['id'])
    op.create_foreign_key(None, 'supply_update_logs', 'research_sessions', ['research_session_id'], ['id'])


def _drop_supply_update_logs_columns() -> None:
    """Drop obsolete supply_update_logs columns."""
    op.drop_column('supply_update_logs', 'created_at')
    op.drop_column('supply_update_logs', 'update_type')


def _modify_tool_usage_logs_table() -> None:
    """Modify tool_usage_logs table structure."""
    _add_tool_usage_logs_columns()
    _alter_tool_usage_logs_columns()
    _create_tool_usage_logs_indexes()
    _create_tool_usage_logs_foreign_keys()
    _drop_tool_usage_logs_columns()


def _add_tool_usage_logs_columns() -> None:
    """Add new columns to tool_usage_logs."""
    _add_tool_usage_logs_tracking_columns()
    _add_tool_usage_logs_permission_columns()


def _add_tool_usage_logs_tracking_columns() -> None:
    """Add tracking columns to tool_usage_logs."""
    op.add_column('tool_usage_logs', sa.Column('category', sa.String(), nullable=True))
    op.add_column('tool_usage_logs', sa.Column('execution_time_ms', sa.Integer(), nullable=True))
    op.add_column('tool_usage_logs', sa.Column('tokens_used', sa.Integer(), nullable=True))
    op.add_column('tool_usage_logs', sa.Column('cost_cents', sa.Integer(), nullable=True))


def _add_tool_usage_logs_permission_columns() -> None:
    """Add permission columns to tool_usage_logs."""
    op.add_column('tool_usage_logs', sa.Column('plan_tier', sa.String(), nullable=False))
    op.add_column('tool_usage_logs', sa.Column('permission_check_result', sa.JSON(), nullable=True))
    op.add_column('tool_usage_logs', sa.Column('arguments', sa.JSON(), nullable=True))


def _alter_tool_usage_logs_columns() -> None:
    """Alter existing tool_usage_logs columns."""
    _alter_tool_usage_logs_user_and_status()
    _alter_tool_usage_logs_created_at()


def _alter_tool_usage_logs_user_and_status() -> None:
    """Alter user_id and status columns for tool_usage_logs."""
    op.alter_column('tool_usage_logs', 'user_id',
        existing_type=sa.VARCHAR(),
        nullable=False)
    op.alter_column('tool_usage_logs', 'status',
        existing_type=sa.VARCHAR(),
        nullable=False)


def _alter_tool_usage_logs_created_at() -> None:
    """Alter created_at column for tool_usage_logs."""
    op.alter_column('tool_usage_logs', 'created_at',
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        nullable=True,
        existing_server_default=sa.text('now()'))


def _create_tool_usage_logs_indexes() -> None:
    """Create indexes for tool_usage_logs."""
    op.create_index(op.f('ix_tool_usage_logs_category'), 'tool_usage_logs', ['category'], unique=False)
    op.create_index(op.f('ix_tool_usage_logs_created_at'), 'tool_usage_logs', ['created_at'], unique=False)
    op.create_index(op.f('ix_tool_usage_logs_status'), 'tool_usage_logs', ['status'], unique=False)
    op.create_index(op.f('ix_tool_usage_logs_tool_name'), 'tool_usage_logs', ['tool_name'], unique=False)


def _create_tool_usage_logs_foreign_keys() -> None:
    """Create foreign key constraints for tool_usage_logs."""
    op.create_foreign_key(None, 'tool_usage_logs', 'userbase', ['user_id'], ['id'])


def _drop_tool_usage_logs_columns() -> None:
    """Drop obsolete tool_usage_logs columns."""
    op.drop_column('tool_usage_logs', 'output_data')
    op.drop_column('tool_usage_logs', 'duration_ms')
    op.drop_column('tool_usage_logs', 'input_data')


def _modify_userbase_table() -> None:
    """Modify userbase table structure."""
    _alter_userbase_columns()
    _drop_userbase_indexes()


def _alter_userbase_columns() -> None:
    """Alter existing userbase columns."""
    _alter_userbase_plan_expires_at()
    _alter_userbase_plan_started_at()


def _alter_userbase_plan_expires_at() -> None:
    """Alter plan_expires_at column for userbase."""
    op.alter_column('userbase', 'plan_expires_at',
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True)


def _alter_userbase_plan_started_at() -> None:
    """Alter plan_started_at column for userbase."""
    op.alter_column('userbase', 'plan_started_at',
        existing_type=postgresql.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True)


def _drop_userbase_indexes() -> None:
    """Drop obsolete userbase indexes."""
    op.drop_index(op.f('idx_userbase_created_at'), table_name='userbase')
    op.drop_index(op.f('idx_userbase_email'), table_name='userbase')
    op.drop_index(op.f('idx_userbase_plan_tier_is_active'), table_name='userbase')
    op.drop_index(op.f('idx_userbase_role_is_developer'), table_name='userbase')
    op.drop_index(op.f('ix_userbase_role'), table_name='userbase')


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    create_mcp_tables()
    create_agent_state_tables()
    _create_all_agent_tables()
    modify_existing_tables()
    # ### end Alembic commands ###


def restore_existing_tables() -> None:
    """Restore existing tables to previous state."""
    _restore_userbase_table()
    _restore_tool_usage_logs_table()
    _restore_supply_update_logs_table()
    _restore_research_sessions_table()
    _restore_corpora_table()
    _restore_ai_supply_items_table()


def _restore_userbase_table() -> None:
    """Restore userbase table to previous state."""
    _restore_userbase_indexes()
    _restore_userbase_columns()


def _restore_userbase_indexes() -> None:
    """Restore userbase indexes."""
    op.create_index(op.f('ix_userbase_role'), 'userbase', ['role'], unique=False)
    op.create_index(op.f('idx_userbase_role_is_developer'), 'userbase', ['role', 'is_developer'], unique=False)
    op.create_index(op.f('idx_userbase_plan_tier_is_active'), 'userbase', ['plan_tier', 'is_active'], unique=False)
    op.create_index(op.f('idx_userbase_email'), 'userbase', ['email'], unique=False)
    op.create_index(op.f('idx_userbase_created_at'), 'userbase', ['created_at'], unique=False)


def _restore_userbase_columns() -> None:
    """Restore userbase column types."""
    _restore_userbase_plan_started_at()
    _restore_userbase_plan_expires_at()


def _restore_userbase_plan_started_at() -> None:
    """Restore plan_started_at column type for userbase."""
    op.alter_column('userbase', 'plan_started_at',
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True)


def _restore_userbase_plan_expires_at() -> None:
    """Restore plan_expires_at column type for userbase."""
    op.alter_column('userbase', 'plan_expires_at',
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        existing_nullable=True)


def _restore_tool_usage_logs_table() -> None:
    """Restore tool_usage_logs table to previous state."""
    _restore_tool_usage_logs_columns()
    _restore_tool_usage_logs_constraints()
    _restore_tool_usage_logs_indexes()
    _restore_tool_usage_logs_column_types()
    _drop_new_tool_usage_logs_columns()


def _restore_tool_usage_logs_columns() -> None:
    """Restore removed tool_usage_logs columns."""
    op.add_column('tool_usage_logs', sa.Column('input_data', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.add_column('tool_usage_logs', sa.Column('duration_ms', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('tool_usage_logs', sa.Column('output_data', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True))


def _restore_tool_usage_logs_constraints() -> None:
    """Remove foreign key and indexes from tool_usage_logs."""
    _drop_tool_usage_logs_foreign_key()
    _drop_tool_usage_logs_indexes()


def _drop_tool_usage_logs_foreign_key() -> None:
    """Drop foreign key constraint from tool_usage_logs."""
    op.drop_constraint(None, 'tool_usage_logs', type_='foreignkey')


def _drop_tool_usage_logs_indexes() -> None:
    """Drop indexes from tool_usage_logs."""
    op.drop_index(op.f('ix_tool_usage_logs_tool_name'), table_name='tool_usage_logs')
    op.drop_index(op.f('ix_tool_usage_logs_status'), table_name='tool_usage_logs')
    op.drop_index(op.f('ix_tool_usage_logs_created_at'), table_name='tool_usage_logs')
    op.drop_index(op.f('ix_tool_usage_logs_category'), table_name='tool_usage_logs')


def _restore_tool_usage_logs_indexes() -> None:
    """Restore tool_usage_logs column types."""
    _restore_tool_usage_logs_created_at()
    _restore_tool_usage_logs_status_and_user()


def _restore_tool_usage_logs_created_at() -> None:
    """Restore created_at column type for tool_usage_logs."""
    op.alter_column('tool_usage_logs', 'created_at',
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        nullable=False,
        existing_server_default=sa.text('now()'))


def _restore_tool_usage_logs_status_and_user() -> None:
    """Restore status and user_id column types for tool_usage_logs."""
    op.alter_column('tool_usage_logs', 'status',
        existing_type=sa.VARCHAR(),
        nullable=True)
    op.alter_column('tool_usage_logs', 'user_id',
        existing_type=sa.VARCHAR(),
        nullable=True)


def _restore_tool_usage_logs_column_types() -> None:
    """Drop new tool_usage_logs columns (part 1)."""
    op.drop_column('tool_usage_logs', 'arguments')
    op.drop_column('tool_usage_logs', 'permission_check_result')
    op.drop_column('tool_usage_logs', 'plan_tier')
    op.drop_column('tool_usage_logs', 'cost_cents')


def _drop_new_tool_usage_logs_columns() -> None:
    """Drop new tool_usage_logs columns (part 2)."""
    op.drop_column('tool_usage_logs', 'tokens_used')
    op.drop_column('tool_usage_logs', 'execution_time_ms')
    op.drop_column('tool_usage_logs', 'category')


def _restore_supply_update_logs_table() -> None:
    """Restore supply_update_logs table to previous state."""
    _restore_supply_update_logs_columns()
    _restore_supply_update_logs_constraints()
    _restore_supply_update_logs_column_types()
    _drop_new_supply_update_logs_columns()


def _restore_supply_update_logs_columns() -> None:
    """Restore removed supply_update_logs columns."""
    op.add_column('supply_update_logs', sa.Column('update_type', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.add_column('supply_update_logs', sa.Column('created_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False))


def _restore_supply_update_logs_constraints() -> None:
    """Remove foreign key constraints from supply_update_logs."""
    op.drop_constraint(None, 'supply_update_logs', type_='foreignkey')
    op.drop_constraint(None, 'supply_update_logs', type_='foreignkey')


def _restore_supply_update_logs_column_types() -> None:
    """Restore supply_update_logs column types."""
    op.alter_column('supply_update_logs', 'updated_by',
        existing_type=sa.VARCHAR(),
        nullable=True)
    op.alter_column('supply_update_logs', 'supply_item_id',
        existing_type=sa.VARCHAR(),
        nullable=True)


def _drop_new_supply_update_logs_columns() -> None:
    """Drop new supply_update_logs columns."""
    op.drop_column('supply_update_logs', 'updated_at')
    op.drop_column('supply_update_logs', 'update_reason')
    op.drop_column('supply_update_logs', 'research_session_id')
    op.drop_column('supply_update_logs', 'field_updated')


def _restore_research_sessions_table() -> None:
    """Restore research_sessions table to previous state."""
    _restore_research_sessions_columns()
    _restore_research_sessions_column_types()
    _drop_new_research_sessions_columns()


def _restore_research_sessions_columns() -> None:
    """Restore removed research_sessions columns."""
    op.add_column('research_sessions', sa.Column('findings', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.add_column('research_sessions', sa.Column('user_id', sa.VARCHAR(), autoincrement=False, nullable=True))
    op.add_column('research_sessions', sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.add_column('research_sessions', sa.Column('topic', sa.VARCHAR(), autoincrement=False, nullable=False))


def _restore_research_sessions_column_types() -> None:
    """Restore research_sessions column types."""
    op.alter_column('research_sessions', 'created_at',
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        nullable=False,
        existing_server_default=sa.text('now()'))


def _drop_new_research_sessions_columns() -> None:
    """Drop new research_sessions columns."""
    _drop_research_sessions_completion_columns()
    _drop_research_sessions_data_columns()


def _drop_research_sessions_completion_columns() -> None:
    """Drop completion tracking columns from research_sessions."""
    op.drop_column('research_sessions', 'error_message')
    op.drop_column('research_sessions', 'completed_at')
    op.drop_column('research_sessions', 'initiated_by')
    op.drop_column('research_sessions', 'citations')


def _drop_research_sessions_data_columns() -> None:
    """Drop data columns from research_sessions."""
    _drop_research_sessions_json_columns()
    _drop_research_sessions_core_columns()


def _drop_research_sessions_json_columns() -> None:
    """Drop JSON data columns from research_sessions."""
    op.drop_column('research_sessions', 'processed_data')
    op.drop_column('research_sessions', 'raw_results')
    op.drop_column('research_sessions', 'questions_answered')
    op.drop_column('research_sessions', 'research_plan')


def _drop_research_sessions_core_columns() -> None:
    """Drop core columns from research_sessions."""
    op.drop_column('research_sessions', 'session_id')
    op.drop_column('research_sessions', 'query')


def _restore_corpora_table() -> None:
    """Restore corpora table to previous state."""
    op.drop_column('corpora', 'metadata_')
    op.drop_column('corpora', 'domain')


def _restore_ai_supply_items_table() -> None:
    """Restore ai_supply_items table to previous state."""
    _restore_ai_supply_items_columns()
    _restore_ai_supply_items_indexes()
    _restore_ai_supply_items_column_types()
    _drop_new_ai_supply_items_columns()


def _restore_ai_supply_items_columns() -> None:
    """Restore removed ai_supply_items columns."""
    op.add_column('ai_supply_items', sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.add_column('ai_supply_items', sa.Column('updated_at', postgresql.TIMESTAMP(), server_default=sa.text('now()'), autoincrement=False, nullable=False))
    op.add_column('ai_supply_items', sa.Column('metadata_', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True))
    op.add_column('ai_supply_items', sa.Column('cost_per_token', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))


def _restore_ai_supply_items_indexes() -> None:
    """Remove ai_supply_items indexes."""
    op.drop_index(op.f('ix_ai_supply_items_provider'), table_name='ai_supply_items')
    op.drop_index(op.f('ix_ai_supply_items_model_name'), table_name='ai_supply_items')


def _restore_ai_supply_items_column_types() -> None:
    """Restore ai_supply_items column types."""
    op.alter_column('ai_supply_items', 'created_at',
        existing_type=sa.DateTime(timezone=True),
        type_=postgresql.TIMESTAMP(),
        nullable=False,
        existing_server_default=sa.text('now()'))


def _drop_new_ai_supply_items_columns() -> None:
    """Drop new ai_supply_items columns."""
    _drop_ai_supply_items_metadata_columns()
    _drop_ai_supply_items_pricing_columns()


def _drop_ai_supply_items_metadata_columns() -> None:
    """Drop metadata columns from ai_supply_items."""
    _drop_ai_supply_items_tracking_columns()
    _drop_ai_supply_items_api_columns()


def _drop_ai_supply_items_tracking_columns() -> None:
    """Drop tracking metadata columns from ai_supply_items."""
    op.drop_column('ai_supply_items', 'confidence_score')
    op.drop_column('ai_supply_items', 'research_source')
    op.drop_column('ai_supply_items', 'last_updated')


def _drop_ai_supply_items_api_columns() -> None:
    """Drop API metadata columns from ai_supply_items."""
    op.drop_column('ai_supply_items', 'performance_metrics')
    op.drop_column('ai_supply_items', 'api_endpoints')


def _drop_ai_supply_items_pricing_columns() -> None:
    """Drop pricing columns from ai_supply_items."""
    _drop_ai_supply_items_capability_columns()
    _drop_ai_supply_items_price_columns()


def _drop_ai_supply_items_capability_columns() -> None:
    """Drop capability columns from ai_supply_items."""
    op.drop_column('ai_supply_items', 'availability_status')
    op.drop_column('ai_supply_items', 'capabilities')
    op.drop_column('ai_supply_items', 'max_output_tokens')
    op.drop_column('ai_supply_items', 'context_window')


def _drop_ai_supply_items_price_columns() -> None:
    """Drop price columns from ai_supply_items."""
    op.drop_column('ai_supply_items', 'pricing_currency')
    op.drop_column('ai_supply_items', 'pricing_output')
    op.drop_column('ai_supply_items', 'pricing_input')
    op.drop_column('ai_supply_items', 'model_version')


def drop_agent_state_tables() -> None:
    """Drop agent state management tables."""
    _drop_agent_state_transactions_table()
    _drop_agent_recovery_logs_table()
    _drop_corpus_audit_logs_table()
    _drop_agent_state_snapshots_table()


def _drop_agent_state_transactions_table() -> None:
    """Drop agent_state_transactions table and indexes."""
    op.drop_index(op.f('ix_agent_state_transactions_snapshot_id'), table_name='agent_state_transactions')
    op.drop_index(op.f('ix_agent_state_transactions_run_id'), table_name='agent_state_transactions')
    op.drop_index('idx_state_tx_started', table_name='agent_state_transactions')
    op.drop_index('idx_state_tx_run_status', table_name='agent_state_transactions')
    op.drop_table('agent_state_transactions')


def _drop_agent_recovery_logs_table() -> None:
    """Drop agent_recovery_logs table and indexes."""
    _drop_agent_recovery_logs_standard_indexes()
    _drop_agent_recovery_logs_custom_indexes()
    op.drop_table('agent_recovery_logs')


def _drop_agent_recovery_logs_standard_indexes() -> None:
    """Drop standard indexes from agent_recovery_logs."""
    op.drop_index(op.f('ix_agent_recovery_logs_thread_id'), table_name='agent_recovery_logs')
    op.drop_index(op.f('ix_agent_recovery_logs_run_id'), table_name='agent_recovery_logs')


def _drop_agent_recovery_logs_custom_indexes() -> None:
    """Drop custom indexes from agent_recovery_logs."""
    op.drop_index('idx_recovery_status', table_name='agent_recovery_logs')
    op.drop_index('idx_recovery_run_initiated', table_name='agent_recovery_logs')
    op.drop_index('idx_recovery_auto', table_name='agent_recovery_logs')


def _drop_corpus_audit_logs_table() -> None:
    """Drop corpus_audit_logs table and indexes."""
    _drop_corpus_audit_logs_indexes()
    _drop_corpus_audit_logs_remaining_indexes()
    op.drop_table('corpus_audit_logs')


def _drop_corpus_audit_logs_indexes() -> None:
    """Drop corpus_audit_logs indexes."""
    _drop_corpus_audit_logs_user_indexes()
    _drop_corpus_audit_logs_resource_indexes()
    _drop_corpus_audit_logs_remaining_indexes()


def _drop_corpus_audit_logs_user_indexes() -> None:
    """Drop user-related indexes from corpus_audit_logs."""
    op.drop_index(op.f('ix_corpus_audit_logs_user_id'), table_name='corpus_audit_logs')
    op.drop_index(op.f('ix_corpus_audit_logs_timestamp'), table_name='corpus_audit_logs')
    op.drop_index(op.f('ix_corpus_audit_logs_status'), table_name='corpus_audit_logs')
    op.drop_index(op.f('ix_corpus_audit_logs_session_id'), table_name='corpus_audit_logs')


def _drop_corpus_audit_logs_resource_indexes() -> None:
    """Drop resource-related indexes from corpus_audit_logs."""
    op.drop_index(op.f('ix_corpus_audit_logs_resource_type'), table_name='corpus_audit_logs')
    op.drop_index(op.f('ix_corpus_audit_logs_resource_id'), table_name='corpus_audit_logs')
    op.drop_index(op.f('ix_corpus_audit_logs_request_id'), table_name='corpus_audit_logs')
    op.drop_index(op.f('ix_corpus_audit_logs_ip_address'), table_name='corpus_audit_logs')


def _drop_corpus_audit_logs_remaining_indexes() -> None:
    """Drop remaining corpus_audit_logs indexes."""
    op.drop_index(op.f('ix_corpus_audit_logs_corpus_id'), table_name='corpus_audit_logs')
    op.drop_index(op.f('ix_corpus_audit_logs_action'), table_name='corpus_audit_logs')


def _drop_agent_state_snapshots_table() -> None:
    """Drop agent_state_snapshots table and indexes."""
    _drop_agent_state_snapshots_indexes()
    _drop_agent_state_snapshots_custom_indexes()
    op.drop_table('agent_state_snapshots')


def _drop_agent_state_snapshots_indexes() -> None:
    """Drop agent_state_snapshots standard indexes."""
    op.drop_index(op.f('ix_agent_state_snapshots_user_id'), table_name='agent_state_snapshots')
    op.drop_index(op.f('ix_agent_state_snapshots_thread_id'), table_name='agent_state_snapshots')
    op.drop_index(op.f('ix_agent_state_snapshots_run_id'), table_name='agent_state_snapshots')
    op.drop_index(op.f('ix_agent_state_snapshots_expires_at'), table_name='agent_state_snapshots')
    op.drop_index(op.f('ix_agent_state_snapshots_created_at'), table_name='agent_state_snapshots')


def _drop_agent_state_snapshots_custom_indexes() -> None:
    """Drop agent_state_snapshots custom indexes."""
    op.drop_index('idx_agent_state_thread_created', table_name='agent_state_snapshots')
    op.drop_index('idx_agent_state_run_created', table_name='agent_state_snapshots')
    op.drop_index('idx_agent_state_recovery', table_name='agent_state_snapshots')
    op.drop_index('idx_agent_state_expires', table_name='agent_state_snapshots')


def drop_mcp_tables() -> None:
    """Drop MCP external server tables."""
    op.drop_table('mcp_tool_executions')
    op.drop_table('mcp_resource_access')
    op.drop_table('mcp_external_servers')


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    restore_existing_tables()
    drop_agent_state_tables()
    drop_mcp_tables()
    # ### end Alembic commands ###
