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


def upgrade() -> None:
    """Upgrade schema."""
    # Create missing tables
    op.create_table('tool_usage_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('tool_name', sa.String(), nullable=False),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('output_data', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('ai_supply_items',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('cost_per_token', sa.Float(), nullable=True),
        sa.Column('metadata_', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('research_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('topic', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('findings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('supply_update_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('supply_item_id', sa.String(), nullable=True),
        sa.Column('update_type', sa.String(), nullable=False),
        sa.Column('old_value', sa.JSON(), nullable=True),
        sa.Column('new_value', sa.JSON(), nullable=True),
        sa.Column('updated_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add missing columns to userbase table
    op.add_column('userbase', sa.Column('tool_permissions', sa.JSON(), nullable=True))
    op.add_column('userbase', sa.Column('plan_expires_at', sa.DateTime(), nullable=True))
    op.add_column('userbase', sa.Column('feature_flags', sa.JSON(), nullable=True))
    op.add_column('userbase', sa.Column('payment_status', sa.String(), nullable=True))
    op.add_column('userbase', sa.Column('auto_renew', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('userbase', sa.Column('plan_tier', sa.String(), nullable=True))
    op.add_column('userbase', sa.Column('plan_started_at', sa.DateTime(), nullable=True))
    op.add_column('userbase', sa.Column('trial_period', sa.Boolean(), nullable=True, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove columns from userbase table
    op.drop_column('userbase', 'trial_period')
    op.drop_column('userbase', 'plan_started_at')
    op.drop_column('userbase', 'plan_tier')
    op.drop_column('userbase', 'auto_renew')
    op.drop_column('userbase', 'payment_status')
    op.drop_column('userbase', 'feature_flags')
    op.drop_column('userbase', 'plan_expires_at')
    op.drop_column('userbase', 'tool_permissions')
    
    # Drop tables
    op.drop_table('supply_update_logs')
    op.drop_table('research_sessions')
    op.drop_table('ai_supply_items')
    op.drop_table('tool_usage_logs')
