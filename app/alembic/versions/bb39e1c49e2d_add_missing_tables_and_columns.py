"""add_missing_tables_and_columns

Revision ID: bb39e1c49e2d
Revises: 9f682854941c
Create Date: 2025-08-11 09:54:49.591314

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb39e1c49e2d'
down_revision: Union[str, Sequence[str], None] = '9f682854941c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_tool_usage_logs_base() -> None:
    """Create tool_usage_logs table base columns."""
    op.create_table('tool_usage_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('tool_name', sa.String(), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_data', sa.JSON(), nullable=True))

def _add_tool_usage_logs_metadata() -> None:
    """Add metadata columns to tool_usage_logs table."""
    op.add_column('tool_usage_logs', sa.Column('status', sa.String(), nullable=True))
    op.add_column('tool_usage_logs', sa.Column('duration_ms', sa.Integer(), nullable=True))
    op.add_column('tool_usage_logs', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_primary_key('pk_tool_usage_logs', 'tool_usage_logs', ['id'])


def _create_ai_supply_items_base() -> None:
    """Create ai_supply_items table base columns."""
    op.create_table('ai_supply_items',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('cost_per_token', sa.Float(), nullable=True))

def _add_ai_supply_items_metadata() -> None:
    """Add metadata columns to ai_supply_items table."""
    op.add_column('ai_supply_items', sa.Column('metadata_', sa.JSON(), nullable=True))
    op.add_column('ai_supply_items', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('ai_supply_items', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_primary_key('pk_ai_supply_items', 'ai_supply_items', ['id'])


def _create_research_sessions_base() -> None:
    """Create research_sessions table base columns."""
    op.create_table('research_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('topic', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('findings', sa.JSON(), nullable=True))

def _add_research_sessions_metadata() -> None:
    """Add metadata columns to research_sessions table."""
    op.add_column('research_sessions', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column('research_sessions', sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_primary_key('pk_research_sessions', 'research_sessions', ['id'])


def _create_supply_update_logs_base() -> None:
    """Create supply_update_logs table base columns."""
    op.create_table('supply_update_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('supply_item_id', sa.String(), nullable=True),
        sa.Column('update_type', sa.String(), nullable=False),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True))

def _add_supply_update_logs_metadata() -> None:
    """Add metadata columns to supply_update_logs table."""
    op.add_column('supply_update_logs', sa.Column('updated_by', sa.String(), nullable=True))
    op.add_column('supply_update_logs', sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.create_primary_key('pk_supply_update_logs', 'supply_update_logs', ['id'])


def _add_userbase_plan_columns() -> None:
    """Add plan-related columns to userbase table."""
    op.add_column('userbase', sa.Column('tool_permissions', sa.JSON(), nullable=True))
    op.add_column('userbase', sa.Column('plan_expires_at', sa.DateTime(), nullable=True))
    op.add_column('userbase', sa.Column('feature_flags', sa.JSON(), nullable=True))
    op.add_column('userbase', sa.Column('payment_status', sa.String(), nullable=True))

def _add_userbase_subscription_columns() -> None:
    """Add subscription-related columns to userbase table."""
    op.add_column('userbase', sa.Column('auto_renew', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('userbase', sa.Column('plan_tier', sa.String(), nullable=True))
    op.add_column('userbase', sa.Column('plan_started_at', sa.DateTime(), nullable=True))
    op.add_column('userbase', sa.Column('trial_period', sa.Integer(), nullable=True, server_default='0'))


def _create_core_tables() -> None:
    """Create all core application tables."""
    _create_tool_usage_logs_base()
    _add_tool_usage_logs_metadata()
    _create_ai_supply_items_base()
    _add_ai_supply_items_metadata()
    _create_research_sessions_base()
    _add_research_sessions_metadata()

def _create_update_tables() -> None:
    """Create update tracking tables."""
    _create_supply_update_logs_base()
    _add_supply_update_logs_metadata()

def upgrade() -> None:
    """Upgrade schema."""
    _create_core_tables()
    _create_update_tables()
    _add_userbase_plan_columns()
    _add_userbase_subscription_columns()


def _remove_userbase_subscription_columns() -> None:
    """Remove subscription-related columns from userbase table."""
    op.drop_column('userbase', 'trial_period')
    op.drop_column('userbase', 'plan_started_at')
    op.drop_column('userbase', 'plan_tier')
    op.drop_column('userbase', 'auto_renew')

def _remove_userbase_plan_columns() -> None:
    """Remove plan-related columns from userbase table."""
    op.drop_column('userbase', 'payment_status')
    op.drop_column('userbase', 'feature_flags')
    op.drop_column('userbase', 'plan_expires_at')
    op.drop_column('userbase', 'tool_permissions')


def _drop_tables() -> None:
    """Drop created tables."""
    op.drop_table('supply_update_logs')
    op.drop_table('research_sessions')
    op.drop_table('ai_supply_items')
    op.drop_table('tool_usage_logs')


def downgrade() -> None:
    """Downgrade schema."""
    _remove_userbase_subscription_columns()
    _remove_userbase_plan_columns()
    _drop_tables()
